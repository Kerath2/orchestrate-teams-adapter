from dataclasses import dataclass, field
import os


@dataclass
class WatsonxAISettings:
    """Configuration settings for IBM Watsonx.ai integration."""
    api_key: str = field(default_factory=lambda: os.getenv("WX_APIKEY", ""))
    project_id: str = field(default_factory=lambda: os.getenv("WX_PROJECT_ID", ""))
    max_concurrent: int = field(default_factory=lambda: int(os.getenv("WX_MAX_CONCURRENT", "7")))
    url: str = field(default_factory=lambda: os.getenv("WX_URL", "https://us-south.ml.cloud.ibm.com"))
    token_url: str = field(default_factory=lambda: os.getenv("WX_TOKEN_URL", "https://iam.cloud.ibm.com/identity/token"))

    # Model configuration
    model_id: str = field(default_factory=lambda: os.getenv("WX_MODEL_ID", "ibm/granite-3-8b-instruct"))
    max_new_tokens: int = field(default_factory=lambda: int(os.getenv("WX_MAX_NEW_TOKENS", "2000")))
    temperature: float = field(default_factory=lambda: float(os.getenv("WX_TEMPERATURE", "0.3")))

    def is_enabled(self) -> bool:
        """Check if Watsonx.ai is properly configured."""
        return bool(self.api_key and self.project_id)
