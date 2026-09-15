"""Generiert die tatsächlich serialisierten Domänenverträge für TypeScript."""

import json
from pathlib import Path
from typing import Any

from platform_app.data.intelligence_schemas import (
    AnalysisInput,
    PlanInput,
    RuleSetView,
    SourceCatalog,
    SourceImportInput,
    TaskSummary,
    TaskView,
)
from platform_app.data.schemas import (
    ChartSample,
    CommitInput,
    DatasetSummary,
    DatasetView,
    ImportInput,
    ImportOptions,
    JobView,
    PreviewInput,
    UploadInput,
    UploadView,
)
from platform_app.data.schemas import VersionView as DataVersionView
from platform_app.decisions.schemas import (
    AssessmentOptions,
    AssessmentResult,
    ScenarioInput,
)

ROOT = Path(__file__).resolve().parents[1]


def ts(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    if "const" in schema:
        return json.dumps(schema["const"])
    if "enum" in schema:
        return " | ".join(json.dumps(value) for value in schema["enum"])
    if "anyOf" in schema:
        return " | ".join(ts(value) for value in schema["anyOf"])
    kind = schema.get("type")
    if kind == "array":
        return "Array<" + ts(schema["items"]) + ">"
    if kind == "object":
        if "properties" in schema:
            # model_dump(mode=json) liefert auch Felder mit Defaultwert; kein exclude_unset.
            return (
                "{ "
                + " ".join(
                    json.dumps(key) + ": " + ts(value) + ";"
                    for key, value in schema["properties"].items()
                )
                + " }"
            )
        keys = schema.get("propertyNames", {}).get("enum")
        index = " | ".join(json.dumps(key) for key in keys) if keys else "string"
        additional = schema.get("additionalProperties")
        return (
            "Record<"
            + index
            + ", "
            + (ts(additional) if isinstance(additional, dict) else "unknown")
            + ">"
        )
    return {
        "string": "string",
        "integer": "number",
        "number": "number",
        "boolean": "boolean",
        "null": "null",
    }.get(kind, "unknown")


def main() -> None:
    models: dict[str, Any] = {}
    for model in (
        ChartSample,
        ImportOptions,
        ScenarioInput,
        AssessmentOptions,
        AssessmentResult,
        DatasetView,
        DatasetSummary,
        JobView,
        DataVersionView,
        ImportInput,
        UploadInput,
        UploadView,
        PreviewInput,
        ChartSample,
        CommitInput,
        AnalysisInput,
        RuleSetView,
        PlanInput,
        SourceCatalog,
        SourceImportInput,
        TaskView,
        TaskSummary,
    ):
        schema = model.model_json_schema(mode="serialization")
        models.update(schema.pop("$defs", {}))
        models[model.__name__] = schema
    output = (
        "// Automatisch erzeugt: python scripts/generate_contracts.py. Nicht manuell bearbeiten.\n"
    )
    output += (
        "\n".join(
            "export type " + name + " = " + ts(schema) + ";"
            for name, schema in sorted(models.items())
        )
        + "\n"
    )
    destination = ROOT / "apps/web/src/generated/domain.ts"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(output, encoding="utf8")
    (ROOT / "docs/contracts").mkdir(exist_ok=True)
    (ROOT / "docs/contracts/domain.schema.json").write_text(
        json.dumps(models, indent=2, ensure_ascii=False) + "\n", encoding="utf8"
    )
    print("Serialisierte Domänenverträge generiert.")


if __name__ == "__main__":
    main()
