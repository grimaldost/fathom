"""Authoring-time distractor generator (§3) — deterministic, no run-time randomness.

Emits coherent-but-irrelevant sibling modules into a LARGE fixture's package so the buggy
module and its contract modules are needles in a ~40-module haystack. Run once at authoring
time (``python gen_distractors.py``); the emitted files are committed. This generator is
NOT imported by any verifier or staged helper, and never writes into a ``-small`` fixture.

Invariants it guarantees (asserted by ``tests/test_context_bank.py``):

* **import-coherent** (FM-N2 / FM-N9): for an interdependence pair every emitted module
  imports one of the package's *contract* modules, forming a connected import graph the
  target participates in; for the negative-control pair they form a star around a hub
  module (still connected, but referencing nothing under test). ``compileall`` passes.
* **grep-resistant** (FM-N1): module names are drawn from a domain-term list that includes
  the symptom's terms AND the contract stems (so ``grep tax`` / ``grep rate`` / ``grep
  config`` each return many candidates, not the lone contract). No emitted module
  name-stem-matches ``avoid`` (the buggy module).
* **ruff-clean**: every import is referenced (``_REFS`` tuple), output is repo-formatted.
"""

from __future__ import annotations

from pathlib import Path

_SUFFIXES = ("service", "helpers", "utils", "manager", "registry", "adapter")


def _module_names(domain_terms: list[str], avoid: str, count: int) -> list[str]:
    # term-outer so each domain term gets ALL suffixes before the next term — guarantees
    # the leading (symptom) terms clear the >=5 grep-resistance floor (FM-N1).
    out: list[str] = []
    for term in domain_terms:
        if term == avoid:
            continue
        for suf in _SUFFIXES:
            name = f"{term}_{suf}"
            if name not in out:
                out.append(name)
            if len(out) >= count:
                return out
    return out


def _module_source(pkg: str, name: str, imports: list[tuple[str, str]]) -> str:
    """Render one ruff-clean distractor module. ``imports`` = [(module, symbol), ...]."""
    lines = [f'"""Auxiliary {name.replace("_", " ")} for the {pkg} package."""', ""]
    for mod, sym in imports:
        lines.append(f"from .{mod} import {sym}")
    refs = ", ".join(sym for _mod, sym in imports)
    lines.append("")
    lines.append(f"_REFS = ({refs},)")
    lines.append("")
    lines.append("")
    lines.append(f"def describe_{name}() -> str:")
    lines.append('    """Return a short tag for this auxiliary module."""')
    lines.append(f'    return "{name}"')
    return "\n".join(lines) + "\n"


def generate(
    pkg_dir: Path,
    *,
    contracts: list[str],
    contract_symbols: dict[str, str],
    ref_contracts: bool,
    domain_terms: list[str],
    avoid: str,
    count: int = 40,
) -> list[str]:
    """Write ``count`` distractor modules into ``pkg_dir``; return the names written."""
    pkg_dir = Path(pkg_dir)
    pkg = pkg_dir.name
    names = _module_names(domain_terms, avoid, count)
    hub = names[0]
    for i, name in enumerate(names):
        if ref_contracts:
            c = contracts[i % len(contracts)]
            imports = [(c, contract_symbols[c])]
        elif i == 0:
            imports = []
        else:
            # negative control: star around the hub (connected, references nothing under test)
            imports = [(hub, f"describe_{hub}")]
        src = _module_source(pkg, name, imports) if imports else _hubless_source(pkg, name)
        (pkg_dir / f"{name}.py").write_text(src, encoding="utf-8")
    return names


def _hubless_source(pkg: str, name: str) -> str:
    """The negative-control hub: no sibling/contract imports, still a real module."""
    return (
        f'"""Auxiliary {name.replace("_", " ")} for the {pkg} package."""\n\n\n'
        f"def describe_{name}() -> str:\n"
        f'    """Return a short tag for this auxiliary module."""\n'
        f'    return "{name}"\n'
    )


# Per-pair generation recipes. `python gen_distractors.py` (re)materialises every LARGE
# fixture deterministically from the committed -small core (which is copied in first).
_PAIRS = [
    {
        "pair": "shipping-tax",
        "pkg": "shopcart",
        "contracts": ["config", "rates"],
        "contract_symbols": {"config": "FREE_SHIPPING_OVER", "rates": "TAX_RATE"},
        "ref_contracts": True,
        "avoid": "checkout",
        "domain_terms": [
            "tax",
            "shipping",
            "config",
            "rate",
            "fee",
            "freight",
            "duty",
            "customs",
            "vat",
            "invoice",
            "currency",
            "region",
            "surcharge",
            "coupon",
        ],
    },
    {
        "pair": "loyalty-reward",
        "pkg": "rewards",
        "contracts": ["accounts", "loyalty"],
        "contract_symbols": {"accounts": "tier_of", "loyalty": "rate_for"},
        "ref_contracts": True,
        "avoid": "points",
        "domain_terms": [
            "account",
            "loyalty",
            "reward",
            "tier",
            "member",
            "spend",
            "bonus",
            "perk",
            "redeem",
            "balance",
            "statement",
            "enroll",
            "segment",
            "campaign",
        ],
    },
    {
        "pair": "nonlocal-sku",
        "pkg": "warehouse",
        "contracts": ["aliases", "keys"],
        "contract_symbols": {"aliases": "canonical", "keys": "sku_key"},
        "ref_contracts": True,
        "avoid": "keys",
        "domain_terms": [
            "sku",
            "alias",
            "inventory",
            "pricing",
            "stock",
            "warehouse",
            "barcode",
            "vendor",
            "bin",
            "lot",
            "shipment",
            "receiving",
            "catalog",
            "reorder",
        ],
    },
    {
        "pair": "slug-control",
        "pkg": "textkit",
        "contracts": [],
        "contract_symbols": {},
        "ref_contracts": False,
        "avoid": "slug",
        "domain_terms": [
            "title",
            "render",
            "markup",
            "token",
            "format",
            "escape",
            "wrap",
            "case",
            "trim",
            "encode",
            "locale",
            "template",
            "heading",
            "anchor",
        ],
    },
]


def main() -> int:
    bank = Path(__file__).resolve().parent
    for rec in _PAIRS:
        pkg_dir = bank / f"{rec['pair']}-large" / "fixtures" / rec["pkg"]
        if not pkg_dir.is_dir():
            print(f"skip {rec['pair']}: {pkg_dir} not found (copy the -small core first)")
            continue
        names = generate(
            pkg_dir,
            contracts=rec["contracts"],
            contract_symbols=rec["contract_symbols"],
            ref_contracts=rec["ref_contracts"],
            domain_terms=rec["domain_terms"],
            avoid=rec["avoid"],
        )
        print(f"{rec['pair']}: wrote {len(names)} distractors into {pkg_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
