# CTS Bundler – AI 기술 스택 및 기술적 심층 정리

이 문서는 CTS Bundler 프로젝트에서 사용된 **AI/ML 관련 기술 전반**을 기술적 깊이와 함께 정리하고, **난이도**, **극복한 과제**, **해결 방식**을 포함합니다.

---

## 1. 기술 스택 요약

| 영역 | 기술 | 난이도 | 비고 |
|------|------|--------|------|
| **MCP** | FastMCP, stdio / Streamable HTTP 이중 전송 | 중상 | Cursor 연동 + 외부 클라이언트 동시 지원 |
| **RAG** | ChromaDB, Azure OpenAI Embeddings, LangChain | 중 | retrieve-then-generate, Django 모델 기반 ingest |
| **ReAct 에이전트** | LangGraph `create_react_agent`, Azure OpenAI, 멀티 도구 | 중상 | 로컬 도구 + **외부 MCP를 LangChain 도구로 동적 래핑** |
| **외부 MCP 클라이언트** | Python `mcp` SDK, Streamable HTTP, async↔sync 브릿지 | 상 | Django 동기 환경에서 비동기 MCP 세션 호출 |
| **ADT MCP HTTP 브릿지** | Node.js stdio→Streamable HTTP, 요청별 서버/트랜스포트 | 상 | stdio 전용 서버에 HTTP 진입점 추가, Stateless per-request 패턴 |
| **구조화 출력** | Pydantic, `with_structured_output` | 중하 | 의도·추천 액션 등 구조화 채팅 응답 |
| **응답 캐시** | in-memory TTL 캐시 (동일 질문 재사용) | 하 | 300초 TTL |
| **배포 심의 워크플로** | LangGraph `StateGraph`, RAG 1~4단계(Researcher/CRAG·Self-RAG·GraphRAG·파이프라인) | 상 | 모듈 전문가 + 아키텍트 + NDJSON 스트리밍. 상세는 **§7 로드맵** |
| **Dependency Map 노이즈 필터** | LLM 기반 JSON 필터 (노드/링크 정제) | 중상 | DDIC/ALV 등 대량 노이즈 제거, 비즈니스 관점 유지 |
| **AI 코드 리뷰** | ChatPromptTemplate, 요구사항 대비 검증 | 중 | 요구사항↔코드 일치 여부 LLM 판정 |

---

## 2. MCP (Model Context Protocol)

### 목적
- Cursor, Claude Desktop 등 AI 클라이언트가 CTS Bundler 데이터(TR, 종속성, 티켓, RAG)에 **표준 프로토콜**로 접근.
- 동시에 **외부 앱·웹**에서도 MCP로 접속 가능하도록 **이중 전송** 지원.

### 구현
- **`api/mcp_server.py`**: FastMCP 기반. Django bootstrap 후 `fetch_recent_transports_via_http`, `DependencySnapshot`, `TicketMapping`, RAG `services` 사용.
- **도구**: `list_transports`, `get_dependency_edges`, `get_ticket_mapping`, `search_rag`, `rag_ask` (RAG 검색만 / RAG+LLM 답변 생성).

### 전송 방식
- **stdio**: Cursor 전용. Cursor가 프로세스를 띄우므로 사용자가 서버를 따로 실행할 필요 없음.
- **Streamable HTTP / SSE**: `--transport streamable-http --port 8020` (또는 `sse`). 외부 클라이언트가 `http://<host>:8020/mcp` 로 접속.

### 기술 포인트
- MCP 스펙(Streamable HTTP, SSE)에 맞춰 **동일 로직을 두 전송에서 공유**하고, 실행 모드만 CLI 인자로 분기.

---

## 3. RAG (Retrieval-Augmented Generation)

### 목적
- 지식베이스(종속성 스냅샷, 티켓 매핑, 추후 문서)를 **벡터 검색**으로 가져와 LLM 컨텍스트에 넣어, 환각을 줄이고 **근거 기반 답변** 제공.

### 스택
- **Vector DB**: ChromaDB, 로컬 persist (`backend/data/chroma`).
- **Embeddings**: Azure OpenAI Embeddings (`text-embedding-3-small` 등). Azure 미설정 시 OpenAI 호환 엔드포인트 fallback.
- **Orchestration**: LangChain (document load, split, retrieve, chain).

### 구현
- **`api/rag/services.py`**: `get_embeddings()`, `get_vector_store()`, `ingest_from_django_models()` (DependencySnapshot + TicketMapping → Document), `ingest_from_texts()`, `retrieve()`, `rag_chain_invoke()` (retrieve + ChatPromptTemplate | LLM).
- **API**: `POST /api/rag/ingest/` (DB 기반 또는 custom texts, `clear=true` 옵션), `POST /api/rag/query/` (query, k, retrieve_only).

### 기술 포인트
- Django 모델을 **Document로 변환해 일괄 임베딩** 후 Chroma에 적재. 대량 데이터 시 `RAG_INGEST_MAX_DOCS` 등으로 제한해 임베딩 비용·시간 조절.

---

## 4. 채팅 확장 (RAG + 구조화 출력 + 캐시)

### 엔드포인트
- `POST /api/chat/rag/`: `message`, `use_rag`, `use_structured`, `use_cache`.

### 기술 포인트
- **구조화 출력**: Pydantic `ChatStructuredOutput` (reply, intent, suggested_actions) + LLM `with_structured_output()`으로 **스키마 준수 응답** 보장.
- **캐시**: 동일 질문에 대해 in-memory TTL 300초 캐시로 **동일 쿼리 재사용** 및 비용/지연 절감.

---

## 5. ReAct 에이전트 (도구 사용 에이전트)

### 목적
- 사용자 질문에 대해 **Reason → Act → Reason → …** 반복으로 도구를 호출하며 최종 답변 생성. 단순 try/except가 아니라 **실제 ReAct 루프** 수행.

### 스택
- **LangGraph** `create_react_agent` + **Azure OpenAI** (도구 바인딩 필수).
- **도구 구성**: 로컬 도구 4개 (`list_transports`, `get_dependency_edges`, `get_ticket_mapping`, `search_rag`) + **외부 SAP Docs MCP** (공개 URL) + **외부 ABAP ADT MCP** (GetClass, GetTable 등, HTTP로 띄운 경우).

### 구현
- **`api/views/agent.py`**: `_make_tools()`에서 로컬 도구 정의 후, `get_external_sap_docs_tools()`, `get_external_adt_tools()`로 **원격 MCP 도구를 LangChain StructuredTool로 래핑**해 동일 에이전트에 통합.
- **시스템 프롬프트**: “클래스/테이블 소스·구조 요청 → GetClass/GetTable”, “종속성/호출 관계만 → get_dependency_edges” 등 **도구 선택 규칙**을 명시해 LLM이 잘못된 도구를 선택하는 문제 완화.

### 기술적 난이도
- **멀티 소스 도구**: 로컬 + 외부 MCP를 **하나의 ReAct 에이전트**에서 사용하려면, 외부 MCP의 도구 목록/스키마를 **동적으로 가져와** Pydantic 스키마 생성 + `StructuredTool.from_function`으로 래핑해야 함. `api/mcp_client.py`에서 **tools/list 캐시** + **inputSchema → create_model** 로 해결.

---

## 6. 외부 MCP 클라이언트 (mcp_client.py)

### 목적
- SAP Docs MCP(공개 URL), ABAP ADT MCP(자체 HTTP 인스턴스) 등 **외부 MCP 서버**에 연결해 도구 목록을 가져오고, ReAct 에이전트에서 호출 가능한 **LangChain 도구**로 변환.

### 기술 스택
- Python **`mcp`** SDK: `streamable_http_client`, **`sse_client`**, `ClientSession`, `session.initialize()`, `list_tools()`, `call_tool()`.
- **이중 전송**: 먼저 **Streamable HTTP**로 시도하고, 실패 시 **SSE**로 재시도 (`tools/list`·`call_tool` 공통). 서버 구현에 따라 한쪽만 지원하는 경우가 많음.
- **HTTP 클라이언트**: MCP 호출용 **`httpx.AsyncClient`**를 앱에서 생성해 전달 — `follow_redirects`, 타임아웃, **`verify=`** (환경 변수 `EXTERNAL_SAP_MCP_VERIFY_SSL` 기본 `true`, 기업 프록시·자체서명 체인 시에만 `false`).

### 난이도와 극복 과제

#### 1) Django 동기 환경 ↔ MCP 비동기 클라이언트
- **문제**: MCP SDK는 async API. Django 뷰/에이전트는 동기. `streamable_http_client` + `ClientSession`은 모두 코루틴 기반.
- **해결**: `_run_async()` 헬퍼로 `asyncio.run(coro)` 또는 기존 이벤트 루프가 있으면 `ThreadPoolExecutor` 안에서 `asyncio.run()` 호출해 **동기 컨텍스트에서 비동기 MCP 호출** 수행. (`api/mcp_client.py`)

#### 2) 원격 도구 → LangChain StructuredTool
- **문제**: MCP `Tool`은 name, description, inputSchema(JSON Schema). LangChain은 `StructuredTool` + Pydantic args schema 필요.
- **해결**: `inputSchema.properties`/`required`를 파싱해 `pydantic.create_model()`으로 동적 Args 모델 생성. `_invoke(**kwargs)`에서 `_call_remote_tool(url, tool_name, kwargs)`를 `_run_async`로 호출. (`_make_remote_tool`)

#### 3) ADT MCP는 stdio 전용
- **문제**: mario-andreschak/mcp-abap-adt는 **stdio**만 지원. Django는 HTTP 클라이언트로만 호출 가능.
- **해결**: CTS_Bundler 내 **mcp-abap-adt**에 **Streamable HTTP 진입점** 추가. Node.js `StreamableHTTPServerTransport`(MCP SDK) + `http.createServer`로 `/mcp` 엔드포인트 제공. **요청별로** 새 MCP 서버 인스턴스 + 새 transport 생성(Stateless 패턴), 응답 후 cleanup. (`mcp-abap-adt/src/server-http.ts`, `npm run start:http`). 자세한 설정은 [`EXTERNAL_SAP_MCP.md`](./EXTERNAL_SAP_MCP.md) 참고.

#### 4) 로그에 `TaskGroup` / `ExceptionGroup`만 보임
- **문제**: Python 3.11+에서 MCP 내부 `anyio` TaskGroup 실패 시 **중첩 예외**가 한 줄로만 보일 수 있음.
- **해결**: `_exception_leaves()`로 leaf 예외를 펼쳐 `detail=`에 기록 (`api/mcp_client.py`).

#### 5) 에이전트 최종 답변에 도구 원문·JSON 노출
- **문제**: LLM이 TR 불릿·SAP Docs **`search`의 `{"results":[...]}` JSON**을 답변 앞에 그대로 붙임.
- **해결**: **`api/agent_reply_cleanup.py`**에서 TR 블록 dedupe·레거시 힌트 제거·선행 JSON blob 제거; 프론트 **`agentReplyCleanup.js`**에서 동일 규칙. 시스템 프롬프트 **`api/prompts/agent.py`**에 “JSON·원시 도구 출력 금지” 명시.

---

## 7. LangGraph 배포 심의 워크플로

### 목적
- 사용자가 선택한 TR에 대해 **Rule 기반 리스크 스코어** → **Researcher(내부 RAG/CRAG 라이트)** → **모듈별 전문가 노드(BC/FI/CO/MM/SD/PP)** → **수석 아키텍트**가 최종 배포 보고서 생성. 프론트엔드는 **진행 상태 스트리밍**으로 UX 제공.

### 스택
- **LangGraph** `StateGraph(AgentState)`, `add_node`, `add_conditional_edges`, `set_entry_point`, `compile()`.
- **AgentState**: user_input, sap_data_raw, rule_score, deploy_risk_grade, 모듈별 analysis 문자열, discussion_history, final_report, review_queue, object_usage_data, **`research_context` / `research_meta`**, **`graph_context` / `graph_meta`**, **`self_rag_meta`** 등.
- **조건부 라우팅**: `central_router(state)`가 `review_queue`에 따라 다음 노드(모듈명 또는 `architect`) 반환.

### 배포 심의 RAG 로드맵 (1~4단계): 요약·예시

배포 심의(`POST /api/analyze/`) LangGraph 안에서 **검색 품질 → 구조화 근거 → 환각 완화 → 운영 제어** 순으로 단계를 쌓았습니다. 환경 변수는 [`LLM_BUDGETS.md`](./LLM_BUDGETS.md), API 필드는 [`API_CONTRACT.md`](./API_CONTRACT.md)를 참고하세요.

---

#### 1단계 — Researcher + CRAG 라이트 (벡터 검색 보강)

| 항목 | 설명 |
|------|------|
| **한 일** | TR·사용자 메시지로 **검색 쿼리**를 만든 뒤 Chroma에서 문서를 가져오고, 필요하면 **소형 LLM**이 “이 청크가 이번 심의에 도움이 되는가?”를 판단합니다. 도움이 아니면 **쿼리를 한 번만 다시 쓰고** 재검색합니다. |
| **왜** | 임베딩 검색만으로는 질문과 안 맞는 덩어리가 섞일 수 있어, **짧은 CRAG 루프**로 노이즈를 줄입니다. |
| **코드** | `api/rag/deploy_research_rag.py`, `api/views/analyze.py`의 `node_research` (Chroma 호출 + 선택적 `with_structured_output` 판정). |
| **상태** | `research_context`(전문가·아키텍트 프롬프트의 `[내부 지식베이스]`), `research_meta`(라운드·판정 등). |

**예시 (개념)**

1. 쿼리 초안: 사용자 입력 `"MM 테이블 변경 리스크 확인"` + TR 오브젝트 `PROG:ZMMR0030, TABL:EKKO` 를 한 줄로 합침.  
2. Chroma `retrieve` → 상위 k(기본 6)개 문서.  
3. fast LLM 판정: `relevant: false`, `rewritten_query: "ZMMR0030 EKKO 구매 테이블 종속성"` → **한 번만** 재검색.  
4. 최종 본문이 `research_context`로 BC/FI/…/아키텍트에게 전달. **TR JSON과 충돌하면 TR 우선**으로 프롬프트에 명시.

**끄기·조절**: `DEPLOY_RESEARCH_RAG_ENABLED`, `DEPLOY_CRAG_JUDGE_ENABLED`, `DEPLOY_RESEARCH_RAG_K` (4단계 `pipeline.research` / `crag_judge`로 요청별 오버라이드 가능).

---

#### 2단계 — Self-RAG (최종 보고서 근거 검증·1회 보정)

| 항목 | 설명 |
|------|------|
| **한 일** | 아키텍트가 만든 **최종 마크다운 보고서**를 fast LLM이 **TR·내부 RAG·(3단계) 그래프**와 대조해 `is_grounded` / `issues`로 심사합니다. **근거 부족**이면 같은 근거만 보고 **전체 보고서를 1번** 고쳐 씁니다. |
| **왜** | 회의록 생성 단계에서 **없는 사실·과장**이 섞이는 것을 줄이기 위함입니다. |
| **코드** | `api/rag/deploy_self_rag.py`, `node_self_rag` (아키텍트 다음 → **`END` 직전 마지막 노드**). |
| **상태** | `self_rag_meta` (판정·보정 여부 등). |

**예시 (개념)**

- 심사 결과: `is_grounded: false`, `issues: ["TR에 없는 프로그램 ZFI999를 이번 변경으로 단정"]`  
- 보정 프롬프트: 위 지적 + TR JSON 일부 + `research_context` + `graph_context`를 넣고, **구조는 유지한 채 문제 문장만 삭제·완화**.

**끄기**: `DEPLOY_SELF_RAG_ENABLED` 또는 `pipeline.self_rag: false`.

---

#### 3단계 — GraphRAG (DB 종속성 스냅샷을 텍스트 그래프로)

| 항목 | 설명 |
|------|------|
| **한 일** | TR의 **OBJ_NAME**들을 시드로 Django **`DependencySnapshot`**에서 `source_obj → target_obj` 간선을 읽어, **마크다운 리스트**로 만듭니다. 이걸 전문가·아키텍트·Self-RAG에 넣고, **1단계 Chroma 쿼리 끝에 짧은 요약**도 붙여 검색을 보강합니다. |
| **왜** | 벡터 RAG는 문장 단위라 **호출 관계**가 흐릿할 때가 있어, **구조화 엣지**를 병행합니다. |
| **코드** | `api/rag/deploy_graph_rag.py`, `node_research` 안에서 그래프 블록 생성 후 `graph_context` / `graph_meta` 설정. |
| **주의** | 그래프에 나오는 이웃 오브젝트가 **이번 TR에 없을 수 있음** → 프롬프트에서 “TR 중심, 그래프는 참고”로 제한. |

**예시 (개념)**

```text
[GraphRAG: DependencySnapshot 부분 그래프] 시드 3개, 간선 12건 ...
- `ZMMR0030` → `EKKO` (group=4)
- `ZMMR0030` → `MARA` (group=4)
```

**끄기·조절**: `DEPLOY_GRAPH_RAG_ENABLED`, `DEPLOY_GRAPH_RAG_MAX_EDGES`, `MAX_HOPS`, `MAX_SEEDS` 또는 `pipeline.graph: false`.

---

#### 4단계 — 파이프라인 통합 (플래그·타이밍·요약)

| 항목 | 설명 |
|------|------|
| **한 일** | **`.env` 기본값**과 **`POST` body의 `pipeline`**을 합쳐 1~3단계 구성요소를 켜고 끕니다. 실행 중 **노드별 소요 시간(ms)**을 모아 **`pipeline_summary`**로 정리하고, DB 저장 시 `DeployReportRecord.extra`에 넣습니다. |
| **왜** | 비용·지연 실험(예: Self-RAG만 끄고 비교), 장애 분석, 운영 문서화를 한 객체로 맞추기 위함입니다. |
| **코드** | `api/rag/deploy_pipeline.py` (`resolve_deploy_pipeline_flags`, `build_deploy_pipeline_summary`), `analyze.py`의 `pipeline_flags` / `pipeline_timings_ms`. |

**요청 예시 (JSON)**

```json
{
  "message": "배포 검토 부탁",
  "user_id": "DEMO",
  "selected_trs": ["DEVK900001"],
  "pipeline": {
    "research": true,
    "graph": true,
    "self_rag": false,
    "crag_judge": true
  },
  "include_pipeline_summary": true
}
```

- `research: false`이면 Chroma 검색·CRAG 판정 생략 → **`crag_judge`는 자동 false**.  
- `include_pipeline_summary: true`이면 스트림 **마지막 NDJSON**에 `pipeline_summary` 필드가 추가됩니다.  
- 저장된 리포트는 `extra.pipeline_flags`, `extra.pipeline_timings_ms`, `extra.pipeline_summary` 등으로 동일 정보를 열람할 수 있습니다.

---

### 구현
- **`api/views/analyze.py`**: `node_fetch_and_score`(SAP TR 조회, Rule 스코어, 오브젝트 사용처 fetch) → **`node_research`** → `central_router` → `node_bc`/`node_fi`/…/`node_architect` → **`node_self_rag`**. Researcher는 **`api/rag/deploy_research_rag.py`**: Chroma `retrieve` 후(선택) **gpt-4o-mini 등 fast LLM**으로 관련성 판단·쿼리 1회 재작성 후 재검색(CRAG 라이트). 검색 본문은 **`research_context`**로 모듈 전문가·아키텍트 프롬프트의 `[내부 지식베이스]`에 주입되며, **TR 데이터와 충돌 시 TR 우선**으로 명시. Top-k는 **`DEPLOY_RESEARCH_RAG_K`**(기본 6, `api/config.py`).
- **Self-RAG(2단계)**: **`api/rag/deploy_self_rag.py`** — 아키텍트 **`final_report`**에 대해 fast LLM **구조화 심사**(`is_grounded`, `issues`, `severity`). `is_grounded=false`이면 **동일 근거(TR·Researcher·GraphRAG)**로 **1회 보정** 재생성. 메타는 **`self_rag_meta`**, 배포 리포트 `extra`에 포함. 끄려면 **`DEPLOY_SELF_RAG_ENABLED=false`** (`api/config.py`).
- **GraphRAG(3단계)**: **`api/rag/deploy_graph_rag.py`** — TR **`objects`의 OBJ_NAME**을 시드로 **`DependencySnapshot`**에서 `source_obj`/`target_obj` 간선을 수집(홉·간선 상한). **`graph_context`**로 모듈 전문가·아키텍트·Self-RAG에 주입하고, Researcher의 **Chroma 쿼리**에 짧은 그래프 요약을 **접미사**로 붙여 검색 보강. 메타 **`graph_meta`**는 `DeployReportRecord.extra`에 포함. **`DEPLOY_GRAPH_RAG_*`** 환경 변수로 조절 (`api/config.py`).
- **파이프라인 통합(4단계)**: **`api/rag/deploy_pipeline.py`** — **`resolve_deploy_pipeline_flags`**: `.env` 기본 + 요청 **`pipeline`** JSON으로 단계별 on/off. **`build_deploy_pipeline_summary`**: 플래그·`pipeline_timings_ms`(research 노드: `graph_rag_ms`, `research_rag_ms` 등 / Self-RAG: `self_rag_ms`)·RAG·그래프·Self-RAG 요약을 **`pipeline_summary`**로 정리. LangGraph **`pipeline_flags`**·**`pipeline_timings_ms`** 상태에 저장 후 `DeployReportRecord.extra`에 포함. 스트림 마지막에 요약을 붙이려면 **`include_pipeline_summary: true`**. 벡터 RAG를 끄면 **`crag_judge`는 자동 off**. 환경: **`DEPLOY_RESEARCH_RAG_ENABLED`**, **`DEPLOY_CRAG_JUDGE_ENABLED`** (`api/config.py`).
- 각 모듈 노드는 전용 ChatPromptTemplate + LLM으로 분석문 작성 후 `discussion_history`에 누적. 아키텍트 노드는 전체 히스토리 + 오브젝트 사용처 + 내부 RAG 맥락을 반영한 최종 보고서 생성.
- **스트리밍**: `StreamingHttpResponse` + 백그라운드 스레드에서 `app.invoke()`. 주기적으로 `progress["step"]`/`progress["label"]`을 NDJSON으로 전송. (`stream_generator`)

### 기술적 난이도
- **멀티 노드 + 상태 공유**: TypedDict 기반 상태를 노드 간 전달하고, 조건부 엣지로 **동적 라우팅**하는 패턴. 재귀 한도(`recursion_limit`) 설정 필요.
- **TR 오브젝트 사용처 통합**: `fetch_object_usage_via_http(trkorr)`로 사용처 데이터를 가져와 `object_usage_data`에 넣고, 아키텍트 프롬프트에 “테스트 권장 프로그램” 등으로 반영. 설계는 [`OBJECT_USAGE_DESIGN.md`](./OBJECT_USAGE_DESIGN.md) 참고.

---

## 8. Dependency Map LLM 노이즈 필터

### 목적
- 종속성 Raw Data(노드/링크)가 많을 때 **DDIC 설명 테이블(DD02T, DD03T 등), ALV/Grid 공통 컴포넌트(LVC_*, CL_SALV_* 등)** 등 **노이즈**를 제거해, 맵을 **25~40개 노드 수준의 핵심 비즈니스 구조**로 정제.

### 구현
- **`api/views/dependency.py`**: 노드/링크 수가 5개 이상일 때만 필터 적용. `AZURE_OPENAI_MAP_FILTER_DEPLOYMENT_NAME`(기본 gpt-4o-mini)으로 **ChatPromptTemplate** 구성. 시스템 프롬프트에 “제거할 노이즈”(description 테이블, ALV, DDIC 메타 등)와 “반드시 유지”(EKKO, MARA, Z/Y 오브젝트, N:N 거미줄 구조)를 명시. LLM 출력을 **순수 JSON**(nodes, links)으로 요구하고, 파싱 후 응답. 실패 시 필터 없이 원본 반환.

### 기술적 난이도
- **안정적인 JSON 출력**: ```json … ``` 제거, 파싱 예외 처리로 **프로덕션에서 필터 실패 시에도 맵 API는 동작**하도록 함.

---

## 9. 기타 AI 활용

| 기능 | 기술 | 비고 |
|------|------|------|
| **SAP 챗봇** | LangChain `ChatPromptTemplate \| llm` | `api/views/chat.py` |
| **AI 코드 리뷰** | 요구사항 대비 코드 검증용 ChatPromptTemplate | `api/views/code_review.py` |
| **ADT 쓰기** | PyPI `abap-adt-py` → `abap_adt_py` + CSRF 처리 | `pip install abap-adt-py` 필수. `.env`: `SAP_ADT_HOST`/`SAP_ADT_USER`/`SAP_ADT_PASSWORD` (또는 `SAP_HTTP_URL`/`SAP_USER`/`SAP_PASSWD`) |

---

## 10. 환경 변수 (AI 관련)

- **Azure OpenAI**: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT_NAME`, `AZURE_OPENAI_FAST_DEPLOYMENT_NAME`, `AZURE_OPENAI_MAP_FILTER_DEPLOYMENT_NAME`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME`, `AZURE_OPENAI_API_VERSION`
- **RAG**: `CHROMA_PERSIST_DIR`, `RAG_COLLECTION_NAME`, `RAG_INGEST_MAX_DOCS`, `RAG_DEFAULT_K`, `RAG_QUERY_MAX_K`, `MCP_RAG_QUERY_MAX_K`
- **LLM 예산·온도·그래프 한도**: [`LLM_BUDGETS.md`](./LLM_BUDGETS.md) 및 `../backend/.env.example` (`LLM_*`, `CHAT_RAG_CACHE_TTL_SEC`, `ANALYZE_GRAPH_RECURSION_LIMIT` 등)
- **관측**: `CTS_LOG_LEVEL`, (선택) `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`
- **외부 MCP**: `EXTERNAL_SAP_MCP_DOCS_ABAP_URL`, `EXTERNAL_SAP_MCP_DOCS_FULL_URL`, `EXTERNAL_SAP_MCP_ADT_URL`, `EXTERNAL_SAP_MCP_ADT_TOOLS`, `EXTERNAL_SAP_MCP_VERIFY_SSL` (기본 검증 on; 프록시 SSL 오류 시에만 `false`)
- **Docker DB 경로(선택)**: `SQLITE_PATH` — 미설정 시 기본 `backend/db.sqlite3`. [`DOCKER.md`](./DOCKER.md) 참고.
- **SAP ADT 쓰기** (`/api/adt-write/`): `SAP_ADT_HOST`, `SAP_ADT_USER`, `SAP_ADT_PASSWORD`, 선택 `SAP_ADT_CLIENT`, `SAP_ADT_LANGUAGE` (미설정 시 HTTP 로그인 변수로 대체)

---

## 11. 관련 문서

- **루트 시작 가이드**: 저장소 루트 [`README.md`](../README.md)
- **문서 색인**: [`docs/README.md`](./README.md)
- **HTTP API 계약 요약**: [`API_CONTRACT.md`](./API_CONTRACT.md)
- **Docker 풀스택(UI+API)**: [`DOCKER.md`](./DOCKER.md)
- **LLM·RAG 예산(환경 변수)**: [`LLM_BUDGETS.md`](./LLM_BUDGETS.md)
- **MCP 서버 실행·Cursor 연동**: [`MCP_README.md`](./MCP_README.md)
- **사용 순서 (RAG 인덱싱 → 채팅 → 에이전트 → MCP)**: [`USAGE_STEPS.md`](./USAGE_STEPS.md)
- **외부 SAP MCP(문서/ADT) 설정·ADT HTTP 띄우기**: [`EXTERNAL_SAP_MCP.md`](./EXTERNAL_SAP_MCP.md)
- **문제·해결 이력·마이그레이션 메모**: [`PROBLEM_SOLUTION_LOG.md`](./PROBLEM_SOLUTION_LOG.md)
- **TR 오브젝트 사용처·배포 보고서 통합 설계**: [`OBJECT_USAGE_DESIGN.md`](./OBJECT_USAGE_DESIGN.md)

---

## 12. 운영·한계 및 알려진 이슈

- **Azure 미설정**: 채팅·에이전트·RAG 생성·코드 리뷰·맵 필터 등 LLM 경로는 `503` 또는 안내 메시지로 동작. 임베딩 fallback은 `OPENAI_API_KEY` 등 별도 설정 필요.
- **RAG 미 ingest**: 벡터 스토어가 비어 있으면 retrieve 결과가 없고, 답변이 “문서에 없습니다” 쪽으로 기우거나 컨텍스트 없이 일반 LLM에 가까워질 수 있음.
- **`/api/chat/rag/` 캐시**: 동일 질문은 TTL 동안 in-memory 캐시를 탐. **ingest 후에도 캐시는 자동 무효화되지 않음** (`CHAT_RAG_CACHE_TTL_SEC=0` 또는 재시작으로 해결).
- **스트리밍·프록시**: `code-review` `stream: true`는 `text/plain` 청크. 앞단 Nginx 등에서 **버퍼링**하면 한 번에만 보일 수 있음 (`X-Accel-Buffering: no` 등).
- **외부 MCP**: Docs/ADT URL이 없거나 타임아웃·SSL 실패 시 해당 도구는 비어 있거나 호출이 실패할 수 있음. 로그 `agent.react tools:`로 `docs_tools`/`adt_tools` 개수 확인. **프로세스당 `tools/list` 캐시** — `.env` 수정 후 **Django 재시작** 권장. HTTPS는 **Streamable HTTP → SSE** 순으로 시도; `CERTIFICATE_VERIFY_FAILED` 시 조직 CA 설치 우선, 불가 시 `EXTERNAL_SAP_MCP_VERIFY_SSL=false`(비권장).
- **ReAct 답변 품질**: 모델이 도구 출력을 중복·JSON 그대로 붙이는 경우 후처리·프롬프트로 완화; 완벽하지 않을 수 있음.
- **동기 Django + 비동기 MCP**: `mcp_client`는 스레드/`asyncio.run` 브릿지 사용. 고동시성에서는 워커·타임아웃 튜닝이 필요.
- **SQLite 기본 DB**: 단일 파일 DB는 동시 쓰기 한계가 있음. 상용 다 사용자·고부하는 Postgres 등 이전 권장. **코드 리뷰·배포 심의 리포트**는 `CodeReviewRecord` / `DeployReportRecord`로 같은 DB에 적재되며, `GET /api/code-review-history/` 등으로 조회 ([`API_CONTRACT.md`](./API_CONTRACT.md)).
- **비밀·PII**: 로그에 `cts.request`/`cts.ai`가 쌓이므로 운영에서는 로그 마스킹·보존 기간 정책을 별도로 두는 것이 좋음.

### 관측 (요약)

- 모든 `/api/*` 요청: 미들웨어가 **지속 시간·상태 코드**를 `cts.request`에 기록, 응답 헤더 **`X-Request-ID`**.
- 주요 LLM 구간: `track_llm_request` / `record_stream_usage`로 `cts.ai`에 **operation명·소요 ms·토큰 수·성공 여부** 기록. `record_llm_usage`가 **`LlmUsageRecord` DB**에 적재하며, UI **Token Dashboard**·`GET /api/usage-stats/`에서 누적 조회 (`langchain-community` OpenAI 콜백). 표시 시각은 **UTC+9(KST)**.
- **LangSmith**: `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` 설정 시 LangChain/LangGraph 트레이스(외부 SaaS).

### 프롬프트 버전

- 자연어 시스템/유저 프롬프트 텍스트는 `api/prompts/` 모듈에 모음. 변경 시 `api/prompts/__init__.py`의 **`PROMPTS_REVISION`** 주석을 갱신하면 운영·감사 추적에 유리.

---

## 13. 요약: “테크풀” 체크리스트

- **MCP**: 표준 프로토콜로 도구 노출, stdio/Streamable HTTP 이중 전송.
- **RAG**: ChromaDB + Azure Embeddings + Django 모델 기반 ingest + retrieve-then-generate.
- **구조화 출력**: Pydantic + `with_structured_output`.
- **응답 캐시**: 동일 쿼리 TTL 캐시.
- **ReAct 에이전트**: LangGraph `create_react_agent` + 로컬/외부 MCP 도구 통합, 도구 선택 규칙으로 GetClass/GetTable vs get_dependency_edges 구분.
- **외부 MCP 클라이언트**: Streamable HTTP **+ SSE 폴백**, 커스텀 `httpx`(TLS verify), async↔sync 브릿지, 원격 도구를 LangChain StructuredTool로 동적 래핑.
- **에이전트 답변 후처리**: TR dedupe·선행 JSON(`results`) 제거 — 백엔드/프론트 동기화.
- **ADT MCP HTTP 브릿지**: stdio 전용 Node 서버에 Streamable HTTP 진입점 추가, 요청별 Stateless 서버/트랜스포트.
- **LangGraph 배포 심의**: StateGraph, 조건부 라우팅, 멀티 전문가 노드, NDJSON 스트리밍.
- **Dependency Map**: LLM 기반 노드/링크 필터로 노이즈 제거.

위 구성을 통해 **MCP, RAG, ReAct, 외부 MCP 연동, 구조화 출력, 캐시, 그래프 기반 워크플로, LLM 기반 데이터 정제**까지 한 프로젝트에서 통합 활용하고 있으며, **동기/비동기 경계**, **프로토콜 전송 방식 차이(stdio vs HTTP)**, **도구 선택 편향** 등 실무 난제를 코드와 프롬프트 설계로 해결하고 있다.
