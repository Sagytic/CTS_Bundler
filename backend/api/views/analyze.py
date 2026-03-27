from __future__ import annotations

import asyncio
import logging
import json
import re
import threading
import time
from collections import Counter
from asgiref.sync import sync_to_async
from types import SimpleNamespace
from typing import TypedDict

from django.http import StreamingHttpResponse
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, StateGraph
from rest_framework.request import Request
from rest_framework.views import APIView

from api.config import (
    analyze_graph_recursion_limit,
    azure_openai_api_version,
    azure_openai_deployment,
    azure_openai_endpoint,
    azure_openai_fast_deployment,
    azure_openai_key,
    deploy_graph_rag_max_edges,
    deploy_graph_rag_max_hops,
    deploy_graph_rag_max_seeds,
    deploy_research_rag_k,
)
from api.persist_ai_reports import save_deploy_report_record, should_persist
from api.rag.deploy_pipeline import (
    build_deploy_pipeline_summary,
    resolve_deploy_pipeline_flags,
)
from api.sap_client import fetch_object_usage_via_http, fetch_recent_transports_via_http

_logger = logging.getLogger("cts.ai")

# 배포 리스크 등급별 권장 액션 (고정)
DEPLOY_ACTIONS = {
    "Low": [
        "단위 테스트 완료 후 배포 진행",
        "변경 이력(트랜잭션 로그) 확인 권장",
    ],
    "Medium": [
        "연관 모듈(FI/CO/MM/SD/PP 등) 통합 테스트 수행 후 배포",
        "스테이징 환경 검증 후 프로덕션 반영",
        "배포 일정 공유 및 담당자 확인",
    ],
    "High": [
        "사전 배포 회의 필수(영향 모듈 담당자 참석)",
        "롤백 계획 및 긴급 조치 절차 수립",
        "점검 시간대 또는 비업무 시간 배포 권장",
        "배포 후 모니터링 강화(DB 락, 덤프, 트랜잭션)",
    ],
}


class AgentState(TypedDict):
    user_input: str
    sap_data_raw: list
    rule_score: int
    rule_reasons: list
    deploy_risk_grade: str
    deploy_risk_reason: str
    deploy_risk_actions: list
    bc_analysis: str
    fi_analysis: str
    co_analysis: str
    mm_analysis: str
    sd_analysis: str
    pp_analysis: str
    discussion_history: str
    final_report: str
    review_queue: list
    called_counts: dict
    object_usage_data: list
    # Researcher (CRAG) — fetch_data 다음 노드에서 채움
    research_context: str
    research_meta: dict
    # Self-RAG (2단계) — architect 다음 노드
    self_rag_meta: dict
    # GraphRAG (3단계) — research 노드에서 채움
    graph_context: str
    graph_meta: dict
    # 4단계: 파이프라인 플래그·타이밍
    pipeline_flags: dict
    pipeline_timings_ms: dict


class AnalyzeGuardianView(APIView):
    """POST /api/analyze-guardian/. LangGraph 배포 위원회 스트리밍 분석."""

    def post(self, request: Request) -> StreamingHttpResponse:
        self.user_input = request.data.get("message", "")
        self.user_id = request.data.get("user_id", "")
        self.selected_trs = request.data.get("selected_trs", [])
        self.req_id = getattr(request, "request_id", "-")
        self.persist_report = should_persist(request.data)
        self.pipeline_flags = resolve_deploy_pipeline_flags(request.data)
        self.include_pipeline_summary = bool(
            request.data.get("include_pipeline_summary")
        )

        self.progress: dict[str, str] = {"step": "", "label": ""}
        self.result_holder: list[dict] = []

        deployment_main = azure_openai_deployment()
        deployment_fast = azure_openai_fast_deployment() or deployment_main
        self.llm = AzureChatOpenAI(
            azure_deployment=deployment_main,
            api_version=azure_openai_api_version(),
            azure_endpoint=azure_openai_endpoint(),
            api_key=azure_openai_key(),
        )
        self.llm_fast = AzureChatOpenAI(
            azure_deployment=deployment_fast,
            api_version=azure_openai_api_version(),
            azure_endpoint=azure_openai_endpoint(),
            api_key=azure_openai_key(),
        )

        app = self._build_graph()

        initial_state = {
            "user_input": self.user_input,
            "sap_data_raw": [],
            "rule_score": 0,
            "rule_reasons": [],
            "deploy_risk_grade": "Low",
            "deploy_risk_reason": "",
            "deploy_risk_actions": [],
            "bc_analysis": "",
            "fi_analysis": "",
            "co_analysis": "",
            "mm_analysis": "",
            "sd_analysis": "",
            "pp_analysis": "",
            "discussion_history": "",
            "final_report": "",
            "review_queue": [],
            "called_counts": {},
            "object_usage_data": [],
            "research_context": "",
            "research_meta": {},
            "graph_context": "",
            "graph_meta": {},
            "self_rag_meta": {},
            "pipeline_flags": self.pipeline_flags,
            "pipeline_timings_ms": {},
        }
        self.config = {"recursion_limit": analyze_graph_recursion_limit()}

        response = StreamingHttpResponse(
            self._stream_generator(app, initial_state),
            content_type="application/x-ndjson; charset=utf-8",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    def _node_fetch_and_score(self, state: AgentState):
        self.progress["step"] = "fetch_data"
        self.progress["label"] = "1차 Rule-based 리스크 스코어링 중..."
        print("\n===========================================")
        print("🚀 [System] 배포 심의 위원회 소집 및 데이터 추출 시작")
        print("===========================================")

        sap_result = fetch_recent_transports_via_http(user_id=self.user_id)
        tr_data = []
        reasons = []
        score = 0
        deploy_grade = "Low"
        deploy_reason = ""
        deploy_actions = DEPLOY_ACTIONS["Low"]
        object_usage_list = []

        if sap_result["status"] == "success":
            raw_tr_data = sap_result["data"]

            if self.selected_trs:
                tr_by_trkorr = {}
                children_by_strkorr = {}
                for tr in raw_tr_data:
                    trkorr = tr.get("TRKORR") or tr.get("trkorr")
                    if trkorr:
                        tr_by_trkorr[trkorr] = tr
                    strkorr = tr.get("STRKORR") or tr.get("strkorr")
                    if strkorr:
                        children_by_strkorr.setdefault(strkorr, []).append(tr)

                for parent_tr_no in self.selected_trs:
                    parent_obj = tr_by_trkorr.get(parent_tr_no)
                    if not parent_obj:
                        continue
                    merged_objects = list(
                        parent_obj.get("objects", parent_obj.get("OBJECTS", []))
                    )
                    merged_keys = list(
                        parent_obj.get("keys", parent_obj.get("KEYS", []))
                    )
                    children = children_by_strkorr.get(parent_tr_no, [])
                    for child in children:
                        merged_objects.extend(
                            child.get("objects", child.get("OBJECTS", []))
                        )
                        merged_keys.extend(child.get("keys", child.get("KEYS", [])))
                    enriched_tr = dict(parent_obj)
                    enriched_tr["objects"] = merged_objects
                    enriched_tr["keys"] = merged_keys
                    tr_data.append(enriched_tr)
            else:
                tr_data = raw_tr_data

            tabl_pts = sicf_pts = clas_pts = prog_pts = key_pts = 0
            tabl_count = sicf_count = clas_count = prog_count = 0
            total_keys = 0
            has_struct_change = False
            has_data_overwrite = False

            for tr in tr_data:
                tr_num = tr.get("TRKORR", tr.get("trkorr", "Unknown TR"))
                objects = tr.get("objects", tr.get("OBJECTS", []))
                for obj in objects:
                    obj_type = str(obj.get("OBJECT", obj.get("object", ""))).upper()
                    obj_name = str(obj.get("OBJ_NAME", obj.get("obj_name", "")))
                    if obj_type == "TABL":
                        tabl_count += 1
                        reasons.append(
                            f"[{tr_num}] 테이블 구조({obj_name}) 변경 (DB 락·스키마 위험)"
                        )
                    elif obj_type == "CLAS":
                        clas_count += 1
                        reasons.append(
                            f"[{tr_num}] 클래스({obj_name}) 변경 (사이드 이펙트 위험)"
                        )
                    elif obj_type == "PROG":
                        prog_count += 1
                        reasons.append(f"[{tr_num}] 프로그램({obj_name}) 변경")
                    elif obj_type == "SICF":
                        sicf_count += 1
                        reasons.append(
                            f"[{tr_num}] SICF 노드({obj_name}) 변경 (서비스 노출 위험)"
                        )

                keys = tr.get("keys", tr.get("KEYS", []))
                if keys:
                    key_count = len(keys)
                    total_keys += key_count
                    modified_tables = list(
                        {
                            str(k.get("MASTERNAME", k.get("mastername", "")))
                            for k in keys
                            if k.get("MASTERNAME") or k.get("mastername")
                        }
                    )
                    table_list_str = (
                        ", ".join(modified_tables) if modified_tables else "특정"
                    )
                    reasons.append(
                        f"[{tr_num}] {table_list_str} 테이블 레코드 {key_count}건 덮어쓰기"
                    )

            has_struct_change = tabl_count > 0 or sicf_count > 0 or clas_count > 0
            has_data_overwrite = total_keys > 0

            def _cap_sum(unit: int, cap: int, count: int) -> int:
                return min(unit * count, cap)

            tabl_pts = _cap_sum(25, 50, tabl_count)
            sicf_pts = _cap_sum(20, 40, sicf_count)
            clas_pts = _cap_sum(12, 36, clas_count)
            prog_pts = _cap_sum(5, 25, prog_count)
            key_pts = min(total_keys * 2, 25)

            concentration_bonus = 0
            for tr in tr_data:
                objects = tr.get("objects", tr.get("OBJECTS", []))
                types = [
                    str(o.get("OBJECT", o.get("object", ""))).upper() for o in objects
                ]
                if any(cnt >= 3 for cnt in Counter(types).values()):
                    concentration_bonus = 10
                    break

            multi_impact_bonus = 15 if (has_struct_change and has_data_overwrite) else 0
            raw_score = (
                tabl_pts
                + sicf_pts
                + clas_pts
                + prog_pts
                + key_pts
                + concentration_bonus
                + multi_impact_bonus
            )
            score = min(int(raw_score), 100)

            if score <= 35:
                deploy_grade = "Low"
                deploy_reason = "변경 규모와 영향 범위가 제한적입니다. 테이블 구조·서비스 노출·대량 데이터 변경이 없거나 소수에 그칩니다."
            elif score <= 65:
                deploy_grade = "Medium"
                deploy_reason = "구조 변경 또는 데이터 덮어쓰기가 다수 포함되어 있습니다. 연관 모듈 검증이 필요합니다."
            else:
                deploy_grade = "High"
                deploy_reason = "테이블/서비스/클래스 변경 또는 대량 데이터 수정이 복합적으로 있어, 배포 전 회의·롤백 계획이 필요합니다."

            if reasons:
                deploy_reason += " 상세: " + "; ".join(reasons[:5])
                if len(reasons) > 5:
                    deploy_reason += f" 외 {len(reasons) - 5}건."

            deploy_actions = DEPLOY_ACTIONS[deploy_grade]
            initial_history = (
                f"**시스템 (Rule-based 검증)**: 선택된 메인 TR {len(tr_data)}개(하위 태스크 포함)를 스캔한 결과, "
                f"배포 리스크 등급은 **{deploy_grade}**({deploy_grade == 'Low' and '낮음' or deploy_grade == 'Medium' and '보통' or '높음'})입니다. "
                f"판단 이유: {deploy_reason}\n\n"
                f"**등급별 권장 액션**: " + " | ".join(deploy_actions) + "\n\n"
            )
            print(f"✅ [System] 배포 리스크 등급: {deploy_grade} (raw_score={score})")
            initial_queue = ["bc", "fi", "co", "mm", "sd", "pp"]

            object_usage_list = []
            if self.selected_trs:
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(len(self.selected_trs), 10)
                ) as executor:
                    futures = {
                        executor.submit(fetch_object_usage_via_http, tr_no): tr_no
                        for tr_no in self.selected_trs
                    }
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            usage_result = future.result()
                            if usage_result.get(
                                "status"
                            ) == "success" and usage_result.get("data"):
                                object_usage_list.append(usage_result["data"])
                        except Exception as e:
                            tr_no = futures[future]
                            _logger.exception(
                                "Error fetching object usage concurrently for TR %s: %s",
                                tr_no,
                                e,
                            )

            if object_usage_list:
                print(
                    f"✅ [System] TR 오브젝트 사용처 {len(object_usage_list)}건 수집 완료"
                )
        else:
            initial_history = "**시스템**: TR 데이터를 불러오는 데 실패하여 토의를 진행할 수 없습니다.\n\n"
            initial_queue = []

        return {
            "sap_data_raw": tr_data,
            "rule_score": score,
            "rule_reasons": reasons,
            "deploy_risk_grade": deploy_grade,
            "deploy_risk_reason": deploy_reason,
            "deploy_risk_actions": deploy_actions,
            "discussion_history": initial_history,
            "review_queue": initial_queue,
            "called_counts": {"bc": 0, "fi": 0, "co": 0, "mm": 0, "sd": 0, "pp": 0},
            "object_usage_data": (
                object_usage_list
                if sap_result["status"] == "success" and self.selected_trs
                else []
            ),
        }

    def _node_research(self, state: AgentState):
        """Chroma RAG + CRAG 라이트 + GraphRAG(구조화 종속성)."""
        self.progress["step"] = "research"
        self.progress["label"] = "내부 지식베이스·종속성 그래프 검색 중..."
        print("📚 [Researcher] GraphRAG + CRAG 검색 시작...")
        from api.rag.deploy_graph_rag import (
            build_graph_context_for_deploy,
            graph_query_suffix,
        )
        from api.rag.deploy_research_rag import (
            build_initial_query,
            crag_retrieve_for_deploy_review,
        )

        pf = state.get("pipeline_flags") or {}
        use_graph = bool(pf.get("graph_rag", True))
        use_research = bool(pf.get("research_rag", True))
        use_crag_judge = bool(pf.get("crag_judge", True))

        timings: dict[str, float] = {**(state.get("pipeline_timings_ms") or {})}
        t_node0 = time.perf_counter()

        t_g0 = time.perf_counter()
        if use_graph:
            graph_block, gmeta = build_graph_context_for_deploy(
                state.get("sap_data_raw") or [],
                max_edges=deploy_graph_rag_max_edges(),
                max_hops=deploy_graph_rag_max_hops(),
                max_seeds=deploy_graph_rag_max_seeds(),
            )
        else:
            graph_block = "(GraphRAG 생략: pipeline.graph=false 또는 환경 설정)"
            gmeta = {
                "skipped": True,
                "edge_count": 0,
                "seed_count": 0,
                "reason": "pipeline_or_env",
            }
        timings["graph_rag_ms"] = round((time.perf_counter() - t_g0) * 1000, 2)

        t_r0 = time.perf_counter()
        if use_research:
            k = deploy_research_rag_k()
            q = build_initial_query(
                state.get("user_input") or "",
                state.get("sap_data_raw") or [],
            )
            q = (q or "").strip() + graph_query_suffix(graph_block)
            judge_llm = None
            if use_crag_judge and azure_openai_key() and azure_openai_endpoint():
                judge_llm = self.llm_fast
            block, rmeta = crag_retrieve_for_deploy_review(
                query=q,
                k=k,
                llm_fast=judge_llm,
                user_input=state.get("user_input") or "",
                sap_data_raw=state.get("sap_data_raw") or [],
            )
        else:
            block = "(벡터 RAG 생략: pipeline.research=false 또는 환경 설정)"
            rmeta = {
                "skipped": "research_rag_disabled",
                "rounds": [],
                "final_query": "",
            }
        timings["research_rag_ms"] = round((time.perf_counter() - t_r0) * 1000, 2)
        timings["research_node_total_ms"] = round(
            (time.perf_counter() - t_node0) * 1000, 2
        )
        summary_line = (
            f"쿼리 `{rmeta.get('final_query', q)[:120]}` → "
            f"검색 라운드 {len(rmeta.get('rounds', []))}회"
        )
        if rmeta.get("judgment"):
            summary_line += f" | 판정: {rmeta['judgment']}"
        graph_line = (
            f"**GraphRAG**: 시드 {gmeta.get('seed_count', 0)} | "
            f"간선 {gmeta.get('edge_count', 0)} | hop {gmeta.get('hop_rounds', 0)}"
        )
        new_hist = (
            state["discussion_history"]
            + f"{graph_line}\n**Researcher (CRAG)**:\n{summary_line}\n\n"
        )
        print(f"   ↳ ✅ Researcher 완료 ({graph_line}; {summary_line})")
        return {
            "research_context": block or "(내부 지식베이스 근거 없음)",
            "research_meta": rmeta,
            "graph_context": graph_block,
            "graph_meta": gmeta,
            "discussion_history": new_hist,
            "pipeline_timings_ms": timings,
        }

    def _create_expert_node(self, module_name, role_desc, state_key):
        def expert_node(state: AgentState):
            self.progress["step"] = module_name.lower()
            self.progress["label"] = f"{module_name} 모듈 검토 중..."
            print(f"🤖 [{module_name}] 에이전트 분석 중...")

            if not state["sap_data_raw"]:
                current_queue = list(state.get("review_queue", []))
                if current_queue and current_queue[0] == module_name.lower():
                    current_queue.pop(0)
                return {
                    state_key: "데이터 없음",
                    "discussion_history": state["discussion_history"],
                    "review_queue": current_queue,
                }

            prompt_text = (
                f"당신은 SAP {module_name} 모듈 최고 전문가입니다. {role_desc}\n"
                "배포 위원회에서 담당 모듈 관점으로 **심도 있는 검토**를 제시하세요. 요약이 아닌 구체적 풀어쓰기.\n\n"
                "[🚨 필수] **TR 데이터(아래 [TR 데이터] JSON)에 실제로 등장하는 오브젝트(OBJ_NAME, 테이블명, 프로그램/클래스명)만**을 기준으로 검토하세요. "
                "TR에 없는 오브젝트(예: TR이 EKKO/EKPO만 건드리는데 BKPF/BSEG가 영향받을 수 있다고 하지 마세요)는 언급하지 마세요. "
                "데이터에 나열된 오브젝트만 보고, 그 오브젝트들이 담당 모듈과 어떻게 연관되는지 서술하세요.\n\n"
                "1. **연관 오브젝트·테이블**: [TR 데이터]의 OBJ_NAME 중 귀하 모듈과 연관된 것**만** 구체적으로 나열하고, "
                "각각 이번 변경에서 왜 중요한지 한 문장씩 설명하세요. (TR에 없는 테이블/오브젝트는 절대 추가하지 마세요.)\n"
                "2. **비즈니스 영향**: 위에서 나열한 **TR 내 오브젝트**가 관여하는 업무·트랜잭션(T-Code)·데이터 흐름만 구체적으로 서술하세요.\n"
                "3. **필요 테스트**: 위 오브젝트·로직에 맞는 검증만 나열하세요. (TR에 없는 오브젝트 기준 테스트는 쓰지 마세요.)\n"
                "4. TR에 담당 모듈 연관 오브젝트가 없을 때만 '특이사항 없음' 한 줄. 그 외에는 위 1~3을 **압축 없이** 4~5문장으로 작성. '@모듈명'은 치명적 연계 시 1회만.\n\n"
                "[내부 지식베이스 (Researcher/CRAG — 종속성·티켓 RAG 인덱스)]\n"
                "{research}\n\n"
                "위는 벡터 검색으로 가져온 **보조 근거**입니다. **[TR 데이터]와 충돌하면 TR 데이터를 우선**하고, 내부 지식은 보완·참고만 하세요.\n\n"
                "[구조화 종속성 그래프 (GraphRAG — DB DependencySnapshot)]\n"
                "{graph}\n\n"
                "위는 TR 오브젝트를 시드로 한 **호출·참조 간선**입니다. TR JSON에 없는 오브젝트가 그래프에 나오면 **그래프는 참고용**이며, "
                "발언에서는 **TR에 있는 오브젝트**를 중심으로 서술하세요.\n\n"
                "[이전 토의]\n{history}\n\n[TR 데이터]\n{data}"
            )
            prompt = ChatPromptTemplate.from_messages([("system", prompt_text)])
            chain = prompt | self.llm_fast
            res = chain.invoke(
                {
                    "research": (state.get("research_context") or "").strip()
                    or "(내부 지식베이스 검색 결과 없음 또는 RAG 미적재)",
                    "graph": (state.get("graph_context") or "").strip()
                    or "(GraphRAG 간선 없음 또는 비활성)",
                    "history": state["discussion_history"],
                    "data": json.dumps(state["sap_data_raw"], ensure_ascii=False),
                }
            )
            content = res.content
            new_history = (
                state["discussion_history"]
                + f"**{module_name} 에이전트**: {content}\n\n"
            )
            current_queue = list(state.get("review_queue", []))
            called_counts = dict(state.get("called_counts", {}))
            if current_queue and current_queue[0] == module_name.lower():
                current_queue.pop(0)
            called_counts[module_name.lower()] = (
                called_counts.get(module_name.lower(), 0) + 1
            )
            called_modules = re.findall(r"@(BC|FI|CO|MM|SD|PP)", content, re.IGNORECASE)
            for mod in reversed(called_modules):
                mod_lower = mod.lower()
                if mod_lower != module_name.lower() and mod_lower not in current_queue:
                    if called_counts.get(mod_lower, 0) < 2:
                        current_queue.insert(0, mod_lower)
                    else:
                        print(
                            f"   ↳ 🛑 [{mod_lower.upper()}] 모듈은 이미 최대 발언 횟수를 채워 반송을 차단합니다."
                        )
            print(f"   ↳ ✨ [{module_name}] 검토 완료. (남은 대기열: {current_queue})")
            return {
                state_key: content,
                "discussion_history": new_history,
                "review_queue": current_queue,
                "called_counts": called_counts,
            }

        return expert_node

    def _node_report_generator(self, state: AgentState):
        self.progress["step"] = "architect"
        self.progress["label"] = "수석 아키텍트가 최종 보고서 작성 중..."
        print("👨‍💼 [Architect] 최종 보고서 작성 중...")
        if not state["sap_data_raw"]:
            return {"final_report": "SAP 시스템에서 데이터를 가져오지 못했습니다."}

        grade = state.get("deploy_risk_grade") or "Low"
        grade_ko = "낮음" if grade == "Low" else "보통" if grade == "Medium" else "높음"
        reason = state.get("deploy_risk_reason") or ""
        actions = state.get("deploy_risk_actions") or DEPLOY_ACTIONS.get(
            grade, DEPLOY_ACTIONS["Low"]
        )
        actions_text = "\n".join(f"- {a}" for a in actions)
        usage_data = state.get("object_usage_data") or []
        usage_json = json.dumps(usage_data, ensure_ascii=False) if usage_data else "[]"

        usage_section_instruction = (
            (
                "\n\n### 4. TR 오브젝트 사용처 및 테스트 권장\n"
                "아래 [TR 오브젝트 사용처] 데이터를 반드시 반영하세요. "
                "각 오브젝트에 대해 **어디서(호출하는 프로그램/클래스)** **어떤 연산(호출/SUBMIT/MODIFY/UPDATE/INSERT/DELETE/APPEND/SELECT)**으로 사용되는지** 요약하고, "
                "**그 프로그램들에 대한 테스트가 필요함**을 명시하세요. 데이터가 없으면 '사용처 데이터 없음' 한 줄로 표시.\n\n"
                "[TR 오브젝트 사용처]\n{usage_json}\n\n"
                "### 5. 수석 아키텍트 종합 요약\n"
                "전체를 3~5문장으로 요약. 어떤 변경·어떤 모듈 검증·배포 시 유의점을 한눈에 정리.\n\n"
                "### 6. 최종 결론\n"
            )
            if usage_data
            else (
                "\n\n### 4. 수석 아키텍트 종합 요약\n"
                "전체를 3~5문장으로 요약. 어떤 변경·어떤 모듈 검증·배포 시 유의점을 한눈에 정리.\n\n"
                "### 5. 최종 결론\n"
            )
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "당신은 배포 위원회 수석 아키텍트입니다. 회의록을 바탕으로 **품질 높은** 최종 마크다운 보고서를 작성하세요. "
                    "담당자 의견을 충실히 반영하여 한 줄로 줄이지 마세요.\n\n"
                    "[🚨 마크다운 규칙] 문단 들여쓰기(Space 4칸 이상) 금지. 섹션 제목 위아래 빈 줄 2번.\n\n"
                    "[보고서 필수 포맷]\n\n"
                    "### 1. 배포 리스크 등급\n"
                    "- **등급**: {grade} (낮음/보통/높음)\n"
                    "- **판단 이유**: (시스템 이유를 보완하여 2~3문장)\n\n"
                    "### 2. 등급별 권장 액션\n"
                    "(시스템 권장 액션 그대로 넣기)\n\n"
                    "{actions_text}\n\n"
                    "### 3. 배포 위원회 검토 (모듈별)\n"
                    "각 모듈별 #### 소제목(예: #### BC 모듈 검토)을 단 뒤, 담당자가 언급한 **연관 오브젝트·테이블·비즈니스 영향·필요 테스트**를 "
                    "빠짐없이 포함해 **모듈당 4~5문장**으로 풀어서 서술하세요. 압축·한 줄 요약 금지. 특이사항 없음 모듈만 한 줄로 묶으세요."
                    + usage_section_instruction
                    + "- **최종 결정**: 승인 / 조건부 승인 / 반려\n"
                    "- **조치사항**: (권장 액션 참고하여 2~3문장)\n\n"
                    "[시스템 판정] 등급={grade}, 이유={reason}\n\n"
                    "[내부 지식베이스 (Researcher/CRAG)]\n"
                    "{research}\n\n"
                    "[구조화 종속성 그래프 (GraphRAG)]\n"
                    "{graph}\n\n"
                    "[전체 회의록]\n"
                    "{history}",
                ),
            ]
        )
        chain = prompt | self.llm
        res = chain.invoke(
            {
                "grade": grade,
                "grade_ko": grade_ko,
                "reason": reason,
                "actions_text": actions_text,
                "usage_json": usage_json,
                "research": (state.get("research_context") or "").strip() or "(없음)",
                "graph": (state.get("graph_context") or "").strip() or "(없음)",
                "history": state["discussion_history"],
            }
        )
        final_text = res.content.strip()
        if final_text.startswith("```markdown"):
            final_text = final_text[11:].strip()
        elif final_text.startswith("```"):
            final_text = final_text[3:].strip()
        if final_text.endswith("```"):
            final_text = final_text[:-3].strip()
        return {"final_report": final_text}

    def _node_self_rag(self, state: AgentState):
        """Self-RAG: 최종 보고서를 TR·내부 RAG 근거로 검증하고, 필요 시 1회 보정."""
        self.progress["step"] = "self_rag"
        self.progress["label"] = "Self-RAG 근거 검증·보정 중..."
        print("🔍 [Self-RAG] 최종 보고서 근거 검증...")
        from api.rag.deploy_self_rag import review_deploy_final_report

        report = (state.get("final_report") or "").strip()

        pf = state.get("pipeline_flags") or {}
        timings = {**(state.get("pipeline_timings_ms") or {})}

        if not bool(pf.get("self_rag", True)):
            meta = {"skipped": True, "summary": "pipeline.self_rag=false"}
            print(f"   ↳ ⏭️ Self-RAG 생략 ({meta['summary']})")
            return {"self_rag_meta": meta, "pipeline_timings_ms": timings}

        if len(report) < 80:
            meta = {"skipped": True, "summary": "보고서가 너무 짧음"}
            print(f"   ↳ ⏭️ Self-RAG 생략 ({meta['summary']})")
            return {"self_rag_meta": meta, "pipeline_timings_ms": timings}

        t_sr0 = time.perf_counter()
        new_report, meta = review_deploy_final_report(
            final_report=report,
            research_context=state.get("research_context") or "",
            research_meta=state.get("research_meta") or {},
            graph_context=state.get("graph_context") or "",
            graph_meta=state.get("graph_meta") or {},
            sap_data_raw=state.get("sap_data_raw") or [],
            user_input=state.get("user_input") or "",
            llm_fast=self.llm_fast,
        )
        summ = meta.get("summary", "")
        new_hist = state["discussion_history"] + f"**Self-RAG**:\n{summ}\n\n"
        if meta.get("revised"):
            print("   ↳ ✅ Self-RAG 보정 반영")
        elif meta.get("skipped"):
            print(f"   ↳ ⏭️ Self-RAG: {summ}")
        else:
            print("   ↳ ✅ Self-RAG: 수정 불필요(grounded)")
        timings["self_rag_ms"] = round((time.perf_counter() - t_sr0) * 1000, 2)
        return {
            "final_report": new_report,
            "self_rag_meta": meta,
            "discussion_history": new_hist,
            "pipeline_timings_ms": timings,
        }

    def _central_router(self, state: AgentState) -> str:
        queue = state.get("review_queue", [])
        if queue:
            print(
                f"🚦 [라우터] 다음 차례인 '{queue[0].upper()}' 모듈로 문서를 전달합니다."
            )
            return queue[0]
        print("🚦 [라우터] 대기열이 비었습니다. 수석 아키텍트에게 전달합니다.")
        return "architect"

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("fetch_data", self._node_fetch_and_score)
        workflow.add_node("research", self._node_research)
        workflow.add_node(
            "bc",
            self._create_expert_node(
                "BC",
                "시스템 인프라, DB 락, 권한, 공통 클래스 및 SICF등 SAP BC 관련 내용을 책임집니다.",
                "bc_analysis",
            ),
        )
        workflow.add_node(
            "fi",
            self._create_expert_node(
                "FI",
                "재무회계, 전표 처리 테이블 등 SAP FI 관련 내용을 책임집니다.",
                "fi_analysis",
            ),
        )
        workflow.add_node(
            "co",
            self._create_expert_node(
                "CO",
                "관리회계 및 수익성 분석 등 SAP CO 관련 내용을 책임집니다.",
                "co_analysis",
            ),
        )
        workflow.add_node(
            "mm",
            self._create_expert_node(
                "MM",
                "자재/구매/재고 관련 테이블과 로직 등 SAP MM 관련 내용을 책임집니다.",
                "mm_analysis",
            ),
        )
        workflow.add_node(
            "sd",
            self._create_expert_node(
                "SD",
                "영업/판매 관련 기능과 오더 처리 등 SAP SD 관련 내용을 책임집니다.",
                "sd_analysis",
            ),
        )
        workflow.add_node(
            "pp",
            self._create_expert_node(
                "PP",
                "생산 계획 및 제조 실행 등 SAP PP 관련 내용을 책임집니다.",
                "pp_analysis",
            ),
        )
        workflow.add_node("architect", self._node_report_generator)
        workflow.add_node("self_rag", self._node_self_rag)
        workflow.set_entry_point("fetch_data")
        workflow.add_edge("fetch_data", "research")
        workflow.add_conditional_edges("research", self._central_router)
        modules = ["bc", "fi", "co", "mm", "sd", "pp"]
        for mod in modules:
            workflow.add_conditional_edges(
                mod,
                self._central_router,
                {
                    "bc": "bc",
                    "fi": "fi",
                    "co": "co",
                    "mm": "mm",
                    "sd": "sd",
                    "pp": "pp",
                    "architect": "architect",
                },
            )
        workflow.add_edge("architect", "self_rag")
        workflow.add_edge("self_rag", END)
        return workflow.compile()

    def _run_invoke(self, app, initial_state):
        t0 = time.perf_counter()
        invoke_err: Exception | None = None
        faux_req = SimpleNamespace(request_id=self.req_id)
        try:
            try:
                from langchain_community.callbacks import get_openai_callback

                from api.observability import record_stream_usage

                with get_openai_callback() as cb:
                    try:
                        result = app.invoke(
                            initial_state, {**self.config, "callbacks": [cb]}
                        )
                        self.result_holder.append(result)
                    except Exception as e:
                        _logger.exception("Analyze guardian invoke error: %s", e)
                        invoke_err = e
                        self.result_holder.append(
                            {
                                "final_report": "분석 실행 중 오류가 발생했습니다. 상세 내용은 서버 로그를 확인하세요."
                            }
                        )
                        print(f"🔥 [Error] {e}")
                    finally:
                        record_stream_usage(
                            "analyze_deploy_graph",
                            faux_req,
                            cb,
                            t0=t0,
                            err=invoke_err,
                        )
            except ImportError:
                result = app.invoke(initial_state, self.config)
                self.result_holder.append(result)
        except Exception as e:
            _logger.exception("Analyze guardian unexpected error: %s", e)
            self.result_holder.append(
                {
                    "final_report": "분석 중 예기치 않은 오류가 발생했습니다. 상세 내용은 서버 로그를 확인하세요."
                }
            )
            print(f"🔥 [Error] {e}")

    async def _stream_generator(self, app, initial_state):
        self.progress["step"] = "fetch_data"
        self.progress["label"] = "시작 중..."
        t = threading.Thread(target=self._run_invoke, args=(app, initial_state))
        t.start()
        last_sent = None
        while t.is_alive():
            cur = {
                "step": self.progress.get("step", ""),
                "label": self.progress.get("label", ""),
            }
            if cur != last_sent:
                last_sent = dict(cur)
                yield json.dumps(cur, ensure_ascii=False) + "\n"
            await asyncio.sleep(0.25)
        reply = "보고서 생성 실패"
        raw_state: dict = {}
        if self.result_holder:
            raw_state = self.result_holder[0]
            if not isinstance(raw_state, dict):
                raw_state = {}
            reply = raw_state.get("final_report", reply)
        pipeline_summary = build_deploy_pipeline_summary(raw_state)
        raw_state_out = {**raw_state, "pipeline_summary": pipeline_summary}
        if self.persist_report:
            try:
                await sync_to_async(save_deploy_report_record)(
                    request_id=str(self.req_id),
                    user_id=str(self.user_id or ""),
                    user_input=str(self.user_input or ""),
                    selected_trs=self.selected_trs,
                    final_report=reply,
                    graph_state=raw_state_out,
                )
            except Exception as e:
                print(f"🔥 [Persist] deploy report DB 저장 실패: {e}")
        done_obj: dict = {"done": True, "reply": reply}
        if self.include_pipeline_summary:
            done_obj["pipeline_summary"] = pipeline_summary
        yield json.dumps(done_obj, ensure_ascii=False) + "\n"
