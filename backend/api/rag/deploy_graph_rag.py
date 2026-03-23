"""
배포 심의 LangGraph 3단계: GraphRAG (구조화 종속성).

TR의 오브젝트명을 시드로 `DependencySnapshot`에서 간선을 수집해
텍스트 블록으로 포맷합니다. 벡터 RAG과 별도 필드(`graph_context`)로 주입합니다.
"""
from __future__ import annotations

import logging
from typing import Any

from django.db.models import Q

_log = logging.getLogger("cts.ai")

_GROUP_HINT = "2=프로그램·클래스, 3=펑션, 4=DB 등"


def seed_object_names_from_tr(sap_data_raw: list, max_seeds: int) -> list[str]:
    """TR objects에서 OBJ_NAME 후보를 모으고, 길이 제한으로 DB __in 부담을 줄임."""
    raw: set[str] = set()
    for tr in sap_data_raw or []:
        objects = tr.get("objects") or tr.get("OBJECTS") or []
        for o in objects:
            n = str(o.get("OBJ_NAME", o.get("obj_name", ""))).strip()
            if n:
                raw.add(n)
                raw.add(n.upper())
    ordered = sorted(raw, key=lambda x: (len(x), x))
    return ordered[: max(1, max_seeds)]


def build_graph_context_for_deploy(
    sap_data_raw: list,
    *,
    max_edges: int,
    max_hops: int,
    max_seeds: int,
) -> tuple[str, dict[str, Any]]:
    """
    Returns:
        (graph_context_markdown, metadata for state['graph_meta'])
    """
    from api.models import DependencySnapshot

    meta: dict[str, Any] = {
        "edge_count": 0,
        "hop_rounds": 0,
        "seed_count": 0,
        "truncated": False,
    }
    seeds_list = seed_object_names_from_tr(sap_data_raw, max_seeds)
    meta["seed_count"] = len(seeds_list)
    if not seeds_list:
        msg = (
            "(GraphRAG) TR에 오브젝트(OBJ_NAME)가 없어 종속성 시드를 만들 수 없습니다. "
            "`DependencySnapshot`이 채워져 있는지, TR 응답 구조를 확인하세요."
        )
        return msg, meta

    nodes: set[str] = set(seeds_list)
    collected: list[dict[str, Any]] = []
    seen_pair: set[tuple[str, str]] = set()
    max_hops = max(0, int(max_hops))
    max_edges = max(1, int(max_edges))

    try:
        for hop in range(max_hops + 1):
            if len(collected) >= max_edges:
                break
            need = max_edges - len(collected)
            q = Q(source_obj__in=nodes) | Q(target_obj__in=nodes)
            qs = (
                DependencySnapshot.objects.filter(q)
                .values("source_obj", "target_obj", "target_group")
                .order_by("source_obj", "target_obj")[: need + 500]
            )
            added_this_hop = 0
            for row in qs.iterator(chunk_size=200):
                key = (row["source_obj"], row["target_obj"])
                if key in seen_pair:
                    continue
                seen_pair.add(key)
                collected.append(
                    {
                        "source_obj": row["source_obj"],
                        "target_obj": row["target_obj"],
                        "target_group": row["target_group"],
                    }
                )
                added_this_hop += 1
                nodes.add(row["source_obj"])
                nodes.add(row["target_obj"])
                if len(collected) >= max_edges:
                    meta["truncated"] = True
                    break
            meta["hop_rounds"] = hop + 1
            if added_this_hop == 0:
                break
    except Exception as e:
        _log.warning("deploy_graph_rag DB query failed: %s", e)
        meta["error"] = "DB 조회 실패"
        return "(GraphRAG 조회 오류)", meta

    meta["edge_count"] = len(collected)
    if not collected:
        return (
            "(GraphRAG) `DependencySnapshot`에서 TR 시드 오브젝트와 연결된 간선이 없습니다. "
            "종속성 스냅샷 적재·동기화를 확인하세요.",
            meta,
        )

    lines = [
        f"[GraphRAG: DependencySnapshot 부분 그래프] 시드 {meta['seed_count']}개, "
        f"간선 {len(collected)}건 (최대 {max_edges}, hop≤{max_hops}). {_GROUP_HINT}",
        "",
    ]
    for r in collected:
        lines.append(
            f"- `{r['source_obj']}` → `{r['target_obj']}` (group={r['target_group']})"
        )
    body = "\n".join(lines)
    return body, meta


def graph_query_suffix(graph_context: str, max_chars: int = 1200) -> str:
    """Chroma 검색 쿼리 보강용 짧은 접미사."""
    g = (graph_context or "").strip()
    if not g or g.startswith("(GraphRAG"):
        return ""
    # 간선에서 따옴표 백틱 내부 토큰만 거칠게 나열
    return "\n\n[종속성 그래프 요약]\n" + g[:max_chars]
