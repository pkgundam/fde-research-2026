"""Closed skill vocabulary loaded from taxonomy.yaml."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

PATH = Path(__file__).resolve().parent.parent / "taxonomy.yaml"


class Skill(BaseModel):
    canonical: str
    label: str
    aliases: list[str] = []
    definition: str


class Taxonomy(BaseModel):
    clusters: dict[str, list[Skill]]
    cluster_labels: dict[str, str]

    @property
    def by_canonical(self) -> dict[str, Skill]:
        return {s.canonical: s for c in self.clusters.values() for s in c}

    @property
    def alias_index(self) -> dict[str, str]:
        idx = {}
        for c in self.clusters.values():
            for s in c:
                idx[s.canonical] = s.canonical
                idx[s.label.lower()] = s.canonical
                for a in s.aliases:
                    idx[a.lower()] = s.canonical
        return idx

    @property
    def labels(self) -> dict[str, str]:
        return {k: v.label for k, v in self.by_canonical.items()}

    def canonical_names(self) -> set[str]:
        return set(self.by_canonical)

    def cluster_of(self, canonical: str) -> str:
        for key, skills in self.clusters.items():
            if any(s.canonical == canonical for s in skills):
                return key
        raise KeyError(canonical)


def load(path: Path = PATH) -> Taxonomy:
    raw = yaml.safe_load(path.read_text())
    return Taxonomy(
        clusters={k: [Skill(**s) for s in v["skills"]] for k, v in raw["clusters"].items()},
        cluster_labels={k: v["label"] for k, v in raw["clusters"].items()},
    )
