"""Validate extraction JSON files against the schema and the closed taxonomy."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from extract import taxonomy
from extract.prepare import EXTRACTIONS_DIR, MANIFEST
from extract.schema import Extraction, SkillMention, parse_extraction
from sources.base import PROCESSED_DIR

REJECTS = PROCESSED_DIR / "rejects.log"


def validate_one(path: Path, tx: taxonomy.Taxonomy) -> tuple[Extraction | None, list[dict]]:
    try:
        ex = parse_extraction(path.read_text())
    except (ValidationError, ValueError):
        return None, []
    if ex.posting_id != path.stem:
        return None, []
    idx, kept, rejects, seen = tx.alias_index, [], [], set()
    for s in ex.skills:
        canon = idx.get(s.canonical.strip().lower())
        if canon is None:
            rejects.append({"posting_id": ex.posting_id, "canonical": s.canonical, "section": s.section, "evidence": s.evidence})
            continue
        if (canon, s.section) in seen:
            continue
        seen.add((canon, s.section))
        kept.append(SkillMention(canonical=canon, section=s.section, evidence=s.evidence))
    return ex.model_copy(update={"skills": kept}), rejects


def run() -> dict:
    tx = taxonomy.load()
    m = json.loads(MANIFEST.read_text())
    ids = list(dict.fromkeys(m["pending"] + m["done"]))
    done, pending, all_rejects, counts = [], [], [], Counter()
    for pid in ids:
        f = EXTRACTIONS_DIR / f"{pid}.json"
        if not f.exists():
            counts["missing"] += 1
            pending.append(pid)
            continue
        ex, rejects = validate_one(f, tx)
        if ex is None:
            counts["invalid"] += 1
            pending.append(pid)
            continue
        f.write_text(ex.model_dump_json(indent=2))  # persist the cleaned version
        all_rejects.extend(rejects)
        counts["valid"] += 1
        done.append(pid)
    MANIFEST.write_text(json.dumps({"pending": pending, "done": done}, indent=2))
    REJECTS.write_text("".join(json.dumps(r) + "\n" for r in all_rejects))
    res = {"valid": counts["valid"], "invalid": counts["invalid"], "missing": counts["missing"], "rejects": len(all_rejects)}
    print(res)
    top = Counter(r["canonical"].lower() for r in all_rejects).most_common(25)
    for name, n in top:
        print(f"  reject x{n:3d}  {name}")
    return res


def load_valid_extractions() -> list[Extraction]:
    m = json.loads(MANIFEST.read_text())
    return [parse_extraction((EXTRACTIONS_DIR / f"{pid}.json").read_text()) for pid in m["done"]]
