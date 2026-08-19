from __future__ import annotations

from abc import ABC, abstractmethod

from rockbot.models import PetProfile


class SourceError(RuntimeError):
    """Raised when a configured data source fails unexpectedly."""


class PetNotFound(SourceError):
    """Raised when a pet cannot be found in a source."""


class DataSource(ABC):
    name = "base"

    @abstractmethod
    def fetch(self, pet_name: str) -> PetProfile:
        raise NotImplementedError
