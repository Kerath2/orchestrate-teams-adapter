from dataclasses import dataclass, field
import os

@dataclass
class WatsonxSettings:
    """Configuration settings for IBM Watsonx Orchestrate integration."""
    api_key: str = field(default_factory=lambda: os.getenv("WATSONX_ORCHESTRATE_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("WATSONX_ORCHESTRATE_URL", ""))
    agent_id: str = field(default_factory=lambda: os.getenv("WATSONX_ORCHESTRATE_AGENT_ID", ""))
    token_url: str = field(default_factory=lambda: os.getenv("WATSONX_TOKEN_URL", "https://iam.cloud.ibm.com/identity/token"))
    token_expiration_buffer: int = field(default_factory=lambda: int(os.getenv("WATSONX_TOKEN_EXPIRATION_BUFFER", "60")))
