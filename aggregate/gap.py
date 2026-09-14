"""What FDE postings demand that standard AI-engineer roadmaps do not teach.

STANDARD_ROADMAP_SKILLS is the union of topics covered by roadmap.sh's "AI Engineer" roadmap
(https://roadmap.sh/ai-engineer, checked 2026-09) and the syllabus shared by common LLM
bootcamps (DeepLearning.AI short courses, Full Stack LLM Bootcamp): Python, LLM APIs, prompting,
RAG + vector DBs, agents/frameworks, embeddings, fine-tuning basics, evals, ML fundamentals,
model serving, cloud basics, Git, REST, Docker, observability, guardrails, multimodal.
Expressed in taxonomy canonical names.
"""
from __future__ import annotations

STANDARD_ROADMAP_SKILLS: set[str] = {
    "python", "git", "rest_apis", "docker", "cloud_platforms", "aws", "sql",
    "llm_apis", "prompt_engineering", "rag", "vector_databases", "agents", "llm_frameworks", "evals",
    "fine_tuning", "ml_fundamentals", "nlp", "computer_vision", "model_serving", "llm_observability",
    "guardrails_safety", "testing", "system_design",
}


def gaps(freq: dict[str, dict], *, min_frequency: float = 0.2) -> list[dict]:
    out = [{"canonical": c, "frequency": round(v["frequency"], 3)} for c, v in freq.items()
           if v["frequency"] >= min_frequency and c not in STANDARD_ROADMAP_SKILLS]
    return sorted(out, key=lambda d: -d["frequency"])
