from dataclasses import dataclass
import os

@dataclass
class WatsonxSettings:
    """Configuration settings for IBM Watsonx Orchestrate integration."""
    api_key: str = os.getenv("WATSONX_ORCHESTRATE_API_KEY", "")
    base_url: str = os.getenv("WATSONX_ORCHESTRATE_URL", "")
    agent_id: str = os.getenv("WATSONX_ORCHESTRATE_AGENT_ID", "")
    token_url: str = os.getenv("WATSONX_TOKEN_URL", "https://iam.cloud.ibm.com/identity/token")
    token_expiration_buffer: int = int(os.getenv("WATSONX_TOKEN_EXPIRATION_BUFFER", "60"))
