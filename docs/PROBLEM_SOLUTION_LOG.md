# 문제·해결 이력 및 마이그레이션 메모

초기 프로토타입을 **별도 환경**에서 진행한 뒤, 저장소를 **Cursor + 로컬 풀스택(Django/React)**으로 옮기며 겪은 이슈와, 실제 적용한 해결책을 정리합니다.  

---

## 1. 컨텍스트: 프로젝트 이전 시 흔한 리스크

| 리스크 | 왜 생기는지 (추정) | 이 레포에서의 완화 |
|--------|-------------------|-------------------|
| **환경 변수 불일치** | 채팅 세션별로 `.env` 조각만 제안되면 `SAP_*` / `AZURE_*` / `EXTERNAL_SAP_MCP_*`가 누락되기 쉬움 | `backend/.env.example` + `api/config.py` 단일 진입 |
| **프론트·백엔드 이중 진실** | 한쪽만 수정되면 스트림 파싱·필드명 불일치 | `docs/API_CONTRACT.md` 계약, 에이전트 답변 후처리는 **Python + JS 동기화** (`agent_reply_cleanup.py` ↔ `agentReplyCleanup.js`) |
| **React 훅/상태 누락** | 스트리밍 UI 추가 시 `useState` 선언 누락 | 린트·수동 테스트; 아래 **§4.1 프론트엔드** 참고 |
| **비동기 MCP vs 동기 Django** | LLM이 “그냥 await 하면 된다” 식 코드 생성 | `mcp_client._run_async` + 스레드 풀 브릿지 |
| **도구 출력을 그대로 노출** | 모델이 tool result JSON을 답에 붙임 | 후처리 스트립 + 시스템 프롬프트 규칙 |

---

## 2. 문제 → 해결 요약표

| # | 증상 / 문제 | 원인 (요약) | 해결 (스택·파일) |
|---|-------------|-------------|------------------|
| 1 | SAP Assistant 로딩 줄 **스크롤바**·레이아웃 깨짐 | 스트리밍/긴 메시지 영역 overflow | React/CSS 조정 (`App.jsx` 등 UI 컴포넌트) |
| 2 | 에이전트 응답이 **한 번에만** 보임 | 비스트림만 사용 또는 스트림 미연동 | `POST /api/agent/` `stream: true` + `fetch` ReadableStream, `frontend/src/api/agentStream.js` |
| 3 | 스트리밍 중 **도구 로그·중간 텍스트**가 화면에 노출 | `onDelta`로 토큰 단위 표시 | 최종 본문만 표시(스피너 등), 완료 후 `cleanAgentReplyText` 적용 |
| 4 | **`agentStreamPreview is not defined`** | 스트리밍 프리뷰 상태 추가 시 `useState` 누락 | `App.jsx`에 `useState` 보강 |
| 5 | **TR 목록이 두 번** (불릿 + 마크다운 헤딩) | 모델이 도구 결과와 요약을 중복 출력 | `api/agent_reply_cleanup.py` + `utils/agentReplyCleanup.js` TR 블록 dedupe |
| 6 | Token 대시보드 **재시작 시 초기화** | 메모리만 집계 | **`LlmUsageRecord`** 모델 + `record_llm_usage` / `usage_metrics.py`, 마이그레이션 |
| 7 | 표시 시각 **타임존 혼선** | 서버 UTC 그대로 표시 | UI·API에서 **UTC+9(KST)** 명시 (`usage-stats` 등) |
| 8 | 문서성 질문에 **내부 RAG**가 끼어듦 | `search_rag`와 SAP Docs 역할 충돌 | `api/prompts/agent.py` + `views/agent.py`: 공개 문서 냄새 시 retrieve 스킵, MCP 우선 규칙 |
| 9 | MCP 실패 로그가 **`TaskGroup`만** 보임 | Python 3.11+ `ExceptionGroup` 래핑 | `mcp_client._exception_leaves` / `_log_mcp_failure`로 leaf 예외 로깅 |
| 10 | 일부 MCP 서버는 **SSE만** 지원 | Streamable HTTP만 시도 시 실패 | **`streamable_http_client` 실패 후 `sse_client` 재시도** (`tools/list`, `call_tool`) |
| 11 | **`CERTIFICATE_VERIFY_FAILED`** (기업 프록시) | 자체서명 체인 | 공유 `httpx.AsyncClient` + **`EXTERNAL_SAP_MCP_VERIFY_SSL=false`** (비권장·개발용), `api/config.mcp_http_verify_ssl` |
| 12 | `127.0.0.1:8021` **connection failed** | ADT MCP를 stdio만 켬 또는 미기동 | ADT MCP를 **HTTP(Streamable HTTP)** 로 기동, `EXTERNAL_SAP_MCP_ADT_URL` — [`EXTERNAL_SAP_MCP.md`](./EXTERNAL_SAP_MCP.md) |
| 13 | URL은 있는데 **`docs_tools=0`** | SSL/방화벽/캐시 | 로그 확인, `.env` 수정 후 **Django 재시작** (프로세스 내 `_remote_tools_cache`) |
| 14 | 답변 앞에 **`{"results":[...]}`** 원시 JSON | Docs MCP `search` 결과를 모델이 그대로 붙임 | `strip_leading_search_results_json_blob` (백엔드·프론트) + 프롬프트 “JSON 금지” |
| 15 | `.env`에 URL 있는데 에이전트가 MCP를 **못 쓴다고** 함 | tools/list 실패와 프롬프트 상태 불일치 | `build_agent_system_prompt(..., docs_url_set_no_tools=...)` 로 사용자 안내 문구 분기 |
| 16 | Docker로 띄울 때 **프론트·API URL**이 헷갈림 | Vite dev(5173)와 Compose(8080) 혼동 | **`web` nginx + 상대 `/api`**, `VITE_API_BASE_URL` 비움; [`DOCKER.md`](./DOCKER.md) |
| 17 | 코드 리뷰·배포 리포트가 **재시작 후 사라짐** | 메모리만 사용, 저장소 없음 | **`CodeReviewRecord`**, **`DeployReportRecord`** + 조회 API `code-review-history/`, `deploy-report-history/`; 본문 **`persist: false`**로 저장 생략 가능 |

---

## 3. 스택별로 묶어 본 해결 패턴

### 3.1 백엔드 (Django + LangGraph + MCP SDK)

- **ReAct**: LangGraph `create_react_agent`, 도구 목록 동적 구성 (`api/views/agent.py`).
- **외부 MCP**: Python **`mcp`** 패키지 — `streamable_http_client` + **`sse_client`**, 커스텀 **`httpx.AsyncClient`(verify)** (`api/mcp_client.py`).
- **동기/비동기**: `_run_async` / `ThreadPoolExecutor` + `asyncio.run`.
- **관측**: `cts.request`, `cts.ai` 로거, `X-Request-ID`, (선택) LangSmith.

### 3.2 프론트엔드 (Vite + React)

- **에이전트 스트림**: `fetch` + `TextDecoder`, 본문 끝 `\x1e` + JSON 메타 분리 (`agentStream.js`).
- **답변 정리**: 스트림 완료 후 `cleanAgentReplyText` — TR dedupe + **JSON blob 제거** (`agentReplyCleanup.js`).

### 3.3 데이터·운영

- **토큰 사용량 영속화**: Django 모델 + SQLite(개발) / 이후 Postgres 권장.
- **문서**: [`API_CONTRACT.md`](./API_CONTRACT.md), [`LLM_BUDGETS.md`](./LLM_BUDGETS.md), [`DOCKER.md`](./DOCKER.md), [`EXTERNAL_SAP_MCP.md`](./EXTERNAL_SAP_MCP.md), [`AI_TECH.md`](./AI_TECH.md) — 색인은 [`README.md`](./README.md).

---

## 4. 상세 메모 (파일 맵)

### 4.1 프론트엔드

| 파일 | 역할 |
|------|------|
| `frontend/src/App.jsx` | SAP Assistant 탭, `streamAgentChat`, (과거) 스트림 프리뷰 상태 |
| `frontend/src/api/agentStream.js` | 스트림 파싱, 최종 `cleanAgentReplyText` |
| `frontend/src/utils/agentReplyCleanup.js` | TR dedupe, **SAP Docs search JSON** 선행 제거 |
| `frontend/src/components/AgentTab.jsx` | 단계 표시: `tool_call` 위주, `tool_result` 과다 노출 완화 |

### 4.2 백엔드

| 파일 | 역할 |
|------|------|
| `api/views/agent.py` | `_make_tools`, 스트림/JSON 응답, `clean_agent_reply_text` |
| `api/mcp_client.py` | tools/list·call_tool, SSE 폴백, SSL verify, 예외 펼치기 |
| `api/config.py` | `mcp_*`, `mcp_http_verify_ssl`, MCP URL 헬퍼 |
| `api/prompts/agent.py` | Docs/ADT/RAG 규칙, JSON·노이즈 금지 |
| `api/agent_reply_cleanup.py` | TR dedupe, list_transports 레거시 힌트 제거, **results JSON** 스트립 |
| `api/usage_metrics.py`, `api/models.py` | `LlmUsageRecord` 집계 |
| `api/models.py` | `CodeReviewRecord`, `DeployReportRecord` (리포트 영속) |
| `api/persist_ai_reports.py` | 저장 헬퍼, `should_persist` |
| `api/views/ai_report_history.py` | `code-review-history/`, `deploy-report-history/` |

### 4.3 Docker

| 파일 | 역할 |
|------|------|
| `docker-compose.yml` | `web`(nginx+정적), `api`(Django), 볼륨 `api_sqlite` |
| `frontend/Dockerfile` | `vite build` → nginx Alpine |
| `frontend/nginx/default.conf` | SPA + `/api` 리버스 프록시 |
| `backend/docker-entrypoint.sh` | `migrate` 후 `runserver` |
| `backend/core/settings.py` | `SQLITE_PATH`로 Docker용 DB 경로 |

### 4.4 테스트

- `api/tests/test_agent_reply_cleanup.py` — 후처리 회귀 방지.

---

## 5. 운영 체크리스트 (빠른 점검)

1. **Django** 기동, **프론트** `npm run dev`, `.env` 최소 Azure OpenAI + SAP HTTP.
2. 외부 MCP 사용 시: `EXTERNAL_SAP_MCP_*` 설정 후 **서버 재시작**.
3. SSL 오류 시: 조직 CA 설치 우선, 불가 시에만 `EXTERNAL_SAP_MCP_VERIFY_SSL=false`.
4. ADT MCP: **HTTP 모드**로 띄운 뒤에만 `EXTERNAL_SAP_MCP_ADT_URL` 사용.
5. 로그에서 `agent.react tools:` 한 줄로 `docs_tools` / `adt_tools` 개수 확인.
6. **Docker**: UI는 `http://localhost:8080`, API 직접 노출은 compose에서 선택.

---

## 6. 관련 문서

| 문서 | 내용 |
|------|------|
| [README.md](../README.md) | 빠른 시작 |
| [README.md (문서 색인)](./README.md) | `docs/` 내 모든 MD 링크 |
| [DOCKER.md](./DOCKER.md) | Compose 풀스택·볼륨 |
| [API_CONTRACT.md](./API_CONTRACT.md) | `/api/agent/` 스트림 계약 |
| [LLM_BUDGETS.md](./LLM_BUDGETS.md) | 토큰·recursion 등 |
| [AI_TECH.md](./AI_TECH.md) | AI 스택·한계 |
| [EXTERNAL_SAP_MCP.md](./EXTERNAL_SAP_MCP.md) | MCP URL·SSL·8021 |

---

*마지막 정리: 본 문서는 이슈 트래킹용이며, 새 증상이 나오면 표 2에 행을 추가하고 구현 파일 링크를 맞춰 두면 이후 작업자가 동일한 함정을 줄일 수 있습니다.*
