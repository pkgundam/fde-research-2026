import json
from pathlib import Path
from render import render as r

FIX = Path("render/fixtures/report_data.fixture.json")
SECTION_IDS = ["what-fde-does", "top-technologies", "frequency-vs-criticality", "capability-clusters",
               "learning-roadmap", "market-insights", "proof-projects", "methodology"]


def test_render_from_fixture_has_all_sections_and_placeholder():
    data = json.loads(FIX.read_text())
    html = r.render_html(data, r.load_content())
    for sid in SECTION_IDS:
        assert f'id="{sid}"' in html, sid
    assert '<div id="author-note" class="placeholder">YOUR ONE SENTENCE HERE</div>' in html
    assert 'type="application/json"' in html
    assert "cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js" in html
    assert "chartjs-plugin-annotation/3.0.1" in html
    assert len(html.encode()) < 1_500_000
    # no other external assets
    assert "fonts.googleapis" not in html and "<link" not in html
    assert "Stacks that travel together" in html
    for st in data["stacks"]:
        assert st["name"] in html
