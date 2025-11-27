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

        target_language = self._determine_target_language(user_message, user_locale)
        prompt = self._build_language_control_prompt(
            user_message,
            orchestrate_response,
            target_language,
        )

        logger.info(f"Calling Watsonx.ai for language control to {target_language}")
        logger.debug(f"Prompt: {prompt}")

        primary_response = self._generate_text(prompt)

        if not primary_response:
            return None

        primary_response = self._strip_prompt_artifacts(primary_response)

        if self._is_in_target_language(primary_response, target_language):
            return primary_response

        translated = self._translate_with_retry(
            text=primary_response,
            target_language=target_language,
        )
        if translated and self._is_in_target_language(translated, target_language):
            return translated

        # Last-chance translation using the original orchestrate response
        last_chance = self._translate_with_retry(
            text=orchestrate_response,
            target_language=target_language,
        )
        if last_chance and self._is_in_target_language(last_chance, target_language):
            return last_chance

        return last_chance or translated

    def _determine_target_language(self, user_message: str, locale: str) -> str:
        """
        Decide the target language giving priority to the latest user message.

        If we can detect the language from the message, we use that; otherwise we
        fall back to the locale.
        """
        locale_language = self._get_target_language_from_locale(locale)
        detected_code, detected_prob = self._detect_language_with_prob(user_message)
        detected_language = self._language_name_from_code(detected_code) if detected_code else None

        if self._has_spanish_markers(user_message):
            if detected_language and detected_language != "Spanish":
                logger.info(
                    "Spanish markers found; overriding detected language '%s'",
                    detected_language,
                )
            return "Spanish"

        if detected_language:
            if detected_language != locale_language:
                logger.info(
                    "Using detected language '%s' over locale '%s' (prob=%.2f)",
                    detected_language,
                    locale_language,
                    detected_prob,
                )
            # If detection probability is weak, prefer locale as safer fallback.
            if detected_prob < 0.70 and locale_language:
                return locale_language
            return detected_language

        return locale_language

    def _get_target_language_from_locale(self, locale: str) -> str:
        """Determine target language from locale."""
        locale_lower = (locale or "").lower()
        if locale_lower.startswith("es"):
            return "Spanish"
        elif locale_lower.startswith("en"):
            return "English"
        elif locale_lower.startswith("pt"):
            return "Portuguese"
        elif locale_lower.startswith("fr"):
            return "French"
        else:
            return "Spanish"  # Default

    def _detect_language_from_text(self, text: str) -> Optional[str]:
        """Detect language from free text using langdetect (best-effort)."""
        code, _prob = self._detect_language_with_prob(text)
        if not code:
            return None
        return self._language_name_from_code(code)

    def _detect_language_with_prob(self, text: str) -> tuple[Optional[str], float]:
        """Return language code and probability using langdetect."""
        if not text or len(text.strip()) < 4:
            return None, 0.0

        try:
            from langdetect import DetectorFactory, detect_langs
        except ImportError:
            logger.warning("langdetect not installed; skipping language detection")
            return None, 0.0

        try:
            DetectorFactory.seed = 0  # deterministic detection
            langs = detect_langs(text)
            if not langs:
                return None, 0.0
            lang_code = langs[0].lang
            prob = langs[0].prob
            logger.debug(
                "Detected language code '%s' (prob=%.2f) for text '%s'",
                lang_code,
                prob,
                text[:50],
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Language detection failed: %s", exc)
            return None, 0.0

        return lang_code, prob

    def _is_in_target_language(self, text: str, target_language: str) -> bool:
        detected = self._detect_language_from_text(text)
        if target_language.lower().startswith("spanish") and self._has_spanish_markers(text):
            return True
        if not detected:
            return False
        target_code = self._language_code_for_target(target_language)
        if detected.lower() == target_language.lower():
            return True
        if target_code and detected.lower().startswith(target_code):
            return True
        return False

    @staticmethod
    def _language_code_for_target(target_language: str) -> Optional[str]:
        return {
            "spanish": "es",
            "english": "en",
            "portuguese": "pt",
            "french": "fr",
        }.get((target_language or "").lower())

    def _language_name_from_code(self, code: str) -> Optional[str]:
        return {
            "es": "Spanish",
            "en": "English",
            "pt": "Portuguese",
            "fr": "French",
        }.get((code or "").lower())

    @staticmethod
    def _has_spanish_markers(text: str) -> bool:
        lowered = (text or "").lower()
        markers = [
            "¿",
            "¡",
            " qué",
            "cómo",
            "por qué",
            "ayuda",
            "opciones",
            "canales",
            "ticket",
        ]
        return any(marker in lowered for marker in markers)

    def _build_translation_prompt(self, text: str, target_language: str) -> str:
        """Force a direct translation when the first pass missed the target language."""
        lang_code = self._language_code_for_target(target_language) or target_language
        return f"""Translate the following text to {target_language} (language code: {lang_code}).
- Use ONLY {target_language}.
- Do NOT include any text in other languages.
- Preserve formatting/markdown/placeholders.
- Do NOT summarize or omit any content.
- If text is already in {target_language}, repeat it exactly.
- Never return the source language if it differs from {target_language}.
- Output format: \"{lang_code}: <translation>\"

TEXT:
{text}

OUTPUT (translation only, with prefix):"""

    def _build_strict_translation_prompt(self, text: str, target_language: str) -> str:
        """Second translation attempt with stricter instructions."""
        lang_code = self._language_code_for_target(target_language) or target_language
        return f"""You are a translation engine. Translate the text inside <text></text> to {target_language} (language code: {lang_code}).
- Answer ONLY with the translation in {target_language}.
- Do NOT include any other language or commentary.
- Preserve placeholders/formatting.
- If text is already in {target_language}, repeat it exactly.
- Never return the source language if it differs from {target_language}.
- Output format: \"{lang_code}: <translation>\"

<text>
{text}
</text>
"""

    def _build_example_translation_prompt(self, text: str, target_language: str) -> str:
        """Third translation attempt with explicit examples."""
        lang_code = self._language_code_for_target(target_language) or target_language
        examples = ""
        if target_language.lower().startswith("spanish"):
            examples = """Examples:
en: Hello! How are you? -> es: ¡Hola! ¿Cómo estás?
en: I can create a ticket for you. -> es: Puedo crear un ticket para ti.
en: Here are your options: view channels, create a ticket, or get help. -> es: Aquí están tus opciones: ver canales, crear un ticket o pedir ayuda."""
        return f"""Translate to {target_language} (code: {lang_code}). Use ONLY {target_language}. If already in {target_language}, repeat it.
- Format: \"{lang_code}: <translation>\"
{examples}

Text: {text}
"""

    def _translate_with_retry(self, text: str, target_language: str) -> Optional[str]:
        """Attempt translation with two increasingly strict prompts."""
        prompts = [
            self._build_translation_prompt(text, target_language),
            self._build_strict_translation_prompt(text, target_language),
            self._build_example_translation_prompt(text, target_language),
        ]
        last_response: Optional[str] = None
        for idx, prompt in enumerate(prompts, start=1):
            translated = self._generate_text(prompt)
            translated = self._strip_prompt_artifacts(translated)
            if translated:
                last_response = translated
            if translated and self._is_in_target_language(translated, target_language):
                return translated
            logger.info(
                "Translation attempt %s did not produce %s. Retrying...",
                idx,
                target_language,
            )

        return last_response or text

    @staticmethod
    def _strip_prompt_artifacts(text: Optional[str]) -> Optional[str]:
        if not text:
            return text
        clean_text = text
        markers = (
            "\nTEXT:",
            "\nINPUT:",
            "\nOUTPUT (translation only):",
            "\nOUTPUT (translation only, with prefix):",
            "\n[Answer]",
            "\n[FORMATTED_SPANISH]",
        )
        for marker in markers:
            idx = clean_text.find(marker)
            if idx != -1:
                clean_text = clean_text[:idx]
        clean_text = clean_text.strip()
        return WatsonxAI._strip_language_prefix(clean_text)

    @staticmethod
    def _strip_language_prefix(text: str) -> str:
        lowered = text.lower()
        prefixes = ("es:", "en:", "pt:", "fr:", "spanish:", "english:", "portuguese:", "french:")
        for prefix in prefixes:
            if lowered.startswith(prefix):
                return text[len(prefix) :].lstrip()
        return text

    def _build_language_control_prompt(
        self,
        user_message: str,
        orchestrate_response: str,
        target_language: str,
    ) -> str:
        """Build the prompt for language control."""
        return f"""You are a language validator. Check if the response is in the correct language and return ONLY the response text.

USER MESSAGE: {user_message}
RESPONSE TO CHECK: {orchestrate_response}
TARGET LANGUAGE: {target_language}

INSTRUCTIONS:
- If response is already in {target_language}: return it EXACTLY as provided
- If response is in wrong language: translate to {target_language}
- Preserve ALL formatting, markdown, emojis, placeholders
- Do NOT shorten, summarize, or omit content
- Return ONLY the final response text
- NO explanations, NO comments, NO meta-text
- Do NOT add phrases like "Here is..." or "(The corrected..."
- Do NOT explain what you did

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
