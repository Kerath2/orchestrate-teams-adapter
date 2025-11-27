import asyncio
import logging
from typing import List, Optional, Dict, Any
from botbuilder.core import TurnContext
from botbuilder.schema import Activity
from conversation.watsonx import WatsonxOrchestrate
from conversation.watsonx_settings import WatsonxSettings
from conversation.watsonx_token_manager import WatsonxTokenManager
from conversation.watsonx_ai import WatsonxAI
from conversation.watsonx_ai_settings import WatsonxAISettings
from services import (
    TeamsContextBuilder,
    MessageRule,
    LocaleResponseRule,
    ArgumentsPrefixRule,
    UserInputLabelRule,
    TeamsActivityContext,
    UserProfileService,
    UserProfileSettings,
)
from session.profile import RedisProfileStore, ProfileStore
from session.chat.redis_session import ChatRedisSessionManager

logger = logging.getLogger(__name__)


class TeamsWatsonBot:
    """Coordinates message handling between Teams and Watson Orchestrate."""

    def __init__(
        self,
        orchestrator: WatsonxOrchestrate,
        context_builder: TeamsContextBuilder,
        message_rules: Optional[List[MessageRule]] = None,
        profile_service: Optional[UserProfileService] = None,
        language_controller: Optional[WatsonxAI] = None,
        fallback_message: str = "Lo siento, no pude procesar tu mensaje en este momento.",
    ):
        self._orchestrator = orchestrator
        self._context_builder = context_builder
        self._message_rules = message_rules or []
        self._profile_service = profile_service
        self._language_controller = language_controller
        self._fallback_message = fallback_message

    async def handle_turn(self, turn_context: TurnContext) -> None:
        """
        Entry point for every Bot Framework activity.

        :param turn_context: Current TurnContext instance (provided by adapter).
        """
        activity = turn_context.activity
        if activity.type != "message":
            logger.debug("Activity type %s ignored by the bot", activity.type)
            return

        activity_context = self._context_builder.from_activity(activity)
        logger.info(
            "Message received: user=%s conversation=%s locale=%s",
            activity_context.user_id,
            activity_context.conversation_id,
            activity_context.locale,
        )
        logger.debug(
            "Message content from %s: %s",
            activity_context.user_id,
            activity_context.message,
        )

        await self._send_typing_indicator(turn_context)

        profile_data = await self._fetch_user_profile(activity_context.user_aad_object_id)
        activity_context = self._context_builder.merge_profile_data(
            activity_context,
            profile_data,
        )

        watson_context = self._context_builder.to_watson_context(
            activity_context,
            profile=profile_data,
        )
        logger.debug(
            "Context built for conversation_id=%s: %s",
            activity_context.conversation_id,
            watson_context,
        )

        logger.info(
            "Requesting Watson Orchestrate response for conversation_id=%s",
            activity_context.conversation_id,
        )
        prepared_message = self._apply_message_rules(
            activity_context.message,
            activity_context,
            profile_data,
        )
        watson_response = self._orchestrator.chat_completion(
            conversation_id=activity_context.conversation_id,
            user_message=prepared_message,
            context=watson_context,
        )

        # Apply language control if enabled
        final_response = await self._apply_language_control(
            watson_response,
            activity_context.message,
            activity_context.locale,
            activity_context.conversation_id,
        )

        await self._dispatch_response(
            turn_context,
            final_response,
            activity_context.conversation_id,
        )

    async def _send_typing_indicator(self, turn_context: TurnContext) -> None:
        typing_activity = Activity(type="typing")
        await turn_context.send_activity(typing_activity)
        logger.debug(
            "Typing indicator sent to Teams conversation_id=%s",
            turn_context.activity.conversation.id,
        )

    async def _dispatch_response(
        self,
        turn_context: TurnContext,
        watson_response: Optional[str],
        conversation_id: str,
    ) -> None:
        if watson_response:
            await turn_context.send_activity(watson_response)
            logger.info(
                "Watson response sent to Teams conversation_id=%s",
                conversation_id,
            )
            logger.debug("Response content: %s", watson_response)
            return

        # await turn_context.send_activity(self._fallback_message)
        logger.warning(
            "Watson did not return a response for conversation_id=%s",
            conversation_id,
        )

    async def _fetch_user_profile(
        self,
        aad_object_id: str,
    ) -> Optional[Dict[str, Any]]:
        if not self._profile_service or not aad_object_id:
            return None
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._profile_service.get_user_profile, aad_object_id
        )

    def _apply_message_rules(
        self,
        message: str,
        context: TeamsActivityContext,
        profile: Optional[Dict[str, Any]] = None,
    ) -> str:
        updated_message = message
        for rule in self._message_rules:
            updated_message = rule.apply(updated_message, context, profile)
        logger.debug(
            "Message after applying rules for conversation_id=%s: %s",
            context.conversation_id,
            updated_message,
        )
        return updated_message

    async def _apply_language_control(
        self,
        orchestrate_response: Optional[str],
        user_message: str,
        user_locale: str,
        conversation_id: str,
    ) -> Optional[str]:
        """Apply language control using Watsonx.ai if enabled."""
        if not orchestrate_response:
            return orchestrate_response

        if not self._language_controller:
            logger.debug("Language controller not enabled, returning original response")
            return orchestrate_response

        logger.info(
            "Applying language control for conversation_id=%s locale=%s",
            conversation_id,
            user_locale,
        )

        loop = asyncio.get_running_loop()
        controlled_response = await loop.run_in_executor(
            None,
            self._language_controller.control_language_response,
            user_message,
            orchestrate_response,
            user_locale,
        )

        if controlled_response:
            logger.info(
                "Language control applied successfully for conversation_id=%s",
                conversation_id,
            )
            logger.debug(
                "Original: %s | Controlled: %s",
                orchestrate_response[:100],
                controlled_response[:100],
            )
            return controlled_response
        else:
            logger.warning(
                "Language control failed, returning original response for conversation_id=%s",
                conversation_id,
            )
            return orchestrate_response


def _build_bot() -> TeamsWatsonBot:
    session_manager = ChatRedisSessionManager(expire_seconds=900)
    watsonx_settings = WatsonxSettings()
    token_manager = WatsonxTokenManager(settings=watsonx_settings)
    orchestrator = WatsonxOrchestrate(
        settings=watsonx_settings,
        chat_session_manager=session_manager,
        token_manager=token_manager,
    )
    context_builder = TeamsContextBuilder()
    message_rules: List[MessageRule] = [
        UserInputLabelRule(),
        ArgumentsPrefixRule(),
    ]
    profile_store: ProfileStore = RedisProfileStore(expire_seconds=86400)
    profile_settings = UserProfileSettings()
    profile_service = UserProfileService(
        settings=profile_settings,
        store=profile_store,
    )

    # Initialize Watsonx.ai for language control
    watsonx_ai_settings = WatsonxAISettings()
    language_controller = None
    if watsonx_ai_settings.is_enabled():
        language_controller = WatsonxAI(
            settings=watsonx_ai_settings,
            api_key=watsonx_ai_settings.api_key,  # Pass API key directly
        )
        logger.info("Watsonx.ai language controller enabled")
    else:
        logger.warning("Watsonx.ai language controller NOT enabled (missing credentials)")

    return TeamsWatsonBot(
        orchestrator=orchestrator,
        context_builder=context_builder,
        message_rules=message_rules,
        profile_service=profile_service if profile_settings.is_enabled() else None,
        language_controller=language_controller,
    )


_bot_instance = _build_bot()


async def bot_logic(turn_context: TurnContext):
    await _bot_instance.handle_turn(turn_context)
