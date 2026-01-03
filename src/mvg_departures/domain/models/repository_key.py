"""Repository key domain model for composite repository caching."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RepositoryKey:
    """Key for identifying a repository by API provider.

    Used as a cache key in composite repository to avoid creating duplicate
    repository instances for the same API provider.
    """

    api_provider: str
