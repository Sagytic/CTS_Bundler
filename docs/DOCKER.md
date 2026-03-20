# Docker — 풀스택 (웹 UI + Django API)

한 번에 **React 빌드 + nginx**와 **Django**를 띄웁니다. 브라우저는 **`http://localhost:8080`** 만 열면 되고, API는 같은 출처의 **`/api/...`** 로 호출됩니다 (nginx → `api:8000`).

## 사전 준비

1. `cp backend/.env.example backend/.env` 후 Azure OpenAI·SAP 등 필수 값 입력.
2. (선택) 호스트에서 API만 디버그할 때 `docker-compose.yml`의 `api.ports` `8000:8000` 주석 해제.

## 실행

```bash
# 레포 루트에서
docker compose up --build
```

- **UI**: http://localhost:8080  
- **마이그레이션**: 컨테이너 기동 시 `docker-entrypoint.sh`가 `migrate` 실행.
- **SQLite / Chroma**: 이름은 `api_sqlite`인 Docker 볼륨에 저장 (`/app/data/db.sqlite3`, `/app/data/chroma`). `docker compose down`만 하면 데이터 유지, **`down -v`는 볼륨 삭제**.

## 구조

| 서비스 | 이미지 빌드 | 역할 |
|--------|-------------|------|
| `web` | `frontend/Dockerfile` | Node로 `vite build` → nginx로 `dist` 서빙, `/api` 리버스 프록시 |
| `api` | `backend/Dockerfile` | Django `runserver` (스모크/개발용). 프로덕션은 gunicorn 등으로 교체 권장 |

프론트 빌드 시 **`VITE_API_BASE_URL`을 비워** 두어, 런타임에 상대 경로 `/api`만 쓰도록 합니다 (`frontend/src/api/client.js`).

## 환경 변수 (Compose가 API에 넣는 값)

`backend/.env`와 병합되며, 아래는 **compose가 덮어쓰는** 대표 값입니다.

| 변수 | 값 | 설명 |
|------|-----|------|
| `SQLITE_PATH` | `/app/data/db.sqlite3` | DB 파일 위치 (볼륨 영속) |
| `CHROMA_PERSIST_DIR` | `/app/data/chroma` | RAG Chroma 디렉터리 |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,api,[::1]` | 브라우저가 보내는 Host / 내부 DNS |

로컬에서만 `python manage.py runserver` 할 때는 이 변수들을 `.env`에 넣지 않아도 됩니다 (`settings.py` 기본값).

## CORS

브라우저 → **같은 호스트:8080** 의 `/api` 이므로 **동일 출처**이고, 별도 CORS 설정 없이 동작합니다.

## 알려진 한계

- **`runserver`**: 단일 워커, 프로덕션 부적합. 배포 시 **gunicorn/uvicorn** + 정적 파일 분리 권장 (`backend/Dockerfile` CMD 교체).
- **MCP / 호스트 `127.0.0.1`**: Django 컨테이너 안의 `127.0.0.1`은 컨테이너 자신입니다. **호스트 PC**에서 띄운 ADT MCP(예: 8021)를 쓰려면 `.env`를 예를 들어 `EXTERNAL_SAP_MCP_ADT_URL=http://host.docker.internal:8021/mcp` 로 두는 방식을 검토하세요(Docker Desktop에서 `host.docker.internal` 지원). Linux는 `network_mode: host` 등 다른 패턴이 필요할 수 있습니다. 자세한 설명: [`EXTERNAL_SAP_MCP.md`](./EXTERNAL_SAP_MCP.md).

## 관련 파일

- `docker-compose.yml` — 서비스 정의
- `frontend/Dockerfile`, `frontend/nginx/default.conf`
- `backend/Dockerfile`, `backend/docker-entrypoint.sh`
- 문제 해결 이력: [`PROBLEM_SOLUTION_LOG.md`](./PROBLEM_SOLUTION_LOG.md)
