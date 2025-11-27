from dotenv import load_dotenv
load_dotenv()

import logging
from aiohttp import web
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity
from bot import bot_logic
from core.logging_config import configure_logging
from core.settings import BotSettings

configure_logging()
logger = logging.getLogger(__name__)

bot_settings = BotSettings()

if bot_settings.has_tenant():
    adapter_settings = BotFrameworkAdapterSettings(
        app_id=bot_settings.app_id,
        app_password=bot_settings.app_password,
        channel_auth_tenant=bot_settings.tenant_id
    )
else:
    adapter_settings = BotFrameworkAdapterSettings(
        bot_settings.app_id,
        bot_settings.app_password
    )

adapter = BotFrameworkAdapter(adapter_settings)

async def on_error(context: TurnContext, error: Exception):
    conversation_id = getattr(getattr(context, "activity", None), "conversation", None)
    conversation_id = getattr(conversation_id, "id", None)
    user = getattr(getattr(context, "activity", None), "from_property", None)
    user_id = getattr(user, "id", None)

    logger.exception(
        "Unhandled error while processing bot turn. conversation_id=%s user_id=%s",
        conversation_id,
        user_id,
    )

    try:
        await context.send_activity(
            "Sorry, something went wrong while processing your message."
        )
    except Exception as notify_error:
        logger.error(
            "Failed to notify user about the error. conversation_id=%s user_id=%s error=%s",
            conversation_id,
            user_id,
            notify_error,
        )

adapter.on_turn_error = on_error

async def messages(req: web.Request) -> web.Response:
    """
    Endpoint principal que recibe los mensajes de Teams
    """
    if req.method != "POST":
        logger.warning("Method %s not allowed on /api/messages", req.method)
        return web.Response(status=405)
    
    logger.info("POST request received on /api/messages")
    body = await req.json()
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")
    conversation_id = getattr(activity.conversation, "id", None)
    user_id = getattr(getattr(activity, "from_property", None), "id", None)
    logger.info(
        "Activity received type=%s conversation_id=%s user_id=%s",
        activity.type,
        conversation_id,
        user_id
    )
    response = await adapter.process_activity(activity, auth_header, bot_logic)
    
    if response:
        logger.debug("Adapter returned response status=%s body=%s", response.status, response.body)
        return web.json_response(data=response.body, status=response.status)
    logger.info("Activity processed without explicit response. conversation_id=%s", conversation_id)
    return web.Response(status=201)

app = web.Application()
app.router.add_post('/api/messages', messages)

if __name__ == '__main__':
    logger.info("Starting aiohttp server on 0.0.0.0:3978")
    web.run_app(app, host='0.0.0.0', port=3978)
