"""What FDE postings demand that standard AI-engineer roadmaps do not teach.

Technical skills are covered by AI-engineer roadmaps if they fall in one of four
taxonomy clusters: software_foundations, ai_application_engineering,
data_and_integrations, deployment_and_operations. That grouping follows
roadmap.sh's "AI Engineer" roadmap (https://roadmap.sh/ai-engineer, checked
2026-09) plus the syllabus shared by common LLM courses (DeepLearning.AI short
courses, Full Stack LLM Bootcamp): Python, LLM APIs, prompting, RAG + vector
DBs, agents/frameworks, embeddings, fine-tuning basics, evals, ML fundamentals,
model serving, cloud basics, Git, REST, Docker, observability, guardrails,
multimodal, and general software/data/deployment engineering — i.e. every skill
in those four clusters, not a hand-picked subset.

GENERIC_PROFESSIONAL is what nearly every job posting asks for regardless of
role (communication, ownership, prioritisation, ...) and so isn't a useful
"gap" either: everyone already knows an employer wants it.

What's left after excluding both — customer delivery and product-thinking
skills that are specific to the FDE role and not "soft skills any job wants" —
is the genuine gap between what roadmaps teach and what FDE postings ask for.
"""
from __future__ import annotations

TECHNICAL_CLUSTERS: set[str] = {
    "software_foundations", "ai_application_engineering", "data_and_integrations", "deployment_and_operations",
}

GENERIC_PROFESSIONAL: set[str] = {
    "verbal_communication", "written_communication", "learning_agility", "ownership_autonomy",
    "cross_functional", "mentoring_leadership", "prioritization",
}


def gaps(freq: dict[str, dict], cluster_of: dict[str, str], *, min_frequency: float = 0.3, limit: int = 8) -> list[dict]:
    out = [{"canonical": c, "frequency": round(v["frequency"], 3)} for c, v in freq.items()
           if v["frequency"] >= min_frequency and cluster_of.get(c) not in TECHNICAL_CLUSTERS
           and c not in GENERIC_PROFESSIONAL]
    return sorted(out, key=lambda d: (-d["frequency"], d["canonical"]))[:limit]
