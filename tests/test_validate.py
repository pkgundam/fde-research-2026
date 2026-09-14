import json
from extract import validate, taxonomy, prepare

GOOD = {"posting_id": "a", "skills": [{"canonical": "python", "section": "requirement", "evidence": "x"},
                                      {"canonical": "quantum_computing", "section": "nice_to_have", "evidence": "q"},
                                      {"canonical": "Amazon Web Services", "section": "requirement", "evidence": "aws"}],
        "seniority": "mid", "years_required": None, "travel_expectation": "unspecified", "customer_facing_intensity": 3,
        "responsibility_verbs": ["a", "b", "c", "d", "e"], "segmentation_quality": "inferred"}


def test_validate_one_drops_unknown_and_resolves_alias(tmp_path):
    f = tmp_path / "a.json"
    f.write_text(json.dumps(GOOD))
    ex, rejects = validate.validate_one(f, taxonomy.load())
    assert [s.canonical for s in ex.skills] == ["python", "aws"]
    assert rejects == [{"posting_id": "a", "canonical": "quantum_computing", "section": "nice_to_have", "evidence": "q"}]


def test_validate_one_tolerates_fenced_extraction(tmp_path):
    f = tmp_path / "a.json"
    f.write_text("```json\n" + json.dumps(GOOD) + "\n```")
    ex, rejects = validate.validate_one(f, taxonomy.load())
    assert ex is not None
    assert [s.canonical for s in ex.skills] == ["python", "aws"]


def test_validate_one_schema_failure_returns_none(tmp_path):
    f = tmp_path / "b.json"
    f.write_text('{"posting_id": "b"}')
    ex, rejects = validate.validate_one(f, taxonomy.load())
    assert ex is None and rejects == []


def test_run_updates_manifest_and_rejects(monkeypatch, tmp_path):
    ex_dir, pr_dir = tmp_path / "extractions", tmp_path / "prompts"
    ex_dir.mkdir(); pr_dir.mkdir()
    monkeypatch.setattr(validate, "EXTRACTIONS_DIR", ex_dir)
    monkeypatch.setattr(validate, "MANIFEST", pr_dir / "manifest.json")
    monkeypatch.setattr(validate, "REJECTS", tmp_path / "rejects.log")
    (pr_dir / "manifest.json").write_text(json.dumps({"pending": ["a", "b", "c"], "done": []}))
    (ex_dir / "a.json").write_text(json.dumps(GOOD))
    (ex_dir / "b.json").write_text("not json")
    res = validate.run()
    assert res == {"valid": 1, "invalid": 1, "missing": 1, "rejects": 1}
    m = json.loads((pr_dir / "manifest.json").read_text())
    assert m["done"] == ["a"] and sorted(m["pending"]) == ["b", "c"]
    assert json.loads((tmp_path / "rejects.log").read_text().splitlines()[0])["canonical"] == "quantum_computing"
    assert json.loads((ex_dir / "a.json").read_text())["skills"][1]["canonical"] == "aws"  # rewritten clean
