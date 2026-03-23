# 사용 순서 (1~4단계)

아래는 **RAG 인덱싱 → RAG/채팅 테스트 → ReAct 에이전트 테스트 → MCP 연동** 순서로 수행하는 방법입니다.

---

## 사전 준비

- Django 서버 실행: 터미널에서 `cd backend` 후 `python manage.py runserver`
- API 베이스 URL: **http://localhost:8000/api/** (포트가 다르면 해당 URL로 치환)

요청은 **Postman**, **Thunder Client**(VS Code), **curl** 등 아무 도구로 보내도 됩니다. 모두 **POST**이며 JSON body를 사용합니다.

---

## 1단계: RAG 인덱싱 (한 번만 수행)

**목적**: DB에 있는 종속성(DependencySnapshot), 티켓 매핑(TicketMapping)을 벡터 DB(ChromaDB)에 넣어, 이후 RAG 검색/챗봇에서 사용할 수 있게 합니다.

**어디서**: Django가 떠 있는 상태에서, **API 클라이언트**로 다음 요청을 보냅니다.

**어떻게**:

- **URL**: `http://localhost:8000/api/rag/ingest/`
- **메서드**: **POST**
- **Headers**: `Content-Type: application/json`
- **Body (JSON)**:
  - DB 기준으로 인덱싱(기본): `{}` 또는 `{ "source": "db" }`
  - 기존 벡터를 비우고 다시 넣을 때: `{ "clear": true, "source": "db" }`
  - 직접 텍스트만 넣을 때: `{ "source": "texts", "texts": ["문단1", "문단2"] }`

**예시 (curl)**:

```bash
curl -X POST http://localhost:8000/api/rag/ingest/ \
  -H "Content-Type: application/json" \
  -d "{}"
```

**성공 시 응답 예**: `{ "ok": true, "ingested": 1234 }`  
→ 이제 RAG 검색/챗봇(RAG)/에이전트의 `search_rag` 도구가 이 데이터를 사용합니다.

---

## 2단계: RAG가 적용된 채팅 테스트

**목적**: RAG로 검색한 문서를 컨텍스트로 넣은 채팅이 동작하는지 확인합니다.

**어디서**: 같은 API 클라이언트로 **채팅 RAG 엔드포인트**에 요청합니다.

**어떻게**:

- **URL**: `http://localhost:8000/api/chat/rag/`
- **메서드**: **POST**
- **Headers**: `Content-Type: application/json`
- **Body (JSON)**:
  - 필수: `"message"` (질문 내용)
  - 선택: `"use_rag": true` (RAG 사용, 기본 false), `"use_structured": false`, `"use_cache": true`

**예시 (curl)**:

```bash
curl -X POST http://localhost:8000/api/chat/rag/ \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"ZMMR0030이 뭘 호출해?\", \"use_rag\": true}"
```

**성공 시 응답 예**: `{ "reply": "… (마크다운 답변) …", "cached": false }`  
→ 1단계에서 인덱싱한 종속성/티켓 정보가 있으면, 그걸 참고한 답변이 나옵니다.

---

## 3단계: ReAct 에이전트 테스트 (도구 호출 확인)

**목적**: ReAct 에이전트가 **실제로 도구를 호출**하는지 확인합니다.  
에이전트는 **질문 → (필요 시) 도구 호출 → 결과 반영 → 다시 답변**을 반복(ReAct 루프)합니다.  
응답의 `steps`와 `react_used_tools`로 그 동작을 볼 수 있습니다.

**어디서**: 같은 API 클라이언트로 **에이전트 엔드포인트**에 요청합니다.

**어떻게**:

- **URL**: `http://localhost:8000/api/agent/`
- **메서드**: **POST**
- **Headers**: `Content-Type: application/json`
- **Body (JSON)**:
  - 필수: `"message"` (예: "11355 사번 TR 목록 알려줘", "ZMMR0030 종속성 알려줘")
  - 선택: `"include_steps": true` (기본 true, ReAct 단계 포함)

**예시 (curl)**:

```bash
curl -X POST http://localhost:8000/api/agent/ \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"11355 사번 TR 목록 알려줘\", \"include_steps\": true}"
```

**성공 시 응답 예**:

```json
{
  "reply": "11355 사번의 TR 목록은 다음과 같습니다. …",
  "steps": [
    { "type": "tool_call", "tool": "list_transports", "args": { "user_id": "11355" } },
    { "type": "tool_result", "content_preview": "- EDAK900101: …" },
    …
  ],
  "react_used_tools": 1
}
```

- **`steps`**: ReAct 루프에서 일어난 **도구 호출(tool_call)**과 **도구 결과(tool_result)**.  
  이게 비어 있지 않고 `tool_call`이 있으면, “단순 try/except”가 아니라 **실제 ReAct(도구 사용)**가 동작한 것입니다.
- **`react_used_tools`**: 호출된 도구 횟수. 0이면 이번 질문에서는 도구를 쓰지 않고 답한 것입니다.

**도구가 안 나오는 경우**:  
질문을 “11355 TR 목록 알려줘”, “ZMMR0030이 뭘 호출해?”처럼 **도구가 필요한 형태**로 바꿔 보세요.  
그래도 `steps`에 `tool_call`이 없으면, LLM이 도구를 쓰지 않고 답한 것이므로 다른 질문으로 한 번 더 시도해 보면 됩니다.

---

## 4단계: Cursor에서 MCP 연동

**목적**: Cursor 채팅에서 CTS Bundler 데이터(TR, 종속성, 티켓, RAG)를 **MCP 도구**로 쓰게 합니다.

**어디서**:  
1) 터미널에서 MCP 서버를 실행하고,  
2) Cursor 설정에서 MCP 서버를 등록합니다.

**어떻게**:

1. **MCP 서버 실행**
   - 터미널에서: `cd backend` (Django backend 폴더로 이동)
   - 실행: `python -m api.mcp_server`
   - 이 프로세스는 **계속 켜 두어야** Cursor가 연결할 수 있습니다.

2. **Cursor에 MCP 추가**
   - Cursor → 설정(Settings) → MCP → Add new MCP server
   - **Command**: `python`
   - **Args**: `-m`, `api.mcp_server`
   - **Cwd**: `backend` 폴더의 **절대 경로** (예: `C:\Users\11355\Desktop\Side_project\CTS_Bundler\backend`)
   - 저장 후 Cursor 채팅에서 해당 MCP 서버를 선택하면, `list_transports`, `get_dependency_edges`, `get_ticket_mapping`, `search_rag`, `rag_ask` 도구를 사용할 수 있습니다.

자세한 설정은 **[`MCP_README.md`](./MCP_README.md)** 를 참고하면 됩니다.

---

## 요약 표

| 단계 | 목적           | URL (POST)                    | Body 예시 |
|------|----------------|-------------------------------|-----------|
| 1    | RAG 인덱싱     | http://localhost:8000/api/rag/ingest/  | `{}` |
| 2    | RAG 채팅 테스트 | http://localhost:8000/api/chat/rag/    | `{"message":"…", "use_rag":true}` |
| 3    | ReAct 에이전트 | http://localhost:8000/api/agent/      | `{"message":"11355 TR 목록 알려줘", "include_steps":true}` |
| 4    | MCP 연동       | (Cursor 설정 + `python -m api.mcp_server`) | - |

---

**ReAct가 “진짜” 적용됐는지 확인하는 방법**:  
3단계에서 `POST /api/agent/` 응답의 **`steps`**에 `type: "tool_call"` 항목이 있고, **`react_used_tools`**가 1 이상이면, 해당 요청에서는 ReAct(도구 호출 루프)가 수행된 것입니다.

- **프론트엔드 채팅**: Agent 탭에서 입력 후 전송하면 `POST /api/agent/` 로 전달되며, ReAct 에이전트가 TR/종속성/RAG/외부 MCP(문서·ADT) 도구를 자동 선택해 답변합니다.
- **AI 기술 스택 상세**(ReAct, 외부 MCP 연동, 난이도·해결 과제): [`AI_TECH.md`](./AI_TECH.md)
