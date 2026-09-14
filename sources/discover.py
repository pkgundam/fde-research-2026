"""Find which ATS hosts each candidate company's board."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from sources import ashby, greenhouse, lever

PATH = Path(__file__).resolve().parent / "companies.yaml"
PROBES = {"greenhouse": greenhouse.probe, "lever": lever.probe, "ashby": ashby.probe}


def load_companies() -> dict:
    return yaml.safe_load(PATH.read_text())


def slug_variants(name: str, extra: list[str]) -> list[str]:
    base = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", "", name.lower())).strip()
    joined, hyphen = base.replace(" ", ""), base.replace(" ", "-")
    out = list(extra)
    for v in (joined, hyphen):
        if v not in out:
            out.append(v)
    return out


def run(*, refresh: bool = False) -> dict[str, dict[str, str]]:
    cfg = load_companies()
    resolved: dict[str, dict[str, str]] = {k: {} for k in PROBES}
    for cand in cfg["candidates"]:
        name, variants = cand["name"], slug_variants(cand["name"], cand.get("slugs", []))
        for ats, probe in PROBES.items():
            for slug in variants:
                if probe(slug, refresh=refresh):
                    resolved[ats][slug] = name
                    print(f"  {ats:10s} {slug:24s} <- {name}")
                    break
        if not any(name in r.values() for r in resolved.values()):
            print(f"  unresolved  {name}")
    cfg["resolved"] = resolved
    PATH.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    return resolved
