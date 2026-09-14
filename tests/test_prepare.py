import json
from pydantic import ValidationError
import pytest
from extract import schema, prepare, taxonomy
from extract.segment import segment
from sources.base import Posting

GOOD = {"posting_id": "abc", "skills": [{"canonical": "python", "section": "requirement", "evidence": "Strong Python"}],
        "seniority": "senior", "years_required": 5, "travel_expectation": "occasional",
        "customer_facing_intensity": 4, "responsibility_verbs": ["build", "deploy", "scope", "own", "present"],
        "segmentation_quality": "header"}


def test_schema_accepts_good_and_rejects_bad():
    schema.Extraction(**GOOD)
    with pytest.raises(ValidationError):
        schema.Extraction(**{**GOOD, "customer_facing_intensity": 6})
    with pytest.raises(ValidationError):
        schema.Extraction(**{**GOOD, "skills": [{"canonical": "python", "section": "bonus", "evidence": "x"}]})
    with pytest.raises(ValidationError):
        schema.Extraction(**{**GOOD, "responsibility_verbs": ["a", "b"]})


def test_render_prompt_contains_taxonomy_segments_and_schema():
    p = Posting(id="abc", title="FDE", company="Acme", url="u", source="t",
                full_text="What you'll do\nDeploy models\nRequirements\nPython\n")
    txt = prepare.render_prompt(p, segment(p.full_text), taxonomy.load())
    assert "stakeholder_communication" in txt and "amazon web services" in txt
    assert "## RESPONSIBILITIES" in txt and "Deploy models" in txt
    assert '"posting_id": "abc"' in txt and "customer_facing_intensity" in txt
    assert "segmentation_quality" in txt and '"header"' in txt


def test_run_writes_prompts_and_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(prepare, "PROMPTS_DIR", tmp_path / "prompts")
    monkeypatch.setattr(prepare, "EXTRACTIONS_DIR", tmp_path / "extractions")
    monkeypatch.setattr(prepare, "MANIFEST", tmp_path / "prompts" / "manifest.json")
    posts = [Posting(id=f"id{i}", title="FDE", company="Acme", url="u", source="t", full_text="Requirements\nPython") for i in range(3)]
    monkeypatch.setattr(prepare, "load_postings", lambda: posts)
    (tmp_path / "extractions").mkdir()
    (tmp_path / "extractions" / "id1.json").write_text(json.dumps({**GOOD, "posting_id": "id1"}))
    assert prepare.run(limit=2) == 2
    m = json.loads(prepare.MANIFEST.read_text())
    assert m["pending"] == ["id0"] and m["done"] == ["id1"]
    assert (tmp_path / "prompts" / "id0.md").exists()
