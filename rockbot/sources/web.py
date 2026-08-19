from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from .base import DataSource, PetNotFound, SourceError
from rockbot.models import PetProfile


@dataclass(slots=True)
class WebSourceConfig:
    name: str
    url_template: str
    timeout_seconds: float = 8.0


class ConfigurableWebSource(DataSource):
    """Fetch JSON pet profiles from a configured URL template.

    The first real scraper can replace this class or feed it with a local proxy.
    Expected JSON shape matches PetProfile.to_dict().
    """

    def __init__(self, config: WebSourceConfig) -> None:
        self.config = config
        self.name = config.name

    def fetch(self, pet_name: str) -> PetProfile:
        encoded = urllib.parse.quote(pet_name)
        url = self.config.url_template.format(pet_name=encoded)
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "rock-kingdom-qq-bot/0.1"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                if response.status == 404:
                    raise PetNotFound(f"{pet_name} not found")
                if response.status >= 400:
                    raise SourceError(f"HTTP {response.status}")
                payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise PetNotFound(f"{pet_name} not found") from exc
            raise SourceError(f"HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise SourceError(str(exc.reason)) from exc
        except TimeoutError as exc:
            raise SourceError("request timed out") from exc

        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise SourceError("source did not return valid JSON") from exc
        profile = PetProfile.from_dict(data)
        if not profile.name:
            profile.name = pet_name
        return profile
