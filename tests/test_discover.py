from sources import discover


def test_slug_variants():
    assert discover.slug_variants("Scale AI", ["scaleai", "scale"]) == ["scaleai", "scale", "scale-ai"]
    assert discover.slug_variants("Anthropic", []) == ["anthropic"]
    assert discover.slug_variants("Weights & Biases", ["wandb"]) == ["wandb", "weightsbiases", "weights-biases"]


def test_run_records_resolved(monkeypatch, tmp_path):
    cfg = tmp_path / "companies.yaml"
    cfg.write_text("candidates:\n  - {name: Foo, slugs: [foo]}\n  - {name: Bar}\nresolved: {}\n")
    monkeypatch.setattr(discover, "PATH", cfg)
    monkeypatch.setattr(discover, "PROBES", {"greenhouse": lambda s, refresh=False: s == "foo",
                                             "lever": lambda s, refresh=False: False,
                                             "ashby": lambda s, refresh=False: s == "bar"})
    res = discover.run()
    assert res == {"greenhouse": {"foo": "Foo"}, "lever": {}, "ashby": {"bar": "Bar"}}
    assert "resolved:" in cfg.read_text() and "foo: Foo" in cfg.read_text()
