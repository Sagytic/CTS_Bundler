# E2E Quickstart (약 10분)

다른 사람이 **같은 절차로 서비스를 띄우고**, 최소 **2개 API**를 호출해 **응답 + 요청 ID 로그**까지 확인하기 위한 가이드입니다. 상세 계약은 [`E2E_API_SPEC.md`](./E2E_API_SPEC.md), [`API_CONTRACT.md`](./API_CONTRACT.md).

---

## 1. 사전 요건

| 항목 | 버전 예시 | 비고 |
|------|-----------|------|
| Python | 3.11+ | `backend/` venv |
| Node.js | 20 LTS 권장 | `frontend/` |
| Docker | 선택 | 풀스택은 [`DOCKER.md`](./DOCKER.md) |

---

## 2. 환경 변수 (`backend/.env`)

```bash
cd backend
cp .env.example .env
```

- **필수(LLM 동작)**: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, 배포명 등 — 없으면 `POST /api/chat/` 등 LLM 경로는 **503** + `{"error":"Azure OpenAI not configured"}`.
- **선택(SAP CTS HTTP)**: `SAP_HTTP_URL`, `SAP_USER`, `SAP_PASSWD`, `SAP_CLIENT` — 없으면 `GET /api/sap-test/` 등 SAP 호출은 **502** 또는 `sap_client` 오류 메시지.
- **선택(외부 MCP)**: `EXTERNAL_SAP_MCP_DOCS_ABAP_URL` 등 — 비우면 에이전트의 해당 도구만 비활성(로그에 tools=0 등). [`EXTERNAL_SAP_MCP.md`](./EXTERNAL_SAP_MCP.md).
- **RAG**: Chroma 경로·ingest 없으면 검색 결과 공백 가능 — [`USAGE_STEPS.md`](./USAGE_STEPS.md).

**“더미 모드”**: 별도 플래그 없음. Azure 미설정 시 LLM API는 503으로 **실패가 명시적**이고, SAP 미설정 시 TR/종속성 도구는 오류 JSON. 로컬 UI는 뜨지만 AI·SAP 기능은 위 조건에 종속.

---

## 3. 실행 방법 (택 1)

### A) 로컬 — 백엔드 + 프론트 (개발 권장)

```bash
# 터미널 1
cd backend && python -m venv venv
# Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000

# 터미널 2
cd frontend && npm install && npm run dev
```

- API Base: `http://127.0.0.1:8000/api/`
- UI: `http://localhost:5173` (Vite가 `/api` → 8000 프록시)

### B) Docker 풀스택

레포 **루트**에서:

```bash
cp backend/.env.example backend/.env   # 값 입력 후
docker compose up --build
```

- UI + API: **`http://localhost:8080`** — 브라우저는 `/api/...` 만 사용.

---

## 4. 대표 시나리오 2개 (curl → 응답 → 로그)

`BASE`를 로컬 Django 기준 `http://127.0.0.1:8000/api` 또는 Docker `http://localhost:8080/api` 로 맞출 것.

### 시나리오 A — 단순 채팅 (JSON)

```http
POST /api/chat/
Content-Type: application/json
X-Request-ID: e2e-demo-001

{"message":"안녕"}
```

**성공(200)**: `{"reply":"..."}`  
**Azure 미설정(503)**: `{"error":"Azure OpenAI not configured"}`

**로그**: 서버 콘솔에서 `X-Request-ID: e2e-demo-001` 또는 자동 발급 UUID가 `cts.request` / `cts.ai` 로그와 대응.

### 시나리오 B — SAP 연결 시험

```http
GET /api/sap-test/
X-Request-ID: e2e-demo-002
```

**성공(200)**: `message`, `transports`  
**SAP 미연결/오류(502)**: `{"message":"SAP 연결 실패","error":"..."}`

---

## 5. 스트리밍·NDJSON (참고)

- **에이전트** `POST /api/agent/` `stream: true`: `text/plain`, 청크 + `\x1e` + JSON 메타 — [`API_CONTRACT.md`](./API_CONTRACT.md) §채팅/에이전트.
- **배포 심의** `POST /api/analyze/`: **NDJSON** 스트림 — 줄마다 JSON 이벤트.

한 흐름으로 끝까지 남기려면: curl `-N` + `X-Request-ID` + 서버 로그 캡처 + (선택) 브라우저 네트워크 탭 스크린샷 → [`E2E_EVIDENCE/README.md`](./E2E_EVIDENCE/README.md) 체크리스트.

---

## 6. 관련 문서

| 문서 | 용도 |
|------|------|
| [`E2E_API_SPEC.md`](./E2E_API_SPEC.md) | 엔드포인트·에러·스트리밍 1장 요약 |
| [`API_CONTRACT.md`](./API_CONTRACT.md) | 전체 계약 |
| [`DOCKER.md`](./DOCKER.md) | Compose·볼륨·호스트 MCP URL |
| [`LLM_BUDGETS.md`](./LLM_BUDGETS.md) | 토큰·캐시 TTL |
