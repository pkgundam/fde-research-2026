import json
from pathlib import Path
from aggregate import build_report_data as b
from extract import taxonomy
from sources.base import Posting

FIX_KEYS = json.loads(Path("render/fixtures/report_data.fixture.json").read_text())


def test_build_matches_fixture_shape(six):
    posts = [Posting(id=e.posting_id, title="FDE", company=f"C{i}", url="u", full_text="x", source="greenhouse",
                     posted_date=f"2026-0{i+3}-01", company_size_hint="startup" if i < 3 else "enterprise") for i, e in enumerate(six)]
    stats = [{"name": "greenhouse", "fetched": 10, "matched": 6, "kept": 6}]
    d = b.build(six, posts, stats, n_rejects=2, tx=taxonomy.load(), generated_at="2026-09-14T00:00:00Z")
    assert set(d) == set(FIX_KEYS)
    assert d["meta"]["n_postings"] == 6 and d["meta"]["n_companies"] == 6 and d["meta"]["date_range"] == ["2026-03-01", "2026-08-01"]
    assert d["meta"]["segmentation"] == {"header": 5, "inferred": 1} and d["meta"]["rejects"] == 2 and d["meta"]["adzuna_used"] is False
    assert d["meta"]["collected_on"] == "2026-09-14" and d["meta"]["recent_share"] == 1.0
    py = next(s for s in d["skills"] if s["canonical"] == "python")
    assert set(py) == set(FIX_KEYS["skills"][0]) and py["label"] == "Python" and py["cluster"] == "software_foundations"
    assert [c["key"] for c in d["clusters"]] == [c["key"] for c in FIX_KEYS["clusters"]]
    assert set(d["scatter"]) == {"median_frequency", "median_criticality", "outliers"}
    assert set(d["market"]) == set(FIX_KEYS["market"])
    assert all(set(g) == {"canonical", "label", "frequency"} for g in d["gap"])
    assert all(set(s) == {"name", "skills", "support"} for s in d["stacks"])
