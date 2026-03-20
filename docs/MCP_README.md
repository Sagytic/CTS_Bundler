# MCP 서버: Cursor 연동 + 외부 연동

CTS Bundler MCP 서버는 **두 가지 방식**으로 사용할 수 있습니다.

| 방식 | 용도 | 실행 방법 |
|------|------|-----------|
| **stdio** | Cursor IDE 전용 (Cursor가 프로세스 실행) | Cursor 설정에 등록만 하면 됨 |
| **HTTP (streamable-http / sse)** | 외부 클라이언트 연동 (웹, 다른 앱, 다른 PC) | 터미널에서 서버를 띄움 |

---

## 1. 의존성

```bash
cd backend
pip install "mcp[cli]"   # 또는 pip install -r requirements.txt
```

---

## 2. Cursor 전용 (stdio)

- Cursor 설정 → MCP → Add new MCP server 후 **Command**: `python`, **Args**: `-m`, `api.mcp_server`, **Cwd**: `backend` 절대 경로.
- Cursor가 필요할 때 스스로 프로세스를 띄우므로 **사용자가 터미널에서 따로 켤 필요 없음**.
- 제공 도구: `list_transports`, `get_dependency_edges`, `get_ticket_mapping`, `search_rag`, `rag_ask`.
- **`list_transports`**: 웹 CTS Analyzer와 같이 **메인 TR만** 반환합니다 (`TRFUNCTION`이 K=Workbench 요청, W=Customizing 요청인 행). 태스크·하위 TR은 제외됩니다.

### TR 설명(AS4TEXT) 한글이 SAP GUI와 다를 때

MCP/백엔드는 SAP HTTP API가 내려주는 JSON을 **그대로** UTF-8로 파싱합니다. 이름이 `장지빈`인데 `장지맥`처럼 보이면:

1. **SAP에 저장된 텍스트 자체**가 다르거나(오타·다른 필드), ABAP에서 JSON으로 넣을 때 **시스템 코드페이지** 처리 오류일 수 있습니다. SE01/해당 TR에서 설명을 SAP GUI로 직접 확인해 보세요.
2. Django·Python 쪽에서 임의로 글자를 바꾸지는 않습니다. 수정은 **SAP CTS HTTP 서비스(ABAP)** 쪽 UTF-8 출력·유니코드 변환이 필요합니다.

---

## 3. 외부 연동 (HTTP) – 다른 클라이언트가 MCP로 접속

Cursor 말고 **다른 앱·웹·다른 PC**에서 MCP 프로토콜로 접속하려면, MCP 서버를 **HTTP 모드**로 띄워야 합니다.

### 3.1 실행 (로컬만)

```bash
cd backend
python -m api.mcp_server --transport streamable-http --port 8020
```

- 접속 URL: **`http://127.0.0.1:8020/mcp`**
- 같은 PC 위의 MCP 클라이언트(Claude Desktop, 커스텀 앱 등)가 이 주소로 연결하면 됨.

### 3.2 실행 (같은 네트워크·외부에서 접속 허용)

```bash
cd backend
python -m api.mcp_server --transport streamable-http --host 0.0.0.0 --port 8020
```

- **`--host 0.0.0.0`**: 다른 기기에서 이 PC의 IP로 접속 가능.
- 접속 URL 예: `http://<이 PC의 IP>:8020/mcp` (예: `http://192.168.0.10:8020/mcp`).
- 방화벽에서 8020 포트 허용이 필요할 수 있음.

### 3.3 SSE 전송 (선택)

일부 클라이언트는 SSE 방식을 쓰는 경우가 있음:

```bash
python -m api.mcp_server --transport sse --host 0.0.0.0 --port 8020 --path /mcp
```

### 3.4 외부 클라이언트에서 연결 시

- **Streamable HTTP** 클라이언트: 서버 URL을 `http://<host>:8020/mcp` 로 설정.
- 프로토콜은 [MCP Streamable HTTP](https://spec.modelcontextprotocol.io/specification/2024-11-05/transports/#streamable-http) 스펙을 따름.  
  (Claude Desktop, MCP 클라이언트 라이브러리 등에서 “MCP server URL”에 위 URL 입력.)

---

## 4. Django와의 관계

- MCP 서버는 시작 시 Django 설정을 로드합니다 (`DJANGO_SETTINGS_MODULE=core.settings`).
- **반드시 `backend` 디렉터리에서** 실행해야 하며, `.env` 및 DB(예: db.sqlite3)에 접근할 수 있어야 합니다.
- HTTP 모드는 **Django와 별도 프로세스**입니다. Django(runserver)는 보통 8000, MCP HTTP는 8020 포트로 동시에 띄우면 됩니다.

---

## 5. 요약

| 목적 | 할 일 |
|------|--------|
| Cursor에서만 MCP 쓰기 | Cursor 설정에 MCP 서버 등록 (stdio, 별도 실행 없음) |
| 외부에서 MCP로 연동 | `python -m api.mcp_server --transport streamable-http [--host 0.0.0.0] --port 8020` 로 서버 실행 후, 클라이언트가 `http://<host>:8020/mcp` 로 접속 |

---

## 6. 참고

- **AI 기술 스택 전반**(MCP, RAG, ReAct 에이전트, 외부 MCP 클라이언트 등): [`AI_TECH.md`](./AI_TECH.md)
- **외부 SAP Docs/ADT MCP URL·SSL·포트 8021**: [`EXTERNAL_SAP_MCP.md`](./EXTERNAL_SAP_MCP.md)
- **문제·해결 이력**(에이전트·MCP 연동 트러블슈팅): [`PROBLEM_SOLUTION_LOG.md`](./PROBLEM_SOLUTION_LOG.md)
- **Docker**: [`DOCKER.md`](./DOCKER.md) (호스트 ADT MCP `127.0.0.1` 은 컨테이너에서 별도 고려)
