# E2E API 스펙 요약 (1장)

Base URL: 로컬 Django `http://127.0.0.1:8000/api/` · Docker UI 경유 `http://localhost:8080/api/` · 전체·예외는 [`API_CONTRACT.md`](./API_CONTRACT.md).

---

## 1. 공통

| 항목 | 값 |
|------|-----|
| JSON POST | `Content-Type: application/json` |
| 요청 추적 | `X-Request-ID` (선택) — 응답에 에코, 로그 `cts.request`와 연결 |
| Accept (스트림) | `Accept: application/json, text/plain; q=0.9, */*; q=0.8` 권장 — DRF 협상 이슈 방지 |

---

## 2. 엔드포인트 목록 (대표)

| Method | Path | 용도 |
|--------|------|------|
| POST | `chat/` | 단일 LLM, 도구 없음 |
| POST | `chat/rag/` | RAG + 선택 구조화 출력 |
| POST | `agent/` | ReAct + MCP·로컬 도구, `stream` 선택 |
| POST | `analyze/` | 배포 심의 — **NDJSON** 스트림 |
| POST | `code-review/` | ABAP 리뷰 — `stream` 시 `text/plain` 청크 |
| GET | `sap-test/` | SAP HTTP 연결 시험 |
| POST | `transports/` | TR 목록 등 |
| GET/POST | `dependency/` | 종속성 그래프 |
| GET | `ticket-info/` | `trkorr` 필수 — 없으면 **400** |
| GET | `usage-stats/` | LLM 토큰 누적·대시보드 |
| POST | `rag/ingest/` | RAG 인제스트 |
| POST | `rag/query/` | RAG 쿼리 |

---

## 3. 스트리밍 규약

| API | 형식 |
|-----|------|
| `agent/` `stream: true` | `text/plain; charset=utf-8` — 텍스트 청크 후 `\x1e` + JSON(`steps`, `react_used_tools`, 선택 `error`) |
| `analyze/` | NDJSON — 이벤트당 1줄 JSON |
| `code-review/` `stream: true` | `text/plain` UTF-8 청크 |

---

## 4. 표준 오류 (요약)

| HTTP | 대표 상황 | 응답 바디 형태 |
|------|-----------|----------------|
| **400** | 필수 파라미터 누락(`message`, `trkorr` 등) | `{"error":"..."}` |
| **403** | 사용량 리셋 등 허용되지 않은 작업 | DRF `detail` 또는 `error` |
| **502** | SAP HTTP 실패(`sap-test` 등) | `{"message":"...","error":"..."}` |
| **503** | Azure OpenAI 미설정 | `{"error":"Azure OpenAI not configured"}` |
| **5xx** | 기타 서버·외부 연동 오류 | 엔드포인트별 `detail` / `error` — 내부 스택은 숨김, **`X-Request-ID`로 로그 대조** |

**참고**: 앱 레벨 **서킷 브레이커·글로벌 레이트리밋**은 미구현. SAP HTTP 타임아웃은 코드 상 초 단위 고정(`sap_client`: 전송 10s, 종속성 15s, 오브젝트 사용 60s). MCP는 SDK/네트워크 타임아웃에 따름.

---

## 5. 입력/출력 스키마

필드 상세는 [`API_CONTRACT.md`](./API_CONTRACT.md) 본문 표. 배포 심의 `pipeline` 객체(`research`, `graph`, `self_rag`, …)는 동 문서 `POST /api/analyze/` 절.
