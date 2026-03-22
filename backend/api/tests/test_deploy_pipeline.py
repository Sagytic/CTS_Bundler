"""deploy_pipeline 플래그·요약 (4단계)."""
from api.rag.deploy_pipeline import build_deploy_pipeline_summary, resolve_deploy_pipeline_flags


def test_resolve_pipeline_overrides_and_crag_off_with_research_off():
    f = resolve_deploy_pipeline_flags(
        {
            "pipeline": {
                "research": False,
                "graph": True,
                "self_rag": False,
                "crag_judge": True,
            }
        }
    )
    assert f["research_rag"] is False
    assert f["crag_judge"] is False
    assert f["graph_rag"] is True
    assert f["self_rag"] is False


def test_build_pipeline_summary_shape():
    s = build_deploy_pipeline_summary(
        {
            "pipeline_flags": {"research_rag": True, "graph_rag": True},
            "pipeline_timings_ms": {"research_rag_ms": 12.3},
            "research_meta": {"rounds": [{"n_hits": 2}], "empty": False},
            "graph_meta": {"edge_count": 5, "seed_count": 2, "skipped": False},
            "self_rag_meta": {
                "skipped": False,
                "revised": True,
                "judge": {"is_grounded": False, "severity": "major"},
            },
        }
    )
    assert s["flags"]["research_rag"] is True
    assert s["research"]["rounds"] == 1
    assert s["graph"]["edges"] == 5
    assert s["self_rag"]["revised"] is True
    assert s["self_rag"]["is_grounded"] is False
