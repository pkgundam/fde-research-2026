"""Render report_data.json + content.yaml into one self-contained HTML file."""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "fde-roadmap.html"
FIXTURE = HERE / "fixtures" / "report_data.fixture.json"
REPORT_DATA = ROOT / "data" / "processed" / "report_data.json"

CLUSTER_COLORS = {  # from owlhub-tokens.css; always shown with a text label
    "software_foundations": "#3f00ff",
    "ai_application_engineering": "#137a6c",
    "data_and_integrations": "#18324a",
    "deployment_and_operations": "#2563eb",
    "customer_delivery": "#a85f00",
    "product_thinking_and_communication": "#71869a",
}


def load_content() -> dict:
    return yaml.safe_load((HERE / "content.yaml").read_text())


def render_html(data: dict, content: dict) -> str:
    env = Environment(loader=FileSystemLoader(HERE), autoescape=select_autoescape(["j2"]))
    tpl = env.get_template("template.html.j2")
    payload = {**data, "content": content, "cluster_colors": CLUSTER_COLORS}
    return tpl.render(data=payload, data_json=json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))


def run(fixture: bool = False) -> Path:
    src = FIXTURE if fixture or not REPORT_DATA.exists() else REPORT_DATA
    data = json.loads(src.read_text())
    OUT.write_text(render_html(data, load_content()))
    print(f"rendered {OUT} from {src.name} ({OUT.stat().st_size // 1024} KB)")
    return OUT
