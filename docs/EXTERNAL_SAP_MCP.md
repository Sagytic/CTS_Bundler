# 외부 SAP MCP 검토 및 제안

CTS Bundler는 **자체 MCP 서버**(TR 목록, 종속성, 티켓, RAG)를 제공하고, 필요 시 **다른 SAP 관련 MCP**를 호출할 수 있도록 `.env`에 URL을 설정해 둘 수 있습니다.

> **참고**: ReAct 에이전트에서 외부 MCP를 호출하는 방식, async/sync 브릿지, ADT MCP HTTP 브릿지 등 기술적 난이도·해결 과제는 **[`AI_TECH.md`](./AI_TECH.md)** 에 정리되어 있습니다.  
> **문제·해결 이력**(SSL 폴백, SSE 재시도, `docs_tools=0` 등)은 **[`PROBLEM_SOLUTION_LOG.md`](./PROBLEM_SOLUTION_LOG.md)** 를 참고하세요.

---

## 1. 사용자 제안 세 개 검토

### 1) SAP Docs MCP (marianfoo)

| 항목 | 내용 |
|------|------|
| **역할** | ABAP/SAP 공식·커뮤니티 문서 시맨틱 검색 (40,761개 파일) |
| **포함** | ABAP Keyword Docs (7.52~최신), Clean ABAP, RAP 패턴, CDS 치트시트 등 |
| **공개 URL** | ABAP 전용: `https://mcp-abap.marianzeis.de/mcp` / SAP 전체: `http://mcp-sap-docs.marianzeis.de/mcp` |
| **설치** | 불필요 (공개 엔드포인트) |

**CTS Bundler와의 적합성**

- TR/종속성/티켓은 우리 MCP로 처리하고, **ABAP 문법·RAP·Clean ABAP·CDS** 같은 **문서성 질문**은 SAP Docs MCP에 맡기기 좋음.
- 채팅에서 “이 ABAP 키워드 뭐야?”, “RAP에서 lock은 어떻게 해?”, “Clean ABAP 네이밍 규칙” 등을 답할 때 **바로 활용 가능**.
- `.env`에 `EXTERNAL_SAP_MCP_DOCS_ABAP_URL` / `EXTERNAL_SAP_MCP_DOCS_FULL_URL` 설정 후, 에이전트가 필요 시 이 MCP 도구를 호출하도록 연동.

---

### 2) ABAP ADT MCP (mario-andreschak 등) — **실시간 SAP 시스템과 연동할 때 적합**

| 항목 | 내용 |
|------|------|
| **역할** | ABAP Development Tools로 **실시간** SAP 시스템 접속 (프로그램/클래스/테이블/구조 등 조회) |
| **도구 예** | GetProgram, GetClass, GetFunction, GetTable, GetStructure, SearchObject 등 12가지 |
| **필요** | SAP 접속 정보 (이미 `.env`에 `SAP_ADT_*` 있음) |
| **전송** | 보통 stdio (Cursor가 프로세스 실행). HTTP로 쓰려면 서버를 **직접 HTTP 모드로 띄워야** 함. |

**CTS Bundler와의 적합성**

- TR에 포함된 **오브젝트 소스/메타**를 바로 보고 싶을 때, 또는 **종속성 분석 보조**로 유용.
- 다만 이 MCP는 **로컬/서버에서 프로세스로 실행**하는 형태가 일반적이고, **공개 HTTP 엔드포인트가 없음**.  
  → 우리 Django에서 호출하려면:
  - ADT MCP를 **직접 설치 후** `--transport streamable-http --port 8021` 등으로 띄우고,
  - `.env`에 `EXTERNAL_SAP_MCP_ADT_URL=http://127.0.0.1:8021/mcp` 처럼 설정하는 방식이 필요.
- **추천**: 실시간 SAP 오브젝트 조회가 꼭 필요할 때만 도입. 그때는 위처럼 자체 HTTP 인스턴스를 띄우고 URL만 설정하면 됨.

---

### 3) CAP MCP (@cap-js/mcp-server) — **CAP 프로젝트 개발 시에만**

| 항목 | 내용 |
|------|------|
| **역할** | SAP Cloud Application Programming Model (CAP) — CDS 엔티티/서비스 검색, CAP 문서 시맨틱 검색 |
| **도구** | search_model, search_docs 등 |
| **용도** | BTP/CAP 기반 앱 개발, CDS·CAP API 질문 |

**CTS Bundler와의 적합성**

- CTS Bundler는 TR/종속성/티켓/ABAP 중심이라 **CAP 전용 MCP와 직접 겹치는 영역은 적음**.
- 팀에서 **CAP 프로젝트도 같이 다룰 때** 보조 문서/모델 검색용으로 쓸 수 있음.
- **추천**: CAP 개발을 함께 할 때만 선택적으로 `.env`에 CAP MCP URL 추가 (CAP MCP를 HTTP로 띄운 경우).

---

## 2. 추가로 찾은 SAP 관련 MCP (참고)

| MCP | 제공처 | 용도 | CTS Bundler와 연관 |
|-----|--------|------|--------------------|
| **SAP Fiori Elements MCP** | SAP (@sap-ux/fiori-mcp-server) | Fiori Elements 앱 생성/수정 | UI 개발 시 참고용 |
| **UI5 MCP** | SAP (@ui5/mcp-server) | UI5 코딩 규칙, deprecated 체크 | UI 개발 시 참고용 |
| **SAP MDK MCP** | SAP (@sap/mdk-mcp-server) | Mobile Development Kit | 모바일 앱 개발 시 |
| **abap-mcp-server** | marianfoo | ABAP/RAP 검색, 린트 등 | SAP Docs와 역할 일부 겹침 |
| **fr0ster/mcp-abap-adt** | 커뮤니티 | ADT + HTTP/SSE 지원, CRUD | 우리가 ADT 연동 시 대안 |
| **ABAP Accelerator (Amazon Q)** | AWS | S/4HANA ABAP 생성/테스트 | 별도 구축 필요 |

---

## 3. CTS Bundler 기준 제안 요약

1. **SAP Docs MCP**  
   - 공개 URL만 넣으면 되고, ABAP/RAP/Clean ABAP/CDS 문서 질문에 바로 활용 가능.  
   - `.env`: `EXTERNAL_SAP_MCP_DOCS_ABAP_URL`, `EXTERNAL_SAP_MCP_DOCS_FULL_URL` (이미 예시 추가됨).

2. **실시간 SAP 오브젝트가 필요할 때**: **ABAP ADT MCP**  
   - 직접 HTTP로 띄운 뒤 `EXTERNAL_SAP_MCP_ADT_URL` 만 설정하면 됨.  
   - ADT MCP를 HTTP로 띄우는 방법은 각 프로젝트(mario-andreschak, fr0ster 등) 문서 참고.

3. **CAP 개발을 함께 할 때만**: **CAP MCP**  
   - 선택 사항. CAP MCP를 HTTP로 서빙하는 경우 `EXTERNAL_SAP_MCP_CAP_URL` 에 넣어 두면 됨.

---

## 4. .env 설정 요약

이미 `backend/.env`에 아래가 반영되어 있습니다.

```env
# SAP Docs MCP (공개)
EXTERNAL_SAP_MCP_DOCS_ABAP_URL=https://mcp-abap.marianzeis.de/mcp
EXTERNAL_SAP_MCP_DOCS_FULL_URL=http://mcp-sap-docs.marianzeis.de/mcp

# ABAP ADT / CAP 은 필요 시 주석 해제 후 URL 입력
# EXTERNAL_SAP_MCP_ADT_URL=http://127.0.0.1:8021/mcp
# EXTERNAL_SAP_MCP_CAP_URL=

# (선택) HTTPS MCP TLS 검증 끄기 — 기업 프록시 등으로 CERTIFICATE_VERIFY_FAILED 날 때만
# EXTERNAL_SAP_MCP_VERIFY_SSL=false
```

URL을 비우거나 주석 처리하면 해당 외부 MCP는 사용하지 않습니다.  

### MCP 연결 실패 시 (`docs_tools=0`, 로그에 `TaskGroup`)

- 로그 **`detail=`** 뒤에 펼쳐지는 실제 예외(예: `ConnectError`, `ReadTimeout`, SSL, `404`)를 확인하세요. 예전에는 `TaskGroup` 한 줄만 보였는데, 이제 **중첩 원인**이 같이 찍힙니다.
- **`SSL: CERTIFICATE_VERIFY_FAILED` / self-signed certificate**: 조직 프록시가 HTTPS를 가로채는 경우가 많습니다. 가능하면 **조직 CA를 OS/파이썬 신뢰 저장소에 설치**하세요. 임시로만 `EXTERNAL_SAP_MCP_VERIFY_SSL=false` 를 켜면 MCP용 `httpx` 연결에서 검증을 끕니다(보안 위험, 개발·신뢰망 전용).
- 클라이언트는 먼저 **Streamable HTTP**로 `tools/list`를 시도하고, 실패하면 **SSE**(`mcp.client.sse`)로 한 번 더 시도합니다. 서버가 둘 중 하나만 지원하는 경우가 많습니다.
- `127.0.0.1:8021` ADT MCP는 해당 포트에서 **HTTP MCP가 실제로 떠 있는지** 확인하세요(stdio 전용 프로세스면 Django에서 붙을 수 없음).
- `.env`만 바꾸고 **Django를 재시작**하지 않으면, 이전에 실패했을 때의 빈 도구 캐시가 남을 수 있습니다.

---

## 5. ReAct 에이전트 연동 (구현됨)

- **SAP Docs MCP**: `.env`에 `EXTERNAL_SAP_MCP_DOCS_ABAP_URL` 또는 `EXTERNAL_SAP_MCP_DOCS_FULL_URL`이 있으면, 에이전트가 해당 서버의 도구(검색 등)를 자동으로 사용합니다.
- **ABAP ADT MCP**: `EXTERNAL_SAP_MCP_ADT_URL`이 있으면, **GetClass, GetTable**만 기본 사용합니다.  
  `EXTERNAL_SAP_MCP_ADT_TOOLS=GetClass,GetTable` 로 명시할 수 있고, 다른 도구를 쓰려면 여기에 추가하면 됩니다.  
  (이미 report/프로그램 조회는 프로젝트에 있으므로, Class·Table만 ADT MCP로 보강하는 구성을 권장합니다.)

ADT MCP를 우리 프로젝트에서 쓰려면, 해당 MCP를 **HTTP(Streamable HTTP)로 띄워야** 합니다.  
예: 해당 프로젝트에서 `--transport streamable-http --port 8021` 지원 시, 서버를 실행한 뒤 `.env`에  
`EXTERNAL_SAP_MCP_ADT_URL=http://127.0.0.1:8021/mcp` 를 넣으면 됩니다.

---

## 6. ADT MCP 띄우는 과정

여기서는 **mario-andreschak/mcp-abap-adt** 기준으로 설치·실행 방법을 정리합니다.  
(Cursor에서만 쓸 때는 “6.1 Cursor에서 쓰기”만 하면 되고, **Django 에이전트에서 쓰려면** “6.2 HTTP로 띄워서 CTS Bundler와 연동”을 참고하세요.)

### 6.1 사전 준비

- **Node.js LTS** 설치 후 터미널에서 `node -v`, `npm -v` 확인.
- **SAP 시스템 정보**: URL, 사용자, 비밀번호, 클라이언트 번호.  
  ADT 서비스(`/sap/bc/adt`)가 해당 시스템에서 활성화되어 있어야 합니다.

### 6.2 설치 및 빌드

1. **저장소 클론**
   ```bash
   git clone https://github.com/mario-andreschak/mcp-abap-adt
   cd mcp-abap-adt
   ```

2. **의존성 설치 및 빌드**
   ```bash
   npm install
   npm run build
   ```

3. **`.env` 파일 생성**  
   프로젝트 **루트**(mcp-abap-adt 폴더)에 `.env` 파일을 만들고 SAP 접속 정보를 넣습니다.
   ```env
   SAP_URL=https://your-sap-system.com:8000
   SAP_USERNAME=your_username
   SAP_PASSWORD=your_password
   SAP_CLIENT=100
   ```
   - 비밀번호에 `#`가 있으면 값을 따옴표로 감싸세요.
   - CTS Bundler의 `.env`에 이미 있는 `SAP_ADT_HOST`, `SAP_ADT_USER` 등을 여기 **SAP_URL**, **SAP_USERNAME** 등에 맞게 넣으면 됩니다.

### 6.3 실행 방법

#### A) Cursor에서만 쓰기 (stdio)

- **ADT MCP 프로세스를 직접 띄울 필요는 없습니다.**  
  Cursor 설정에서 MCP 서버로 등록해 두면, Cursor가 필요할 때 `node dist/index.js`를 실행합니다.

- **Cursor MCP 설정 예시**
  - **Command**: `node`
  - **Args**: `C:/경로/mcp-abap-adt/dist/index.js` (본인 PC의 **절대 경로**)
  - **Cwd**: `C:/경로/mcp-abap-adt` (선택 사항, 권장)

- 이렇게 하면 Cursor 채팅에서 GetProgram, GetClass, GetTable 등 ADT 도구를 사용할 수 있습니다.

#### B) Django(CTS Bundler) 에이전트에서 쓰기 (HTTP 필요)

- 우리 ReAct 에이전트는 **HTTP(Streamable HTTP)** 로만 외부 MCP를 호출합니다.
- **mario-andreschak/mcp-abap-adt**는 기본이 **stdio**라서, 이 프로젝트만으로는 “HTTP 서버”로 띄우는 옵션이 문서에 없을 수 있습니다.
- **CTS_Bundelr 내 mcp-abap-adt**에는 Streamable HTTP 진입점이 포함되어 있습니다.  
  **1) HTTP로 ADT MCP 실행** (포트 기본 8021):
  ```bash
  cd mcp-abap-adt
  npm run build
  npm run start:http
  ```
  포트 변경: `MCP_HTTP_PORT=8022 npm run start:http`  
  **2)** `backend/.env`에 다음을 설정합니다.
  ```env
  EXTERNAL_SAP_MCP_ADT_URL=http://127.0.0.1:8021/mcp
  EXTERNAL_SAP_MCP_ADT_TOOLS=GetClass,GetTable
  ```
  **3)** 다른 터미널에서: `cd backend` → `python manage.py test_adt_mcp`
- **fr0ster/mcp-abap-adt** 등 다른 HTTP 지원 포크를 쓰는 경우, 해당 문서대로 서버를 띄운 뒤 위와 같이 URL만 설정하면 됩니다.

### 6.4 제공 도구 (mario-andreschak/mcp-abap-adt)

| 도구 | 설명 |
|------|------|
| GetProgram | ABAP 프로그램 소스 |
| **GetClass** | ABAP 클래스 소스 (CTS Bundler에서 Class 보강용으로 추천) |
| **GetTable** | ABAP 테이블 구조 (CTS Bundler에서 Table 보강용으로 추천) |
| GetFunction, GetFunctionGroup | 함수 모듈/함수 그룹 |
| GetStructure, GetInclude, GetInterface | 구조/인클루드/인터페이스 |
| GetTableContents, GetPackage, GetTypeInfo, GetTransaction, SearchObject | 기타 |

CTS Bundler는 이미 report(프로그램) 조회가 있으므로, **GetClass, GetTable**만 외부 ADT MCP로 쓰려면 `.env`에  
`EXTERNAL_SAP_MCP_ADT_TOOLS=GetClass,GetTable` 로 두면 됩니다.

### 6.5 CTS Bundler 기준 .env와 테스트

- **mcp-abap-adt용 .env**  
  `backend/mcp-abap-adt.env.example` 에 **신 세팅 [SAP_Edu]** 기준으로 변수명을 매핑해 두었습니다.  
  이 내용을 **mcp-abap-adt 클론 폴더 루트**에 `.env` 로 복사해 두면 됩니다.
  - `SAP_ADT_HOST` → `SAP_URL`
  - `SAP_ADT_USER` → `SAP_USERNAME`
  - `SAP_ADT_PASSWORD` → `SAP_PASSWORD`
  - `SAP_ADT_CLIENT` → `SAP_CLIENT`

- **Django에서 ADT MCP 연동 테스트**  
  ADT MCP를 **HTTP로 띄운 뒤** `backend/.env`에 `EXTERNAL_SAP_MCP_ADT_URL`을 설정하고, backend 폴더에서:
  ```bash
  python manage.py test_adt_mcp
  ```
  - 도구 목록 조회 후, **GetClass**(기본: SAPMV45A), **GetTable**(기본: MARA)를 한 번씩 호출해 봅니다.
  - 다른 클래스/테이블로 테스트: `python manage.py test_adt_mcp --class=ZCL_MY_CLASS --table=MARA`
  - URL이 비어 있으면 안내 메시지만 출력됩니다.
