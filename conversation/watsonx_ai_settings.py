from dataclasses import dataclass
import os


@dataclass
class WatsonxAISettings:
    """Configuration settings for IBM Watsonx.ai integration."""
    api_key: str = os.getenv("WX_APIKEY", "")
    project_id: str = os.getenv("WX_PROJECT_ID", "")
    max_concurrent: int = int(os.getenv("WX_MAX_CONCURRENT", "7"))
    url: str = os.getenv("WX_URL", "https://us-south.ml.cloud.ibm.com")
    token_url: str = os.getenv("WX_TOKEN_URL", "https://iam.cloud.ibm.com/identity/token")

    # Model configuration
    model_id: str = os.getenv("WX_MODEL_ID", "ibm/granite-3-8b-instruct")
    max_new_tokens: int = int(os.getenv("WX_MAX_NEW_TOKENS", "2000"))
    temperature: float = float(os.getenv("WX_TEMPERATURE", "0.3"))

    def is_enabled(self) -> bool:
        """Check if Watsonx.ai is properly configured."""
        return bool(self.api_key and self.project_id)
