"""Coarse-facade MCP server over a frozen data-context corpus snapshot.

Eval-harness artifact (fathom bank ``dc-granularity-v1``, COARSE arm) — not
part of the data-context product surface. It exposes the same underlying facts
as the product's twelve-tool surface through THREE merged tools:

* ``find_data``        — one search over datasets AND glossary terms
* ``describe_dataset`` — one composite digest per dataset (properties, schema,
                         lineage, business rules, inlined term definitions,
                         freshness verdict, serving instructions)
* ``corpus_status``    — manifest provenance + snapshot-staleness verdict

It is built on the same ``LocalCorpusBackend``, freshness engine, actuation
resolution, and provenance envelope as the fine arm, so the two arms differ
ONLY in tool granularity, never in available facts. ``argv[1]`` = corpus
directory (the plugin-local frozen snapshot).
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from data_context.actuation import locator_for
from data_context.backend.local import LocalCorpusBackend
from data_context.canonical.corpus import Entity
from data_context.errors import (
    AmbiguousAssertionError,
    ErrorPayload,
    UnknownDatasetError,
    UnresolvedLocatorError,
    to_error_payload,
)
from data_context.freshness import (
    FreshnessVerdict,
    SnapshotFreshness,
    evaluate_freshness,
    evaluate_snapshot,
    find_freshness_assertion,
)
from data_context.producers.treasuryutils import PRODUCER_ID as _DEFAULT_PRODUCER_ID
from data_context.provenance import (
    CorpusManifest,
    Coverage,
    DiscoveryResponse,
    EntityResult,
    build_entity_result,
    build_response,
    load_verified,
)
from data_context.server import _aliases, _find_by_serving_name, _observe_latest


class FindHit(BaseModel):
    """One search hit: a dataset or a glossary term, labeled by kind."""

    kind: Literal["dataset", "glossary_term"]
    name: str | None
    text: str | None


class TermDigest(BaseModel):
    """A glossary term attached to a dataset, with its definition inlined."""

    urn: str
    name: str | None
    definition: str | None


class SchemaFieldDigest(BaseModel):
    """One schema field of a dataset."""

    field_path: str
    native_data_type: str
    description: str | None


class DatasetDigest(BaseModel):
    """Everything the corpus knows about one dataset, in a single payload."""

    name: str | None
    description: str | None
    custom_properties: dict[str, str]
    schema_fields: list[SchemaFieldDigest]
    upstream: list[str]
    downstream: list[str]
    terms: list[TermDigest]
    freshness: FreshnessVerdict
    producer_id: str
    locator: str | None
    aliases: list[str]


async def _resolve_ref(backend: LocalCorpusBackend, ref: str) -> Entity | None:
    """Resolve `ref` — a dataset URN, a serving locator, or an alias — to its entity."""
    if ref.startswith("urn:li:"):
        return await backend.get_entity(ref)
    entity = await _find_by_serving_name(backend, ref)
    if entity is None:
        entity = await backend.get_entity(ref)
    return entity


def create_coarse_server(
    backend: LocalCorpusBackend,
    manifest: CorpusManifest,
    name: str = "data-context",
) -> FastMCP:
    """Build the coarse three-tool facade over `backend` and `manifest`."""
    server = FastMCP(name)

    @server.tool()
    async def find_data(
        query: str,
        limit: int = 20,
    ) -> DiscoveryResponse[FindHit] | ErrorPayload:
        """Search the whole catalog — datasets AND glossary terms — for entities
        matching every whitespace-split token of `query`. Each hit is labeled
        `dataset` (with its description) or `glossary_term` (with its full
        definition). Use `describe_dataset` on a dataset hit for details."""
        hits: list[EntityResult[FindHit]] = []
        for entity in await backend.search_datasets(query, limit=limit):
            props = entity.dataset_properties
            hits.append(
                build_entity_result(
                    entity,
                    FindHit(
                        kind="dataset",
                        name=props.name if props else None,
                        text=props.description if props else None,
                    ),
                )
            )
        for entity in await backend.search_terms(query, limit=limit):
            info = entity.glossary_term_info
            hits.append(
                build_entity_result(
                    entity,
                    FindHit(
                        kind="glossary_term",
                        name=info.name if info else None,
                        text=info.definition if info else None,
                    ),
                )
            )
        return build_response(manifest, hits)

    @server.tool()
    async def describe_dataset(
        ref: str,
        lineage_hops: int = 1,
        observed_as_of: datetime | None = None,
    ) -> DiscoveryResponse[DatasetDigest] | ErrorPayload:
        """Return everything known about one dataset in a single digest:
        properties and business rules (customProperties), schema fields,
        upstream/downstream lineage URNs within `lineage_hops`, attached
        glossary terms with their definitions inlined, a freshness verdict
        against the dataset's FRESHNESS assertion (pass `observed_as_of` — a
        timezone-aware ISO timestamp — to evaluate a known observation), and
        serving instructions (producer id + locator + aliases). `ref` accepts
        a dataset URN, a serving locator, or an alias."""
        entity = await _resolve_ref(backend, ref)
        if entity is None:
            return to_error_payload(UnknownDatasetError(f"unknown dataset: {ref}"))
        urn = entity.entity_urn

        props = entity.dataset_properties
        custom = props.custom_properties if props else {}

        schema = entity.schema_metadata
        schema_fields = [
            SchemaFieldDigest(
                field_path=field.field_path,
                native_data_type=field.native_data_type,
                description=field.description,
            )
            for field in (schema.fields if schema else [])
        ]

        terms: list[TermDigest] = []
        if entity.glossary_terms is not None:
            for association in entity.glossary_terms.terms:
                term_entity = await backend.get_entity(association.urn)
                info = term_entity.glossary_term_info if term_entity else None
                terms.append(
                    TermDigest(
                        urn=association.urn,
                        name=info.name if info else None,
                        definition=info.definition if info else None,
                    )
                )

        try:
            assertion_entity = find_freshness_assertion(await backend.list_entities(), urn)
        except AmbiguousAssertionError as exc:
            return ErrorPayload(code="ambiguous_assertion", message=str(exc))
        assertion = assertion_entity.assertion_info if assertion_entity else None
        no_observation_reason = "no_observation"
        observed = observed_as_of
        if observed is None:
            observed, no_observation_reason = await _observe_latest(entity, urn)
        try:
            freshness = evaluate_freshness(
                assertion,
                observed,
                now=datetime.now(UTC),
                no_observation_reason=no_observation_reason,
            )
        except ValueError as exc:
            return ErrorPayload(code="naive_datetime", message=str(exc))

        try:
            locator: str | None = locator_for(props, urn)
        except UnresolvedLocatorError:
            locator = None

        digest = DatasetDigest(
            name=props.name if props else None,
            description=props.description if props else None,
            custom_properties=custom,
            schema_fields=schema_fields,
            upstream=await backend.get_upstream(urn, max_hops=lineage_hops),
            downstream=await backend.get_downstream(urn, max_hops=lineage_hops),
            terms=terms,
            freshness=freshness,
            producer_id=custom.get("serving.producer") or _DEFAULT_PRODUCER_ID,
            locator=locator,
            aliases=_aliases(custom),
        )
        return build_response(manifest, [build_entity_result(entity, digest)])

    @server.tool()
    async def corpus_status() -> DiscoveryResponse[SnapshotFreshness] | ErrorPayload:
        """Return the metadata snapshot's provenance (producer source version,
        emit timestamp, corpus id, max-age policy) plus a snapshot-staleness
        verdict — how stale the snapshot itself is, distinct from any one
        dataset's freshness."""
        verdict = evaluate_snapshot(manifest, now=datetime.now(UTC))
        result = EntityResult(
            entity_urn="-",
            entity_type="corpus",
            coverage=Coverage(aspects={}, unknown_aspects=[]),
            result=verdict,
        )
        return build_response(manifest, [result])

    return server


def main() -> None:
    corpus_dir = Path(sys.argv[1])
    backend = LocalCorpusBackend(load_verified(corpus_dir))
    manifest = CorpusManifest.load(corpus_dir)
    create_coarse_server(backend, manifest).run()


if __name__ == "__main__":
    main()
