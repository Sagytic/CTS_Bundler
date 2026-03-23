# CTS Bundler

SAP CTS·종속성·티켓·RAG·ReAct 에이전트·배포 심의 워크플로를 한 프로젝트에서 다루는 풀스택 앱입니다.

**이 파일(`README.md`)은 저장소 최상단에 두고**, 빠른 시작·개요만 적습니다. **상세 문서**(API 계약, Docker, AI/MCP 스택, 트러블슈팅, 사용 순서 등)는 모두 **`docs/`** 아래에 있습니다. 목차: **[`docs/README.md`](docs/README.md)**.

## 빠른 시작 (로컬)

### 1. 백엔드 (Django)

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
source venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
cp .env.example .env         # 값 채우기 (최소 Azure OpenAI, SAP HTTP)
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

- API: `http://localhost:8000/api/`
- **Token Dashboard**: 사이드바 **Token Dashboard** 또는 `GET /api/usage-stats/` (SQLite 등 **DB에 누적**, 서버 재시작 후에도 유지. `langchain-community`로 토큰 수 집계).
- 관측: 요청마다 `X-Request-ID` 헤더. 콘솔 로그 `cts.request`(HTTP), `cts.ai`(LLM 구간·토큰 수).
- **LangSmith(선택)**: `.env`에 `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` 설정 시 LangChain/LangGraph 호출이 추적됩니다.

### 2. 프론트엔드 (Vite + React)

```bash
cd frontend
cp .env.example .env        # 선택; 로컬 dev는 보통 비워두면 Vite가 /api → 127.0.0.1:8000 프록시
npm install
npm run dev
```

기본 `http://localhost:5173` — API는 Vite 프록시로 백엔드에 전달됩니다.

### 3. RAG (선택)

1. 종속성/티켓 데이터 적재 후 `POST /api/rag/ingest/` (`source: db` 등).
2. `chat/rag` 또는 에이전트 `search_rag` 사용.

자세한 순서: [`docs/USAGE_STEPS.md`](docs/USAGE_STEPS.md)

## 문서

**전체 목록·링크**: [`docs/README.md`](docs/README.md)

| 문서 | 내용 |
|------|------|
| [`docs/QUICKSTART_E2E.md`](docs/QUICKSTART_E2E.md) | **E2E Quickstart**(10분, curl, 외부 의존 없을 때 동작) |
| [`docs/E2E_API_SPEC.md`](docs/E2E_API_SPEC.md) | API·스트리밍·오류 코드 1장 요약 |
| [`docs/DOCKER.md`](docs/DOCKER.md) | **Docker 풀스택**(웹+API), 볼륨·환경 변수 |
| [`docs/PROBLEM_SOLUTION_LOG.md`](docs/PROBLEM_SOLUTION_LOG.md) | **문제·해결 이력**, 마이그레이션 시 리스크, 파일 맵 |
| [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) | REST 경로·본문·스트리밍 `Accept` 주의 |
| [`docs/LLM_BUDGETS.md`](docs/LLM_BUDGETS.md) | 토큰·k·recursion·캐시 TTL 환경 변수 |
| [`docs/AI_TECH.md`](docs/AI_TECH.md) | AI 아키텍처·한계·알려진 이슈 |
| [`docs/MCP_README.md`](docs/MCP_README.md) | MCP 서버 실행 |
| [`docs/EXTERNAL_SAP_MCP.md`](docs/EXTERNAL_SAP_MCP.md) | 외부 SAP MCP URL·SSL·ADT HTTP |

## Docker (풀스택: UI + API)

레포 **루트**에서:

```bash
cp backend/.env.example backend/.env   # 최초 1회, 값 입력
docker compose up --build
```

- **앱(UI)**: http://localhost:8080 — 브라우저는 `/api/...` 만 사용 (nginx가 Django로 프록시).
- **데이터**: `api_sqlite` 볼륨에 SQLite·Chroma 유지 (`docker compose down -v` 시 삭제).
- API만 호스트에서 열어보려면 `docker-compose.yml`의 `api.ports` `8000:8000` 주석을 해제.

상세: **`docs/DOCKER.md`**. 로컬 핫 리로드 개발은 기존처럼 `npm run dev` + `runserver` 권장.

## CI

GitHub Actions: `.github/workflows/ci.yml` — 백엔드 `pytest`, 프론트 `lint` + `vitest run`.

## 테스트 로그 저장 (증빙용)

레포 루트에서 `.\scripts\capture-test-results.ps1` 실행 시 `docs/E2E_EVIDENCE/test-outputs/`에 pytest·vitest 전체 로그가 저장됩니다. 상세는 [`docs/E2E_EVIDENCE/TEST_CAPTURE.md`](docs/E2E_EVIDENCE/TEST_CAPTURE.md).

## 레포 구조 (요약)

```
backend/          Django + DRF, LangChain/LangGraph, RAG, MCP 진입
frontend/         React UI (Docker: Dockerfile + nginx/default.conf)
docs/             **기술·API 문서 전부** (`docs/README.md` 색인)
docker-compose.yml + web / api 서비스
mcp-abap-adt/     (별도) ADT MCP HTTP 브릿지 등
```
