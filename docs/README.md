# CTS Bundler 문서 색인

모든 프로젝트 문서는 이 `docs/` 폴더에 모아 두었습니다. (저장소 루트 `README.md`는 빠른 시작만 유지합니다.)

| 문서 | 설명 |
|------|------|
| [QUICKSTART_E2E.md](./QUICKSTART_E2E.md) | **E2E 10분 실행** — env, 로컬/Docker, curl 2종, 외부 없을 때 동작 |
| [E2E_API_SPEC.md](./E2E_API_SPEC.md) | **E2E용 API 1장 요약** — 엔드포인트·스트리밍·표준 오류 |
| [E2E_EVIDENCE/README.md](./E2E_EVIDENCE/README.md) | KPI·실패 시나리오 **증빙 첨부** 체크리스트 |
| [E2E_EVIDENCE/TEST_CAPTURE.md](./E2E_EVIDENCE/TEST_CAPTURE.md) | **pytest/vitest 로그·스크린샷** (`scripts/capture-test-results.ps1`) |
| [API_CONTRACT.md](./API_CONTRACT.md) | REST·스트리밍 API 계약 |
| [LLM_BUDGETS.md](./LLM_BUDGETS.md) | LLM/RAG 환경 변수·예산 |
| [DOCKER.md](./DOCKER.md) | Docker 풀스택(UI+API) |
| [PROBLEM_SOLUTION_LOG.md](./PROBLEM_SOLUTION_LOG.md) | 문제·해결 이력·온보딩 |
| [AI_TECH.md](./AI_TECH.md) | AI 스택·아키텍처·한계 · **§7 배포 심의 RAG 1~4단계 로드맵(예시 포함)** |
| [MCP_README.md](./MCP_README.md) | 내장 MCP 서버 실행·Cursor |
| [EXTERNAL_SAP_MCP.md](./EXTERNAL_SAP_MCP.md) | 외부 SAP Docs/ADT MCP URL |
| [USAGE_STEPS.md](./USAGE_STEPS.md) | RAG → 채팅 → 에이전트 순서 |
| [OBJECT_USAGE_DESIGN.md](./OBJECT_USAGE_DESIGN.md) | TR 오브젝트 사용처 설계 |
| [mcp-abap-adt/](./mcp-abap-adt/) | vendored ADT MCP 원문 README·CHANGELOG |

로컬 설정 파일은 여전히 **`backend/.env`** / **`backend/.env.example`** 입니다.
