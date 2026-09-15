"""Versionierte, ausdrücklich synthetische Katalogwerte."""

import json
from importlib.resources import files
from typing import Any, cast

RULE_VERSION = "rules-1.1.0"


def load_catalog() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(files("platform_app.decisions").joinpath("catalog.json").read_text("utf8")),
    )


def catalog_metadata() -> dict[str, Any]:
    source = load_catalog()
    return {
        **source,
        "rule_set_version": RULE_VERSION,
        "candidate_catalog_version": source["version"],
        "cost_catalog_version": source["version"],
    }
