import os
from functools import lru_cache
from typing import Any

import yaml


@lru_cache(maxsize=1)
def _load() -> dict[str, Any]:
    path = os.path.join(os.path.dirname(__file__), "config", "form_config.yml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def patient_form_fields() -> list[dict[str, Any]]:
    return _load()["patient_form"]["fields"]
