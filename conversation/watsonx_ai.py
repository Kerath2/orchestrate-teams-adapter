import requests
import logging
from typing import Optional
from .watsonx_ai_settings import WatsonxAISettings

logger = logging.getLogger(__name__)


class WatsonxAI:
    """Client for IBM Watsonx.ai to post-process responses and control language."""

    def __init__(self, settings: WatsonxAISettings, api_key: str):
        """
        Initialize Watsonx.ai client using IAM API Key directly.

        :param settings: Watsonx.ai settings
        :param api_key: IBM Cloud API Key for authentication
        """
        self.settings = settings
        self.api_key = api_key
        self._token = None
        self._token_expires_at = 0

    def _get_iam_token(self) -> str:
        """Get IAM token using API key."""
        import time

        now = time.time()
        # Reuse token if still valid (with 60 second buffer)
        if self._token and now < self._token_expires_at - 60:
            remaining = int(self._token_expires_at - now)
            logger.debug(f"Reusing IAM token; {remaining} seconds remaining.")
            return self._token

        logger.info("Requesting new IAM token for Watsonx.ai")

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={self.api_key}"

        try:
            response = requests.post(
                self.settings.token_url,
                headers=headers,
                data=data,
                timeout=30
            )
            response.raise_for_status()
            payload = response.json()

            self._token = payload["access_token"]
            expires_in = payload.get("expires_in", 3600)
            self._token_expires_at = time.time() + expires_in

            logger.info(f"IAM token for Watsonx.ai renewed. Expires in {expires_in} seconds.")
            return self._token

        except requests.exceptions.RequestException as exc:
            logger.exception(f"Error requesting IAM token: {exc}")
            raise

    def control_language_response(
        self,
        user_message: str,
        orchestrate_response: str,
        user_locale: str = "es-ES",
    ) -> Optional[str]:
        """
        Post-process the Orchestrate response to ensure it's in the correct language.

        :param user_message: Original message from the user
        :param orchestrate_response: Response from Watsonx Orchestrate
        :param user_locale: User's locale (e.g., 'es-ES', 'en-US')
        :return: Language-controlled response or None if error
        """
        if not self.settings.is_enabled():
            logger.warning("Watsonx.ai is not enabled, returning original response")
            return orchestrate_response

        fallback_language = self._get_target_language_from_locale(user_locale)
        prompt = self._build_language_control_prompt(
            user_message,
            orchestrate_response,
            fallback_language,
        )

        logger.info("Calling Watsonx.ai for language control using user message language")
        logger.debug(f"Prompt: {prompt}")

        return self._generate_text(prompt)

    def _get_target_language_from_locale(self, locale: str) -> str:
        """Determine fallback target language from locale for English/Spanish only."""
        locale_lower = (locale or "").lower()
        if locale_lower.startswith("en"):
            return "English"
        return "Spanish"  # Default to Spanish when locale is missing or not English

    def _build_language_control_prompt(
        self,
        user_message: str,
        orchestrate_response: str,
        fallback_language: str,
    ) -> str:
        """Build the prompt for language control using only English and Spanish."""
        return f"""You are a bilingual (English/Spanish) language validator. Determine the language of the USER MESSAGE (only English or Spanish) and ensure the RESPONSE TO CHECK is returned in that same language.

USER MESSAGE: {user_message}
RESPONSE TO CHECK: {orchestrate_response}
FALLBACK LANGUAGE FROM LOCALE: {fallback_language}

INSTRUCTIONS:
- Decide if USER MESSAGE is Spanish or English. If unclear, use the FALLBACK LANGUAGE FROM LOCALE.
- If RESPONSE TO CHECK is already in the USER MESSAGE language: return it EXACTLY as provided.
- If RESPONSE TO CHECK is in the other language: translate it to match the USER MESSAGE language.
- Preserve ALL formatting, markdown, emojis, placeholders, variables, and quoted text.
- Return ONLY the final response text.
- NO explanations, NO comments, NO meta-text.
- Do NOT add phrases like "Here is..." or "(The corrected...)".
- Do NOT explain what you did.
- Do NOT shorten or summarize; keep the full response intact.

OUTPUT (response only):"""

    def _generate_text(self, prompt: str) -> Optional[str]:
        """Call Watsonx.ai text generation API using project_id (not space_id)."""
        api_url = f"{self.settings.url}/ml/v1/text/generation?version=2023-05-29"
        token = self._get_iam_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Use project_id in the payload, not in headers
        payload = {
            "input": prompt,
            "parameters": {
                "decoding_method": "greedy",
                "max_new_tokens": self.settings.max_new_tokens,
                "temperature": self.settings.temperature,
                "repetition_penalty": 1.1,
            },
            "model_id": self.settings.model_id,
            "project_id": self.settings.project_id,  # THIS is the key!
        }

        try:
            logger.debug(f"Calling Watsonx.ai with model {self.settings.model_id}")
            logger.debug(f"Using project_id: {self.settings.project_id}")

            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()

            generated_text = result.get("results", [{}])[0].get("generated_text", "").strip()
            logger.debug(f"Watsonx.ai response: {generated_text}")

            return generated_text if generated_text else None

        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                logger.error(
                    f"HTTP error when calling Watsonx.ai status={e.response.status_code} body={e.response.text}"
                )
            logger.exception("Request to Watsonx.ai failed")
            return None
