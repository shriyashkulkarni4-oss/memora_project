"""Idempotently register Memoryhive Temporal visibility attributes."""

import asyncio

from temporalio.api.enums.v1 import IndexedValueType
from temporalio.api.operatorservice.v1 import (
    AddSearchAttributesRequest,
    ListSearchAttributesRequest,
)
from temporalio.client import Client

from app.config import get_settings

SEARCH_ATTRIBUTES = {
    "MemoryhiveItemType": "INDEXED_VALUE_TYPE_KEYWORD",
    "MemoryhiveTenant": "INDEXED_VALUE_TYPE_KEYWORD",
    "MemoryhiveAnalysisVersion": "INDEXED_VALUE_TYPE_INT",
    "MemoryhiveProvider": "INDEXED_VALUE_TYPE_KEYWORD",
    "MemoryhiveModel": "INDEXED_VALUE_TYPE_KEYWORD",
    "MemoryhiveStage": "INDEXED_VALUE_TYPE_KEYWORD",
    "MemoryhiveOutcome": "INDEXED_VALUE_TYPE_KEYWORD",
}


async def configure_visibility() -> list[str]:
    settings = get_settings()
    client = await Client.connect(
        settings.temporal_address, namespace=settings.temporal_namespace
    )
    current = await client.operator_service.list_search_attributes(
        ListSearchAttributesRequest(namespace=settings.temporal_namespace)
    )
    missing = {
        name: IndexedValueType.Value(value_type)
        for name, value_type in SEARCH_ATTRIBUTES.items()
        if name not in current.custom_attributes
    }
    if missing:
        await client.operator_service.add_search_attributes(
            AddSearchAttributesRequest(
                namespace=settings.temporal_namespace,
                search_attributes=missing,
            )
        )
    return sorted(missing)


def main() -> int:
    added = asyncio.run(configure_visibility())
    print(
        "Temporal search attributes ready"
        + (f"; added: {', '.join(added)}" if added else "; no changes")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
