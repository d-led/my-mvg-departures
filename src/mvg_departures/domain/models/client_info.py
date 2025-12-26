"""Client information domain model."""

from pydantic import BaseModel, ConfigDict


class ClientInfo(BaseModel):
    """Client information extracted from request headers."""

    model_config = ConfigDict(frozen=True)

    ip: str
    user_agent: str
    browser_id: str
