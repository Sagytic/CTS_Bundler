# HTTP API 계약 (요약)

Base URL: 개발 시 프록시 기준 **`/api/`** (Vite → Django). **Docker 풀스택**(`docker compose`) 시 같은 방식으로 **`http://localhost:8080/api/`** (nginx → Django). 호스트에서 Django만 직접 호출 시 `http://localhost:8000/api/`.

공통:

- **Content-Type**: `application/json` (본문이 있는 POST).
- **Accept**: DRF 협상용. `application/json`을 포함하는 것을 권장. `code-review` 스트림은 응답이 `text/plain`이어도 요청 `Accept`에 `application/json`을 함께 넣지 않으면 **406**이 날 수 있음 (JSON renderer 협상).
- **X-Request-ID**: 선택.내면 응답에 동일 값이 에코되며, 로그(`cts.request`)와 연결됩니다. 없으면 서버가 UUID를 발급합니다.

---

## SAP / TR

| Method | Path | Body / Query | 응답 |
|--------|------|----------------|------|
| GET | `sap-test/` | — | SAP 연결 시험 |
| POST | `transports/` | `user_id` 등 (기존 스펙 유지) | TR 목록 |
| POST | `snapshot/update/` | — (또는 기존) | 스냅샷 갱신 |

---

## 채팅 / 에이전트

| Method | Path | Body | 응답 |
|--------|------|------|------|
| POST | `chat/` | `message` | `{ "reply": string }` |
| POST | `chat/rag/` | `message`, `use_rag`, `use_structured`, `use_cache` | 자유 텍스트 또는 구조화 필드. `use_structured: true` → `reply`, `intent`, `suggested_actions` |
| POST | `agent/` | `message`, `user_id` (선택), `include_steps`, **`stream`: true** (선택) | 비스트림: `{ "reply", "steps", "react_used_tools" }`. 스트림: **`text/plain; charset=utf-8`** 청크 후 **`\\x1e` + JSON** (`steps`, `react_used_tools`, 선택 `error`). 클라이언트 `Accept`는 code-review와 동일하게 `application/json`을 포함할 것. |

**답변 후처리 (계약 보조)**  
`reply` 텍스트는 서버·클라이언트 모두에서 동일 규칙으로 정리됩니다: TR 목록 중복 제거, 레거시 도구 안내 문구 제거, SAP Docs MCP `search`가 반환한 **`{"results":[...]}` JSON 덩어리**가 모델이 답 앞에 붙인 경우 제거 (`api/agent_reply_cleanup.py`, `frontend/src/utils/agentReplyCleanup.js`). 상세는 [`PROBLEM_SOLUTION_LOG.md`](./PROBLEM_SOLUTION_LOG.md).

**역할 구분**

- **`chat/`**: 단일 LLM, 도구 없음.
- **`chat/rag/`**: 선택적 RAG + 선택적 **Pydantic 구조화 출력**.
- **`agent/`**: LangGraph ReAct, 로컬·외부 MCP 도구.

---

## 분석 / 종속성 / 티켓

| Method | Path | 설명 |
|--------|------|------|
| POST | `analyze/` | 배포 심의 — NDJSON 스트림. 완료 후 **`DeployReportRecord`에 저장**(기본). **`persist: false`** 로 끔. |
| GET/POST | `dependency/` | 그래프 노드/링크 (링크 ≥5 시 LLM 필터 적용 가능) |
| GET | `dependency-edges/` | `?target_obj=&limit=` |
| GET | `ticket-info/` | **`trkorr` 필수** 쿼리. 선택 `objName`(SAP 소스 조회). 없으면 `400`. |
| POST | `ticket-mapping/` | TR ↔ 티켓 매핑 upsert (`trkorr` 필수) |
| POST | `adt-write/` | ADT 반영 |

---

## AI 코드 리뷰

| Method | Path | Body | 응답 |
|--------|------|------|------|
| POST | `code-review/` | `objName`, `abapCode`, `requirementSpec` (선택), **`stream`**, 선택 **`user_id`**, **`persist`** (기본 `true` → 응답 끝나면 SQLite 등 DB에 `CodeReviewRecord` 저장; `false`면 미저장) | 스트림: **`Content-Type: text/plain; charset=utf-8`**, UTF-8 청크. 비스트림: `{ "aiResult": string }` |

### 저장된 코드 리뷰·배포 리포트 조회

| Method | Path | 설명 |
|--------|------|------|
| GET | `code-review-history/?limit=20` | 최근 코드 리뷰 목록 (`preview`만, 최대 100건) |
| GET | `code-review-history/<id>/` | 단건 전체 (`ai_result`, `abap_code`, `requirement_spec`) |
| GET | `deploy-report-history/?limit=20` | 최근 배포 심의 리포트 목록 |
| GET | `deploy-report-history/<id>/` | 단건 전체 (`final_report`, `extra` 메타) |

Django Admin에서도 동일 모델 조회·삭제 가능.

**스트리밍 클라이언트 권장 헤더**

```http
Accept: application/json, text/plain; q=0.9, */*; q=0.8
```

`text/plain`만내면 DRF 기본 협상과 충돌할 수 있습니다 (서버는 `PlainTextRenderer`를 등록해 완화함).

---

## RAG

| Method | Path | Body | 응답 |
|--------|------|------|------|
| POST | `rag/ingest/` | `source`, `clear`, `texts`, `max_docs` … | `{ "ok", "ingested" }` |
| POST | `rag/query/` | `query`, `k` (≤ `RAG_QUERY_MAX_K`), `retrieve_only` | 문서 목록 또는 생성 `answer` |

---

## LLM 사용량 (대시보드)

| Method | Path | 설명 |
|--------|------|------|
| GET | `usage-stats/` | 누적 토큰·기능별 합계·최근 호출 목록 (**DB 영속**, `LlmUsageRecord`). 시각 필드 `ts_kst`·`server_started_at_iso` 등은 **UTC+9(KST)** 표기. |
| POST | `usage-stats/reset/` | DB 사용 기록 전체 삭제 — 기본 **403**. `DEBUG=True` 또는 `USAGE_STATS_ALLOW_RESET=true` 일 때만 허용. |

집계는 `langchain-community`의 OpenAI 콜백에 의존합니다. **청구·정식 사용량은 Azure Portal**을 따르세요.

---

## 오류 형태

- DRF: `{"detail": "..."}` 또는 `{"error": "..."}` (엔드포인트별 상이).
- 사용자에게 노출 시 **내부 스택은 숨기고**, 운영에서는 **`X-Request-ID`** 로 서버 로그와 대조하는 것을 권장.

자세한 AI 스택 설명은 [`AI_TECH.md`](./AI_TECH.md), MCP는 [`MCP_README.md`](./MCP_README.md) 참고.
