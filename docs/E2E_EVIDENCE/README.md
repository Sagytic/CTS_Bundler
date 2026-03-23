# E2E 증빙 첨부 가이드 (선택)

과제·레포트에 **제3자 재현·KPI 증빙**을 붙일 때 아래를 채우면 됩니다. 파일명은 예시이며 PDF/PNG 모두 가능.

## pytest / vitest 실행 로그 (자동)

레포 루트에서:

```powershell
.\scripts\capture-test-results.ps1
```

`test-outputs/pytest-output.txt`(백엔드), `vitest-output.txt`(프론트)가 갱신됩니다. `pip install pytest-html`(또는 `backend/requirements-dev.txt`) 설치 시 `pytest-report.html`도 생성.

- 상세: [`TEST_CAPTURE.md`](./TEST_CAPTURE.md)
- Linux/macOS: `bash scripts/capture-test-results.sh`

## 권장 첨부 (2~3개)

1. **Quickstart 시나리오 A**: `POST /api/chat/` 성공 또는 503 응답 캡처 + 요청에 넣은 `X-Request-ID` + 서버 로그 한 줄.
2. **Quickstart 시나리오 B**: `GET /api/sap-test/` 200 또는 502 캡처 + `X-Request-ID` + 로그.
3. **(선택)** `usage-stats/` 화면 또는 JSON — 토큰 누적 증빙.

## 실패 시나리오 3종 (고정)

| # | 조건 | 기대 HTTP/메시지 | 증빙 |
|---|------|-------------------|------|
| (a) | SAP 타임아웃·연결 불가 | `sap-test` **502**, `error` 필드 | curl + 로그 |
| (b) | MCP URL 없음/연결 실패 | 에이전트에서 외부 도구 0건 또는 단계 내 오류 | `agent/` 응답 메타 + 로그 `TaskGroup` 등 |
| (c) | RAG 미 ingest | 검색 공백·빈 컨텍스트 | `rag/query` 또는 채팅 응답 + Chroma 경로 확인 |

상세 절차는 [`../QUICKSTART_E2E.md`](../QUICKSTART_E2E.md), [`../E2E_API_SPEC.md`](../E2E_API_SPEC.md).
