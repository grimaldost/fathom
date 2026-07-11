# ruff: noqa: ANN401, PERF401, D103
# Vendored from the user-level treasuryutils-usage skill; runs ad-hoc to
# regenerate reference markdown. Introspection requires dynamic typing.
"""Generate domain-split API reference files for the treasuryutils-usage skill.

Introspects the installed ``treasuryutils`` package and produces one markdown
reference file per domain, plus a YAML contracts reference.

Usage::

    uv run python .claude/skills/treasuryutils-usage/scripts/generate_references.py \
        --output-dir .claude/skills/treasuryutils-usage/references/
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import enum
import importlib
import importlib.metadata
import inspect
import json
import pkgutil
import re
import socket
import sys
import types
from pathlib import Path
from textwrap import dedent
from typing import Any, Literal, Union, get_args, get_origin

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TARGET_PREFIXES = (
    'treasuryutils.datatools',
    'treasuryutils.calendartools',
    'treasuryutils.authenticator',
    'treasuryutils.financialtools',
    'treasuryutils.compute',
    'treasuryutils.common',
    'treasuryutils.config',
    'treasuryutils.logging_config',
    'treasuryutils.quanttools',
    'treasuryutils.equitytools',
    'treasuryutils.capitaltools',
)

DOMAIN_ROUTING: dict[str, str] = {
    'treasuryutils.datatools': 'datatools',
    'treasuryutils.calendartools': 'calendartools',
    'treasuryutils.authenticator': 'authenticator',
    'treasuryutils.financialtools': 'financialtools',
    'treasuryutils.compute': 'compute_common',
    'treasuryutils.common': 'compute_common',
    'treasuryutils.config': 'datatools',
    'treasuryutils.logging_config': 'datatools',
    'treasuryutils.quanttools': 'quanttools',
    'treasuryutils.equitytools': 'equitytools',
    'treasuryutils.capitaltools': 'capitaltools',
}

DOMAIN_TITLES: dict[str, str] = {
    'datatools': 'DataTools API Reference',
    'calendartools': 'CalendarTools API Reference',
    'authenticator': 'Authenticator API Reference',
    'financialtools': 'FinancialTools API Reference',
    'compute_common': 'Compute & Common API Reference',
    'quanttools': 'QuantTools API Reference',
    'equitytools': 'EquityTools API Reference',
    'capitaltools': 'CapitalTools API Reference',
}

DOMAIN_EXTRAS: dict[str, str] = {
    'datatools': 'treasuryutils[datatools]',
    'calendartools': 'treasuryutils[calendartools]',
    'authenticator': 'treasuryutils (core)',
    'financialtools': 'treasuryutils[pricing]',
    'compute_common': 'treasuryutils (core)',
    'quanttools': 'treasuryutils[datatools,quant-math,quant-optimizer]',
    'equitytools': 'treasuryutils[datatools,quant-math,quant-optimizer]',
    'capitaltools': 'treasuryutils[datatools,quant-math,quant-optimizer]',
}

DEFAULT_TTL_HOURS = 168
STALE_EXIT_CODE = 3
MISSING_PACKAGE_EXIT_CODE = 2

# Number of generated reference mirrors: 8 per-domain API files — authenticator,
# calendartools, capitaltools, compute_common, datatools, equitytools,
# financialtools, quanttools — plus yaml_contracts.md.
# ``--check`` enforces this count exactly: a generation failure that would drop one
# is rc 1, never a silent skip.
EXPECTED_REFERENCE_COUNT = 9

# The two volatile stamp lines stripped before a content comparison (they encode
# the version + generation time and differ on every run / environment).
_STAMP_LINE_PREFIXES = ('- treasuryutils_version:', '- generated_at_utc:')

# ---------------------------------------------------------------------------
# YAML-specific constants (ported from Codex yaml_index script)
# ---------------------------------------------------------------------------

SERVING_ALIASES: dict[str, str] = {
    'artifact': 'artifact_kind',
    'parquet_partition_by': 'partition_by',
    'persist': 'persist_artifacts',
    'use_existing': 'use_existing_artifacts',
}

SOURCE_DRIVER_RULES: dict[str, dict[str, Any]] = {
    'rest_api': {
        'required_config_fields': ['base_url', 'endpoint'],
        'requires_query': False,
        'notes': [
            'request_headers must be dict[str, str] when provided',
            'request_params must be dict with string keys',
            'response.metadata_fields is only valid for JSON format',
            'params.date_param cannot be combined with params.start_param/params.end_param',
        ],
    },
    'file': {
        'required_config_fields': ['path'],
        'requires_query': False,
        'notes': ['path must be provided in source.config'],
    },
    'bigquery': {
        'required_config_fields': [],
        'requires_query': False,
        'notes': ['No model-level required config keys; query may be provided per source/query.'],
    },
    'databricks': {
        'required_config_fields': ['warehouse_id'],
        'requires_query': True,
        'notes': ['source.query is required for databricks sources'],
    },
    'python': {
        'required_config_fields': ['class_path'],
        'requires_query': False,
        'notes': ['class_path must resolve to an importable builder class'],
    },
    'dataset': {
        'required_config_fields': ['dataset_name'],
        'requires_query': False,
        'notes': ['dataset_name must reference an existing upstream dataset'],
    },
}

YAML_TEMPLATES: list[dict[str, Any]] = [
    {
        'name': 'rest_api',
        'snippet': dedent("""\
            dataset_name: external_rates
            source:
              type: rest_api
              config:
                base_url: https://api.example.com
                endpoint: /v1/rates"""),
        'required_fields': [
            'dataset_name',
            'source.type',
            'source.config.base_url',
            'source.config.endpoint',
        ],
        'common_errors': [
            "missing 'base_url' or 'endpoint'",
            'date_param combined with start_param/end_param',
        ],
    },
    {
        'name': 'file',
        'snippet': dedent("""\
            dataset_name: local_positions
            source:
              type: file
              config:
                path: ./data/positions.parquet"""),
        'required_fields': ['dataset_name', 'source.type', 'source.config.path'],
        'common_errors': ["missing 'path' in source.config"],
    },
    {
        'name': 'bigquery',
        'snippet': dedent("""\
            dataset_name: warehouse_balances
            source:
              type: bigquery
              query: SELECT * FROM project.dataset.table
              config:
                project: my-project"""),
        'required_fields': ['dataset_name', 'source.type'],
        'common_errors': ['omitting query when no provider-side defaults exist'],
    },
    {
        'name': 'databricks',
        'snippet': dedent("""\
            dataset_name: dbx_positions
            source:
              type: databricks
              query: SELECT * FROM catalog.schema.table
              config:
                warehouse_id: abc123def456"""),
        'required_fields': [
            'dataset_name',
            'source.type',
            'source.query',
            'source.config.warehouse_id',
        ],
        'common_errors': ["missing 'warehouse_id'", 'missing source.query for databricks'],
    },
    {
        'name': 'python',
        'snippet': dedent("""\
            dataset_name: custom_source_dataset
            source:
              type: python
              config:
                class_path: my_package.builders.CustomBuilder"""),
        'required_fields': ['dataset_name', 'source.type', 'source.config.class_path'],
        'common_errors': ["missing 'class_path' in source.config"],
    },
    {
        'name': 'dataset',
        'snippet': dedent("""\
            dataset_name: downstream_enriched
            source:
              type: dataset
              config:
                dataset_name: upstream_base"""),
        'required_fields': ['dataset_name', 'source.type', 'source.config.dataset_name'],
        'common_errors': ["missing 'dataset_name' in source.config for dataset source"],
    },
]

YAML_PITFALLS = [
    "'dataset_name' and 'cache_table_name' must be snake_case (validated by TABLE_NAME_RE)",
    "'databricks' source requires both 'source.config.warehouse_id' and 'source.query'",
    "'params.date_param' cannot be combined with 'params.start_param' or 'params.end_param'",
    "'response.metadata_fields' is only valid when response.format is 'json'",
    "'params.chunk_days' must be a positive integer when provided",
    "'serving' aliases are accepted but normalized to canonical field names",
]

# ---------------------------------------------------------------------------
# Introspection utilities (ported from Codex api_index script)
# ---------------------------------------------------------------------------


def _module_is_target(name: str) -> bool:
    return any(name == prefix or name.startswith(prefix + '.') for prefix in TARGET_PREFIXES)


def _is_public_module(name: str) -> bool:
    parts = name.split('.')
    return all(not part.startswith('_') for part in parts[1:])


def _safe_signature(obj: Any, *, drop_self: bool = False) -> str:
    try:
        signature = inspect.signature(obj)
        normalized_params = []
        for parameter in signature.parameters.values():
            if parameter.default is inspect._empty:
                normalized_params.append(parameter)
            else:
                normalized_params.append(parameter.replace(default=inspect._empty))
        if drop_self and normalized_params and normalized_params[0].name in ('self', 'cls'):
            normalized_params = normalized_params[1:]
        signature = signature.replace(parameters=normalized_params)
        return str(signature)
    except (TypeError, ValueError):
        return '(...)'


def _doc_first_line(obj: Any) -> str:
    doc = inspect.getdoc(obj) or ''
    return doc.splitlines()[0].strip() if doc else ''


def _input_columns_clause(obj: Any) -> str:
    """Render a function's declared ``__tu_input_columns__`` contract as a clause.

    Frame-shaped functions decorated with
    ``treasuryutils.compute._contracts.document_input_columns`` carry a per-parameter
    DataFrame-column contract; this surfaces it in the reference so a caller sees the
    required columns instead of discovering them as a ColumnNotFoundError at runtime.
    Returns '' for every other symbol (the common case), so only those few rows change.
    """
    contracts = getattr(obj, '__tu_input_columns__', None)
    if not isinstance(contracts, dict) or not contracts:
        return ''
    parts: list[str] = []
    for param, contract in contracts.items():
        required = tuple(getattr(contract, 'required', ()) or ())
        optional = tuple(getattr(contract, 'optional', ()) or ())
        note = (getattr(contract, 'note', '') or '').strip()
        inner = ', '.join(required)
        if optional:
            opt = 'optional: ' + ', '.join(optional)
            inner = f'{inner} ({opt})' if inner else opt
        if note:
            inner = f'{inner} -- {note}' if inner else note
        parts.append(f'{param}{{{inner}}}')
    return ' · Input columns: ' + '; '.join(parts)


def _symbol_kind(obj: Any) -> str:
    if inspect.isclass(obj):
        return 'class'
    if inspect.isfunction(obj):
        return 'function'
    if inspect.ismethod(obj):
        return 'method'
    if callable(obj):
        return 'callable'
    return 'object'


def _symbol_identity(obj: Any) -> str:
    """Stable cross-module identity for re-export / alias detection."""
    module = getattr(obj, '__module__', '') or ''
    qualname = getattr(obj, '__qualname__', None) or getattr(obj, '__name__', '')
    return f'{module}.{qualname}'


def _enum_member_summary(cls: type[enum.Enum]) -> str:
    """Render an enum's members as ``NAME=<value!r>`` pairs.

    ``inspect.signature`` on an ``Enum`` class returns the useless
    ``EnumMeta.__call__`` metaclass signature
    (``(value, names, *, module, qualname, ...)``); a consumer needs the actual
    member set instead.
    """
    return ', '.join(f'{member.name}={member.value!r}' for member in cls)


def _public_methods(cls: Any) -> list[tuple[str, Any]]:
    """Public methods DEFINED in the treasuryutils package on *cls*.

    Filters to members whose ``__module__`` is within ``TARGET_PREFIXES`` so
    inherited stdlib / pydantic / object methods are excluded — the result is the
    class's own API surface (e.g. ``DatasetClient.get`` / ``.update``), not
    ``model_dump`` and friends.
    """
    methods: list[tuple[str, Any]] = []
    try:
        members = inspect.getmembers(cls)
    except Exception:  # introspection must never crash generation
        return methods
    for mname, member in members:
        if mname.startswith('_'):
            continue
        if not (inspect.isfunction(member) or inspect.ismethod(member)):
            continue
        owner = getattr(member, '__module__', '') or ''
        if not any(owner == prefix or owner.startswith(prefix + '.') for prefix in TARGET_PREFIXES):
            continue
        methods.append((mname, member))
    methods.sort(key=lambda item: item[0].lower())
    return methods


def _public_symbol_names(module: Any) -> list[str]:
    all_names = getattr(module, '__all__', None)
    if isinstance(all_names, (list, tuple)):
        return [name for name in all_names if isinstance(name, str) and not name.startswith('_')]
    return [name for name in dir(module) if not name.startswith('_')]


def _collect_module_symbols(module_name: str) -> dict[str, Any]:
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        return {'import_error': f'{type(exc).__name__}: {exc}', 'symbols': []}

    symbols: list[dict[str, str]] = []
    explicit = isinstance(getattr(module, '__all__', None), (list, tuple))

    for name in _public_symbol_names(module):
        try:
            obj = getattr(module, name)
        except Exception:  # noqa: S112
            continue

        if not explicit:
            obj_mod = getattr(obj, '__module__', '')
            if not (obj_mod == module_name or obj_mod.startswith(module_name + '.')):
                continue

        if not callable(obj) and not inspect.isclass(obj):
            continue

        # Enums introspect to the ``EnumMeta.__call__`` metaclass signature, which is
        # noise; render their members instead and skip the method emission below.
        if inspect.isclass(obj) and issubclass(obj, enum.Enum):
            symbols.append(
                {
                    'name': name,
                    'kind': 'enum',
                    'signature': _enum_member_summary(obj),
                    'doc': _doc_first_line(obj),
                    'identity': _symbol_identity(obj),
                    'real_name': getattr(obj, '__name__', name),
                }
            )
            continue

        symbols.append(
            {
                'name': name,
                'kind': _symbol_kind(obj),
                'signature': _safe_signature(obj),
                'doc': _doc_first_line(obj),
                'identity': _symbol_identity(obj),
                'real_name': getattr(obj, '__name__', name),
                'input_columns': _input_columns_clause(obj),
            }
        )

        # For classes, also emit the public methods defined in the library so
        # method-based APIs (e.g. DatasetClient.get / DatasetHandle.collect) are
        # documented, not just the constructor.
        if inspect.isclass(obj):
            for method_name, method in _public_methods(obj):
                symbols.append(
                    {
                        'name': f'{name}.{method_name}',
                        'kind': _symbol_kind(method),
                        'signature': _safe_signature(method, drop_self=True),
                        'doc': _doc_first_line(method),
                    }
                )

    symbols.sort(key=lambda item: item['name'].lower())
    return {'symbols': symbols}


def _discover_modules() -> list[str]:
    root = importlib.import_module('treasuryutils')
    modules: set[str] = set()

    if hasattr(root, '__path__'):
        for entry in pkgutil.walk_packages(root.__path__, prefix='treasuryutils.'):
            name = entry.name
            if not _module_is_target(name):
                continue
            if not _is_public_module(name):
                continue
            modules.add(name)

    for prefix in TARGET_PREFIXES:
        modules.add(prefix)

    return sorted(modules)


def _safe_treasuryutils_version() -> str:
    try:
        return importlib.metadata.version('treasuryutils')
    except importlib.metadata.PackageNotFoundError:
        return 'unknown'


def _route_module_to_domain(module_name: str) -> str:
    """Map a module name to its domain key."""
    for prefix, domain in sorted(DOMAIN_ROUTING.items(), key=lambda x: -len(x[0])):
        if module_name == prefix or module_name.startswith(prefix + '.'):
            return domain
    return 'datatools'


# ---------------------------------------------------------------------------
# YAML model introspection (ported from Codex yaml_index script)
# ---------------------------------------------------------------------------


def _type_to_str(annotation: Any) -> str:
    if annotation is None:
        return 'None'
    if annotation is Any:
        return 'Any'
    if isinstance(annotation, type):
        return annotation.__name__
    text = str(annotation)
    return text.replace('typing.', '')


def _extract_literal_values(annotation: Any) -> list[str]:
    origin = get_origin(annotation)
    if origin is Literal:
        return [repr(arg) for arg in get_args(annotation)]
    if origin in (Union, types.UnionType):
        values: list[str] = []
        for arg in get_args(annotation):
            values.extend(_extract_literal_values(arg))
        return sorted(set(values))
    return []


def _constraints_from_metadata(metadata: list[Any]) -> dict[str, Any]:
    constraints: dict[str, Any] = {}
    for item in metadata:
        for attr in ('ge', 'gt', 'le', 'lt', 'min_length', 'max_length', 'pattern'):
            if hasattr(item, attr):
                value = getattr(item, attr)
                if value is not None:
                    constraints[attr] = value
    return constraints


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    return repr(value)


def _field_default_value(field: Any) -> tuple[Any, str]:
    if field.is_required():
        return None, '(required)'
    factory = getattr(field, 'default_factory', None)
    if factory is not None:
        factory_name = getattr(factory, '__name__', 'callable')
        return {'default_factory': factory_name}, f'<factory:{factory_name}>'
    return _json_safe(field.default), repr(field.default)


def _field_aliases(model_name: str, field_name: str, field: Any) -> list[str]:
    aliases: list[str] = []
    alias = getattr(field, 'alias', None)
    if isinstance(alias, str) and alias and alias != field_name:
        aliases.append(alias)
    if model_name == 'ServingConfig':
        aliases.extend(
            alias_key for alias_key, target in SERVING_ALIASES.items() if target == field_name
        )
    return sorted(set(aliases))


def _extract_model(model_name: str, model_cls: Any) -> dict[str, Any]:
    fields_payload: list[dict[str, Any]] = []
    model_fields = getattr(model_cls, 'model_fields', {})

    for field_name, field in model_fields.items():
        default_value, default_display = _field_default_value(field)
        literals = _extract_literal_values(field.annotation)
        constraints = _constraints_from_metadata(list(getattr(field, 'metadata', [])))

        fields_payload.append(
            {
                'name': field_name,
                'type': _type_to_str(field.annotation),
                'required': field.is_required(),
                'default': default_value,
                'default_display': default_display,
                'description': field.description or '',
                'literals': literals,
                'aliases': _field_aliases(model_name, field_name, field),
                'constraints': constraints,
            }
        )

    return {
        'name': model_name,
        'doc': (inspect.getdoc(model_cls) or '').splitlines()[0].strip()
        if inspect.getdoc(model_cls)
        else '',
        'fields': sorted(fields_payload, key=lambda item: item['name']),
    }


def _known_validators(models_mod: Any, validation_mod: Any) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []

    for name, obj in inspect.getmembers(validation_mod, inspect.isfunction):
        if name.startswith('validate_') or name == 'resolve_schema_mode':
            doc = inspect.getdoc(obj) or ''
            result.append(
                {
                    'name': name,
                    'where': 'treasuryutils.datatools.config.validation',
                    'purpose': doc.splitlines()[0].strip() if doc else 'No docstring.',
                }
            )

    for label, attr in [
        ('SourceConfig.validate_driver_config', 'validate_driver_config'),
        ('ServingConfig._accept_aliases', '_accept_aliases'),
        ('DatasetConfig._normalize_cache_table_name', '_normalize_cache_table_name'),
    ]:
        model_name = label.split('.')[0]
        model_cls = getattr(models_mod, model_name, None)
        method = getattr(model_cls, attr, None) if model_cls else None
        if method is not None:
            doc = inspect.getdoc(method) or ''
            result.append(
                {
                    'name': label,
                    'where': 'treasuryutils.datatools.config.models',
                    'purpose': doc.splitlines()[0].strip() if doc else 'No docstring.',
                }
            )

    result.sort(key=lambda item: item['name'])
    return result


# ---------------------------------------------------------------------------
# Markdown rendering -- per-domain API files
# ---------------------------------------------------------------------------


def _md_escape(text: str) -> str:
    return text.replace('|', '\\|').replace('\n', ' ')


def _is_type_alias_annotation(annotation: ast.expr) -> bool:
    """True if an annotation is ``TypeAlias`` (bare or ``typing.TypeAlias``)."""
    if isinstance(annotation, ast.Name):
        return annotation.id == 'TypeAlias'
    return isinstance(annotation, ast.Attribute) and annotation.attr == 'TypeAlias'


def _parse_type_aliases(module_name: str) -> dict[str, str]:
    """Resolve ``X: TypeAlias = ...`` definitions from a module's source.

    Aliases are stringized in signatures (``from __future__ import annotations``), so
    ``inspect.signature`` only ever sees the bare alias *name*; and aliases under
    ``if TYPE_CHECKING:`` degrade to ``object`` / ``Any`` at runtime. Read the source and
    collect every ``: TypeAlias`` assignment at any nesting, preferring a meaningful
    right-hand side over a runtime ``Any`` / ``object`` fallback. Which aliases to *show*
    is left to the per-mirror reachability pass, so no ``__all__`` filter is applied here.
    """
    try:
        module = importlib.import_module(module_name)
        source = inspect.getsource(module)
    except (ImportError, OSError, TypeError):
        return {}
    aliases: dict[str, str] = {}
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)):
            continue
        if node.value is None or not _is_type_alias_annotation(node.annotation):
            continue
        name = node.target.id
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            # Forward-ref string alias: the string literal IS the definition.
            definition = node.value.value
        else:
            definition = ast.unparse(node.value)
        if definition in ('object', 'Any'):
            aliases.setdefault(name, definition)  # runtime fallback — only if nothing better
        else:
            aliases[name] = definition  # a meaningful definition always wins
    return {name: defn for name, defn in aliases.items() if defn not in ('object', 'Any')}


_GLOBAL_ALIAS_CACHE: dict[str, str] | None = None


def _global_type_aliases() -> dict[str, str]:
    """Merged ``TypeAlias`` glossary across ``dtypes`` + every documented module.

    Covers both the central ``treasuryutils.dtypes`` aliases and module-local ones
    (e.g. compute ``SpecsLike`` / ``Measure``). Cached: imports + AST-parses each
    module's source once per run.
    """
    global _GLOBAL_ALIAS_CACHE
    if _GLOBAL_ALIAS_CACHE is None:
        merged: dict[str, str] = {}
        for mod in ['treasuryutils.dtypes', *_discover_modules()]:
            for name, definition in _parse_type_aliases(mod).items():
                merged.setdefault(name, definition)
        _GLOBAL_ALIAS_CACHE = merged
    return _GLOBAL_ALIAS_CACHE


def _referenced_aliases(body: str, glossary: dict[str, str]) -> list[str]:
    """Aliases from *glossary* reachable from *body* (transitive over definitions).

    Starts from aliases whose name appears in the rendered signatures, then pulls in
    any alias referenced by an included alias's definition, so the emitted glossary is
    self-contained (e.g. ``DateInput`` drags in ``DateScalar`` / ``DateSequence``).
    """
    included: set[str] = set()
    frontier = [name for name in glossary if re.search(rf'\b{re.escape(name)}\b', body)]
    while frontier:
        name = frontier.pop()
        if name in included:
            continue
        included.add(name)
        definition = glossary[name]
        frontier.extend(
            other
            for other in glossary
            if other not in included and re.search(rf'\b{re.escape(other)}\b', definition)
        )
    return sorted(included)


def _render_domain_api(
    domain: str,
    modules_data: dict[str, dict[str, Any]],
    version: str,
    generated_at: str,
    canonical: dict[str, tuple[str, str]],
) -> str:
    """Render a single domain's API reference as markdown."""
    lines: list[str] = []
    title = DOMAIN_TITLES.get(domain, f'{domain} API Reference')
    extras = DOMAIN_EXTRAS.get(domain, 'treasuryutils')

    lines.append(f'# {title} (generated)')
    lines.append('')
    lines.append(f'- treasuryutils_version: `{version}`')
    lines.append(f'- generated_at_utc: `{generated_at}`')
    lines.append(f'- install_extras: `{extras}`')
    lines.append('')

    for module_name in sorted(modules_data):
        payload = modules_data[module_name]
        import_error = payload.get('import_error')

        lines.append(f'## `{module_name}`')
        lines.append('')

        if import_error:
            lines.append(f'> Import error: `{import_error}`')
            lines.append('')
            continue

        symbols: list[dict[str, str]] = payload.get('symbols', [])
        if not symbols:
            lines.append('_No public callables discovered._')
            lines.append('')
            continue

        lines.append('| Symbol | Kind | Signature | Description |')
        lines.append('| --- | --- | --- | --- |')
        for sym in symbols:
            sig = _md_escape(sym['signature'])
            doc = _md_escape(sym['doc'])
            note = _canonical_note(sym, canonical)
            inputs = sym.get('input_columns', '')
            lines.append(f'| `{sym["name"]}` | {sym["kind"]} | `{sig}` | {doc}{note}{inputs} |')
        lines.append('')

    glossary = _global_type_aliases()
    used = _referenced_aliases('\n'.join(lines), glossary) if glossary else []
    if used:
        lines.append('## Type Aliases')
        lines.append('')
        lines.append(
            'Type-alias names used in the signatures above, resolved from the '
            'treasuryutils source (some are defined under `TYPE_CHECKING`).'
        )
        lines.append('')
        lines.append('| Alias | Definition |')
        lines.append('| --- | --- |')
        for name in used:
            lines.append(f'| `{name}` | `{_md_escape(glossary[name])}` |')
        lines.append('')

    return '\n'.join(lines).strip() + '\n'


# ---------------------------------------------------------------------------
# Markdown rendering -- YAML contracts
# ---------------------------------------------------------------------------


def _render_yaml_contracts(
    models_data: dict[str, dict[str, Any]],
    validators: list[dict[str, str]],
    version: str,
    generated_at: str,
) -> str:
    """Render the YAML contracts reference as markdown."""
    lines: list[str] = []

    lines.append('# YAML Contracts Reference (generated)')
    lines.append('')
    lines.append(f'- treasuryutils_version: `{version}`')
    lines.append(f'- generated_at_utc: `{generated_at}`')
    lines.append('')
    lines.append('This file documents the DataTools YAML dataset contract schema.')
    lines.append('')

    # --- Model fields ---
    lines.append('## Model Fields')
    lines.append('')

    for model_name, model_payload in models_data.items():
        lines.append(f'### {model_name}')
        if model_payload.get('doc'):
            lines.append('')
            lines.append(model_payload['doc'])
        lines.append('')
        lines.append('| Field | Type | Required | Default | Description |')
        lines.append('| --- | --- | --- | --- | --- |')

        for field in model_payload['fields']:
            lines.append(
                f'| `{field["name"]}` '
                f'| `{_md_escape(field["type"])}` '
                f'| {"yes" if field["required"] else "no"} '
                f'| {_md_escape(field["default_display"])} '
                f'| {_md_escape(field["description"])} |'
            )
        lines.append('')

    # --- Source driver rules ---
    lines.append('## Source Driver Rules')
    lines.append('')
    for driver, rule in SOURCE_DRIVER_RULES.items():
        required_config = ', '.join(rule['required_config_fields']) or '(none)'
        lines.append(f'### `{driver}`')
        lines.append('')
        lines.append(f'- Required config fields: `{required_config}`')
        lines.append(f'- Requires query: `{rule["requires_query"]}`')
        for note in rule['notes']:
            lines.append(f'- {note}')
        lines.append('')

    # --- Known validators ---
    lines.append('## Known Validators')
    lines.append('')
    lines.append('| Name | Location | Purpose |')
    lines.append('| --- | --- | --- |')
    for item in validators:
        lines.append(f'| `{item["name"]}` | `{item["where"]}` | {_md_escape(item["purpose"])} |')
    lines.append('')

    # --- Templates ---
    lines.append('## Baseline Templates')
    lines.append('')
    for template in YAML_TEMPLATES:
        lines.append(f'### `{template["name"]}` driver')
        lines.append('')
        lines.append('```yaml')
        lines.append(template['snippet'])
        lines.append('```')
        lines.append('')
        lines.append(f'Required: `{template["required_fields"]}`')
        lines.append('')
        if template['common_errors']:
            lines.append('Common errors:')
            for error in template['common_errors']:
                lines.append(f'- {error}')
            lines.append('')

    # --- Pitfalls ---
    lines.append('## Pitfalls')
    lines.append('')
    for pitfall in YAML_PITFALLS:
        lines.append(f'- {pitfall}')
    lines.append('')

    return '\n'.join(lines).strip() + '\n'


def _build_canonical_map(
    domain_modules: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, tuple[str, str]]:
    """Map each object identity to its canonical ``(module, name)`` for imports.

    A class re-exported under several modules (or several names) appears once per
    occurrence; pick one canonical home — the shortest public module, named by the
    object's real ``__name__`` — so re-export / alias rows can point an agent at the
    single import that works (e.g. ``DatasetManager`` -> ``DatasetClient``).
    """
    occurrences: dict[str, list[tuple[str, str, str]]] = {}
    for modules in domain_modules.values():
        for module_name, payload in modules.items():
            for sym in payload.get('symbols', []):
                identity = sym.get('identity')
                if identity and identity.startswith('treasuryutils'):
                    occurrences.setdefault(identity, []).append(
                        (module_name, sym['name'], sym.get('real_name', sym['name']))
                    )
    canonical: dict[str, tuple[str, str]] = {}
    for identity, occ in occurrences.items():
        names = {n for _, n, _ in occ}
        if len(names) < 2:
            continue  # a single export name — not an alias, nothing to disambiguate
        real = occ[0][2]
        public = sorted(n for n in names if not n.startswith('_'))
        if real in names and not real.startswith('_'):
            canon_name = real  # the object's own __name__ is a public export
        elif public:
            canon_name = public[0]
        else:
            canon_name = sorted(names)[0]
        under_canon = [m for m, n, _ in occ if n == canon_name]
        canon_module = min(under_canon, key=lambda m: (m.count('.'), len(m), m))
        canonical[identity] = (canon_module, canon_name)
    return canonical


def _canonical_note(sym: dict[str, str], canonical: dict[str, tuple[str, str]]) -> str:
    """Suffix flagging an *alias* row with its canonical name + import.

    An alias is a class exported under a second name (e.g. ``DatasetManager`` ->
    ``DatasetClient``). Returns ``''`` for the canonical name itself and for same-name
    re-exports, whose import name is already unambiguous.
    """
    identity = sym.get('identity')
    if not identity or identity not in canonical:
        return ''
    canon_module, canon_name = canonical[identity]
    if sym['name'] == canon_name:
        return ''
    return f' · alias of `{canon_name}` (import: `from {canon_module} import {canon_name}`)'


# ---------------------------------------------------------------------------
# In-memory reference building (shared by the write path and --check)
# ---------------------------------------------------------------------------


def _build_domain_references(version: str, generated_at: str) -> dict[str, str]:
    """Build the per-domain API markdown files in memory.

    Returns a ``{filename: content}`` mapping in stable (sorted-domain) order.
    No filesystem writes happen here — the caller decides whether to persist.
    """
    all_modules = _discover_modules()
    domain_modules: dict[str, dict[str, dict[str, Any]]] = {}
    for module_name in all_modules:
        domain = _route_module_to_domain(module_name)
        domain_modules.setdefault(domain, {})[module_name] = _collect_module_symbols(module_name)

    canonical = _build_canonical_map(domain_modules)
    return {
        f'{domain}_api.md': _render_domain_api(
            domain, modules_data, version, generated_at, canonical
        )
        for domain, modules_data in sorted(domain_modules.items())
    }


def _build_yaml_contracts(version: str, generated_at: str) -> str:
    """Build the ``yaml_contracts.md`` content in memory.

    Raises on any introspection/render failure. The write path wraps this in a
    warn-and-skip ``try/except`` (historical behaviour); ``--check`` lets the
    exception propagate so a generation failure is treated as drift, never a skip.
    """
    models_mod = importlib.import_module('treasuryutils.datatools.config.models')
    validation_mod = importlib.import_module('treasuryutils.datatools.config.validation')

    model_payload = {
        'DatasetConfig': _extract_model('DatasetConfig', models_mod.DatasetConfig),
        'SourceConfig': _extract_model('SourceConfig', models_mod.SourceConfig),
        'ServingConfig': _extract_model('ServingConfig', models_mod.ServingConfig),
        'ProviderConfig': _extract_model('ProviderConfig', models_mod.ProviderConfig),
        'RefreshPolicy': _extract_model('RefreshPolicy', models_mod.RefreshPolicy),
    }
    validators = _known_validators(models_mod, validation_mod)
    return _render_yaml_contracts(model_payload, validators, version, generated_at)


# ---------------------------------------------------------------------------
# Content freshness check (--check)
# ---------------------------------------------------------------------------


def _strip_stamp_lines(text: str) -> str:
    """Drop the two volatile stamp lines so comparisons are version/time-stable."""
    return '\n'.join(
        line
        for line in text.splitlines()
        if not any(line.startswith(prefix) for prefix in _STAMP_LINE_PREFIXES)
    )


def _run_content_check(references_dir: Path, version: str, generated_at: str) -> int:
    """Compare in-memory regenerated mirrors against the committed files.

    Returns rc 0 only when EXACTLY ``EXPECTED_REFERENCE_COUNT`` files are both
    generated and compared and every committed file matches (modulo the two
    stamp lines). Performs ZERO filesystem writes.

    Three hard invariants:

    1. *Exactly-9* — fewer than 9 generated (e.g. a yaml generation exception,
       which the write path only WARNS about) is rc 1, never a skip.
    2. *Zero-write* — no mirrors and no ``.generated_meta.json`` are written.
    3. *Non-vacuous* — an empty regenerated body or a missing committed file is
       rc 1, never a pass.
    """
    try:
        contents = _build_domain_references(version, generated_at)
        contents['yaml_contracts.md'] = _build_yaml_contracts(version, generated_at)
    except Exception as exc:
        # Broad by design: ANY generation failure is drift (rc 1), never a skip.
        sys.stderr.write(
            f'--check FAILED: reference generation raised '
            f'{type(exc).__name__}: {exc} (treated as drift).\n'
        )
        return 1

    # Invariant 1 — exactly-9 generated.
    if len(contents) != EXPECTED_REFERENCE_COUNT:
        sys.stderr.write(
            f'--check FAILED: generated {len(contents)} reference file(s), '
            f'expected exactly {EXPECTED_REFERENCE_COUNT}.\n'
        )
        return 1

    drifted: list[str] = []
    compared = 0
    for filename, generated in sorted(contents.items()):
        generated_body = _strip_stamp_lines(generated)
        # Invariant 3a — a vacuous empty body is never a pass.
        if not generated_body.strip():
            sys.stderr.write(f'--check: {filename}: regenerated body is empty (vacuous).\n')
            drifted.append(filename)
            continue
        committed_path = references_dir / filename
        # Invariant 3b — a missing committed file is drift, never a pass.
        if not committed_path.exists():
            sys.stderr.write(f'--check: {filename}: committed file is missing.\n')
            drifted.append(filename)
            continue
        committed_body = _strip_stamp_lines(committed_path.read_text(encoding='utf-8'))
        compared += 1
        if generated_body != committed_body:
            sys.stderr.write(f'--check: {filename}: drift detected vs committed mirror.\n')
            drifted.append(filename)

    # Invariant 1 (compared half) — every one of the 9 must have been read+compared.
    if compared != EXPECTED_REFERENCE_COUNT:
        sys.stderr.write(
            f'--check FAILED: compared {compared} file(s) against committed mirrors, '
            f'expected exactly {EXPECTED_REFERENCE_COUNT} '
            f'(missing or empty: {", ".join(sorted(set(drifted))) or "none"}).\n'
        )
        return 1

    if drifted:
        sys.stderr.write(
            f'--check FAILED: {len(drifted)} mirror(s) out of date: '
            f'{", ".join(sorted(drifted))}. Regenerate with generate_references.py.\n'
        )
        return 1

    sys.stdout.write(
        f'--check passed: all {EXPECTED_REFERENCE_COUNT} reference mirrors are current.\n'
    )
    return 0


# ---------------------------------------------------------------------------
# Staleness checking
# ---------------------------------------------------------------------------


def _read_staleness_timestamp(staleness_file: Path) -> dt.datetime | None:
    """Read generated_at_utc from a staleness JSON sidecar."""
    if not staleness_file.exists():
        return None
    try:
        data = json.loads(staleness_file.read_text(encoding='utf-8'))
        raw = data.get('generated_at_utc', '')
        parsed = dt.datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.UTC)
        return parsed.astimezone(dt.UTC)
    except Exception:
        return None


def _check_staleness(staleness_file: Path, stale_after_hours: int) -> int:
    generated_at = _read_staleness_timestamp(staleness_file)
    if generated_at is None:
        sys.stderr.write(
            f'Staleness check: no timestamp found at {staleness_file}. Run generator first.\n'
        )
        return STALE_EXIT_CODE

    age_hours = (dt.datetime.now(dt.UTC) - generated_at).total_seconds() / 3600
    if age_hours <= stale_after_hours:
        sys.stdout.write(f'Staleness check passed: age {age_hours:.1f}h <= {stale_after_hours}h.\n')
        return 0

    sys.stderr.write(f'Staleness check failed: age {age_hours:.1f}h > {stale_after_hours}h.\n')
    return STALE_EXIT_CODE


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            'Generate domain-split API reference files for the '
            'treasuryutils-usage Claude Code skill.'
        )
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=None,
        help='Output directory for generated references (default: ../references/).',
    )
    parser.add_argument(
        '--ttl-hours',
        type=int,
        default=DEFAULT_TTL_HOURS,
        help=f'Suggested TTL in hours (default: {DEFAULT_TTL_HOURS}).',
    )
    parser.add_argument(
        '--stale-after-hours',
        type=int,
        default=None,
        help='Staleness threshold in hours.',
    )
    parser.add_argument(
        '--check-staleness-only',
        action='store_true',
        help=f'Only check staleness and exit (code {STALE_EXIT_CODE} if stale).',
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help=(
            'Content-freshness gate: regenerate all references in memory, compare '
            '(modulo the version/time stamps) against the committed mirrors, and exit '
            '1 on any drift. Writes nothing.'
        ),
    )
    parser.add_argument(
        '--references-dir',
        type=Path,
        default=None,
        help=(
            'Directory of committed mirrors that --check compares against '
            '(default: ../references/). Lets a test point --check at a tampered copy.'
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    output_dir = args.output_dir or (script_dir.parent / 'references')
    staleness_file = output_dir / '.generated_meta.json'

    # --- Staleness check ---
    if args.check_staleness_only:
        if args.stale_after_hours is None:
            sys.stderr.write('--check-staleness-only requires --stale-after-hours.\n')
            return 1
        return _check_staleness(staleness_file, args.stale_after_hours)

    if args.stale_after_hours is not None:
        rc = _check_staleness(staleness_file, args.stale_after_hours)
        if rc != 0:
            sys.stdout.write('References are stale, regenerating...\n')

    # --- Import treasuryutils ---
    try:
        importlib.import_module('treasuryutils')
    except ModuleNotFoundError:
        sys.stderr.write(
            'Could not import `treasuryutils`. Install it first.\n'
            'Example:\n'
            '  uv add "treasuryutils[all] @ '
            'git+https://github.com/stone-payments/treasuryutils.git@main"\n'
        )
        return MISSING_PACKAGE_EXIT_CODE
    except Exception as exc:
        sys.stderr.write(f'Failed to import treasuryutils: {type(exc).__name__}: {exc}\n')
        return MISSING_PACKAGE_EXIT_CODE

    version = _safe_treasuryutils_version()
    generated_at = dt.datetime.now(dt.UTC).isoformat()

    # --- Content-freshness check (writes nothing; returns before the write block) ---
    if args.check:
        references_dir = args.references_dir or (script_dir.parent / 'references')
        return _run_content_check(references_dir, version, generated_at)

    # --- Build + write per-domain API files ---
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files: list[str] = []

    for filename, content in _build_domain_references(version, generated_at).items():
        (output_dir / filename).write_text(content, encoding='utf-8')
        generated_files.append(filename)
        sys.stdout.write(f'Generated: {filename}\n')

    # --- Generate YAML contracts (write path WARNS and skips on failure — the
    #     historical behaviour; --check treats the same failure as drift, rc 1) ---
    try:
        yaml_content = _build_yaml_contracts(version, generated_at)
        (output_dir / 'yaml_contracts.md').write_text(yaml_content, encoding='utf-8')
        generated_files.append('yaml_contracts.md')
        sys.stdout.write('Generated: yaml_contracts.md\n')
    except Exception as exc:
        sys.stderr.write(
            f'Warning: could not generate yaml_contracts.md: {type(exc).__name__}: {exc}\n'
        )

    # --- Write staleness metadata ---
    meta = {
        'generated_at_utc': generated_at,
        'treasuryutils_version': version,
        'python_version': sys.version.split(' ')[0],
        'generated_from': socket.gethostname(),
        'ttl_hours': args.ttl_hours,
        'files': generated_files,
    }
    # Trailing newline so the sidecar satisfies the repo's pre-commit
    # end-of-file-fixer (the mirrors already end in a newline via _render_*).
    staleness_file.write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')

    sys.stdout.write(
        f'\nDone. Generated {len(generated_files)} files for treasuryutils {version}.\n'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
