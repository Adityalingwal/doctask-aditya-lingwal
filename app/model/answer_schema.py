from __future__ import annotations

from typing import Any

from pydantic import BaseModel


JSON_SCHEMA_FORMAT = "json_schema"


def strict_answer_format(answer_model: type[BaseModel]) -> dict[str, Any]:
    """The provider's strict `response_format`, generated from the answer model.

    The shape is never written a second time. Whatever the Pydantic model
    validates at the boundary is exactly what the model was asked for, so the
    two cannot drift apart the way a hand-written example in a prompt does.
    """
    return {
        "type": JSON_SCHEMA_FORMAT,
        JSON_SCHEMA_FORMAT: {
            "name": answer_model.__name__,
            "strict": True,
            "schema": _tightened(answer_model.model_json_schema()),
        },
    }


def _tightened(schema: Any) -> Any:
    """Rewrite a generated schema into the subset strict mode accepts.

    Strict mode allows no optional key and no unexpected one: every property
    must be required and every object must refuse what it did not declare. A
    `default` is how Pydantic writes "this key may be missing", so it goes —
    an absent key is not something the boundary should have to guess about.
    """
    if isinstance(schema, list):
        return [_tightened(entry) for entry in schema]
    if not isinstance(schema, dict):
        return schema

    tightened = {
        name: _tightened(value)
        for name, value in schema.items()
        if name != "default"
    }
    if "properties" in tightened:
        tightened["required"] = list(tightened["properties"])
        tightened["additionalProperties"] = False
    return tightened
