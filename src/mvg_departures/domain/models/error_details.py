"""Error details domain model."""

from pydantic import BaseModel, ConfigDict


class ErrorDetails(BaseModel):
    """Details about an error, including HTTP status code if applicable."""

    model_config = ConfigDict(frozen=True)

    status_code: int | None = None
    reason: str
