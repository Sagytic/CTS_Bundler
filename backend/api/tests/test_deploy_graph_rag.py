"""GraphRAG (deploy) — DependencySnapshot 부분 그래프."""
import pytest
from api.models import DependencySnapshot
from api.rag.deploy_graph_rag import build_graph_context_for_deploy, graph_query_suffix


@pytest.mark.django_db
class TestDeployGraphRag:
    def test_build_graph_finds_edges_for_tr_seed(self):
        DependencySnapshot.objects.create(
            source_obj="ZMMR0030", target_obj="EKKO", target_group=4
        )
        sap_data_raw = [
            {
                "trkorr": "DEVK900001",
                "objects": [{"OBJECT": "PROG", "OBJ_NAME": "ZMMR0030"}],
            }
        ]
        text, meta = build_graph_context_for_deploy(
            sap_data_raw,
            max_edges=20,
            max_hops=0,
            max_seeds=50,
        )
        assert meta["edge_count"] >= 1
        assert "ZMMR0030" in text
        assert "EKKO" in text

    def test_graph_query_suffix_skips_placeholder(self):
        assert graph_query_suffix("(GraphRAG 비활성)") == ""
        assert "종속성" in graph_query_suffix("[GraphRAG: x]\n- `A` → `B`")
