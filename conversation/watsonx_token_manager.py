import logging
import time
import requests
from .watsonx_settings import WatsonxSettings

logger = logging.getLogger(__name__)

class WatsonxTokenManager:
    """Handles token caching and refreshing for Watsonx."""
    def __init__(self, settings: WatsonxSettings):
        self.settings = settings
        self._token = None
        self._token_expires_at = 0

    def get_token(self) -> str:
        """Return a valid token, refreshing it if needed."""
        now = time.time()
        if (
            not self._token
            or now >= self._token_expires_at - self.settings.token_expiration_buffer
        ):
            logger.info("Token missing or expired; requesting a new IAM token.")
            self._refresh_token()
        else:
            remaining = int(self._token_expires_at - now)
            logger.debug("Reusing IAM token; %s seconds remaining.", remaining)
        return self._token

    def _refresh_token(self):
        """Request a new token from IBM IAM."""
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={self.settings.api_key}"
        logger.debug("Requesting IAM token from %s", self.settings.token_url)
        try:
            response = requests.post(self.settings.token_url, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as exc:
            logger.exception("Error requesting IAM token: %s", exc)
            raise

        self._token = payload["access_token"]
        expires_in = payload.get("expires_in", 3600)
        self._token_expires_at = time.time() + expires_in
        logger.info("IAM token renewed. Expires in %s seconds.", expires_in)
