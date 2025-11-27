from dataclasses import dataclass
from typing import Optional
import os, ssl

@dataclass
class RedisSessionSettings:
    """Configuration object for Redis connection and session behavior."""

    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", 6379))
    db: int = int(os.getenv("REDIS_DB", 0))
    username: Optional[str] = os.getenv("REDIS_USERNAME", None)
    password: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    ssl: bool = os.getenv("REDIS_SSL", "false").lower() == "true"
    ssl_ca_certs: Optional[str] = os.getenv("REDIS_SSL_CA_CERTS", None)

    def as_dict(self) -> dict:
        """Return configuration as a dictionary, useful for Redis client initialization."""
        d = {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "username": self.username,
            "password": self.password,
            "decode_responses": True,
            "ssl": True, 
            "ssl_cert_reqs": ssl.CERT_NONE
        }

        return d