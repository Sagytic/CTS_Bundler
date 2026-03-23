# E2E Quickstart (약 10분)

다른 사람이 **같은 절차로 서비스를 띄우고**, 최소 **2개 API**를 호출해 **응답 + 요청 ID 로그**까지 확인하기 위한 가이드입니다. 상세 계약은 [`E2E_API_SPEC.md`](./E2E_API_SPEC.md), [`API_CONTRACT.md`](./API_CONTRACT.md).

## 이름·경로 (철자)

| 구분 | 값 |
|------|-----|
| **제품 표기** | **CTS Bundler** |
| **이 레포를 클론한 폴더명** | **`CTS_Bundler`** (로컬 경로는 이 이름 그대로) |

제품 표기와 레포 폴더명은 모두 **`CTS_Bundler`**로 통일합니다.

---

## 1. 사전 요건

| 항목 | 버전 예시 | 비고 |
|------|-----------|------|
| Python | 3.11+ | `backend/` venv |
| Node.js | 20 LTS 권장 | `frontend/` |
| Docker | 선택 | 풀스택은 [`DOCKER.md`](./DOCKER.md) |
| curl | Windows 10+ 내장 `curl.exe` | 아래 예시는 **`curl.exe`** 권장(PowerShell에서 `curl`은 별칭일 수 있음) |

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

### 의존성 미설정 시(UI는 어디까지 되나)

별도 “더미 모드” 플래그는 없음.

- **백엔드 + 프론트만 뜬 상태**(Azure/SAP/MCP 미설정): **브라우저 UI는 로드·탭 이동·입력 폼 사용 가능**. 다만 **채팅·에이전트·배포 심의·코드 리뷰** 등 LLM 호출은 API가 **503** 등으로 실패하고, 화면에는 **에러 메시지/빈 응답**으로 보임. **SAP**이 없으면 TR 목록·`sap-test`·종속성 데이터 연동은 **502 또는 빈 데이터**. **RAG 미 ingest**면 검색·RAG 채팅은 **컨텍스트 없음**으로 동작.
- **정적·라우팅**: 랜딩·사이드바·티켓/맵 화면 **렌더링**은 가능(데이터 없으면 빈 표·안내).

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

- UI + API: **`http://localhost:8080`** — 브라우저는 `/api/...` 만 사용. 아래 `curl`에서 `BASE`를 `http://localhost:8080/api` 로 바꿀 것.

---

## 4. 복붙 실행 가능한 curl 예시

**전제**: 백엔드가 `127.0.0.1:8000`에서 실행 중. Windows PowerShell에서는 **`curl.exe`** 사용 권장.

### 시나리오 A — 단순 채팅 (JSON, 비스트림)

```powershell
curl.exe -sS -i -X POST "http://127.0.0.1:8000/api/chat/" ^
  -H "Content-Type: application/json" ^
  -H "X-Request-ID: e2e-demo-001" ^
  -d "{\"message\":\"hello\"}"
```

Linux / macOS / Git Bash:

```bash
curl -sS -i -X POST "http://127.0.0.1:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: e2e-demo-001" \
  -d '{"message":"hello"}'
```

**성공(200)**: `{"reply":"..."}`  
**Azure 미설정(503)**: `{"error":"Azure OpenAI not configured"}`

### 시나리오 B — SAP 연결 시험

```powershell
curl.exe -sS -i "http://127.0.0.1:8000/api/sap-test/" -H "X-Request-ID: e2e-demo-002"
```

```bash
curl -sS -i "http://127.0.0.1:8000/api/sap-test/" -H "X-Request-ID: e2e-demo-002"
```

**성공(200)**: `message`, `transports`  
**SAP 미연결/오류(502)**: `{"message":"SAP 연결 실패","error":"..."}`

### 시나리오 C — 에이전트 스트리밍 (`-N` = 버퍼 없이 출력)

```powershell
curl.exe -N -sS -i -X POST "http://127.0.0.1:8000/api/agent/" ^
  -H "Content-Type: application/json" ^
  -H "Accept: application/json, text/plain; q=0.9, */*; q=0.8" ^
  -H "X-Request-ID: e2e-stream-agent" ^
  -d "{\"message\":\"ping\",\"stream\":true}"
```

```bash
curl -N -sS -i -X POST "http://127.0.0.1:8000/api/agent/" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/plain; q=0.9, */*; q=0.8" \
  -H "X-Request-ID: e2e-stream-agent" \
  -d '{"message":"ping","stream":true}'
```

**참고**: Azure 미설정 시 503. 응답은 `text/plain` 청크 + `\x1e` + JSON 메타 — [`API_CONTRACT.md`](./API_CONTRACT.md).

### 시나리오 D — 배포 심의 NDJSON 스트림

```powershell
curl.exe -N -sS -i -X POST "http://127.0.0.1:8000/api/analyze/" ^
  -H "Content-Type: application/json" ^
  -H "Accept: application/json" ^
  -H "X-Request-ID: e2e-ndjson-001" ^
  -d "{\"message\":\"smoke\",\"user_id\":\"\",\"selected_trs\":[],\"persist\":false,\"include_pipeline_summary\":true}"
```

(Azure·SAP·데이터 전제에 따라 길이·성공 여부는 달라짐. 스모크용 최소 본문.)

**로그**: 서버 콘솔에서 `X-Request-ID` 값이 `cts.request` / `cts.ai` 와 대응.

---

## 5. 스트리밍·NDJSON (요약)

| API | 옵션 | curl |
|-----|------|------|
| 에이전트 | `stream: true` | **`-N`** + 위 시나리오 C |
| 배포 심의 | POST `/api/analyze/` | **`-N`** + 위 시나리오 D |

한 흐름 증빙: `curl -N` + `X-Request-ID` + 서버 로그 + (선택) 브라우저 네트워크 탭 → [`E2E_EVIDENCE/README.md`](./E2E_EVIDENCE/README.md).

---

## 6. 관련 문서

| 문서 | 용도 |
|------|------|
| [`E2E_API_SPEC.md`](./E2E_API_SPEC.md) | 엔드포인트·에러·스트리밍 1장 요약 |
| [`API_CONTRACT.md`](./API_CONTRACT.md) | 전체 계약 |
| [`DOCKER.md`](./DOCKER.md) | Compose·볼륨·호스트 MCP URL |
| [`LLM_BUDGETS.md`](./LLM_BUDGETS.md) | 토큰·캐시 TTL |
| [`E2E_EVIDENCE/test-outputs/`](./E2E_EVIDENCE/test-outputs/) | pytest/vitest 로그 재생성 |
