# LLM / RAG 비용·지연 예산 (환경 변수)

기본값은 **비용과 응답 시간의 균형**을 기준으로 잡았습니다. 운영에서 토큰 비용이 크면 `max_tokens`·`k`·`recursion_limit`을 낮추고, 품질이 부족하면 반대로 조정하세요.

모든 getter는 `api/config.py`에 정의되어 있으며, 문서와 실제 코드가 어긋나지 않도록 변경 시 **이 파일과 `../backend/.env.example`** 을 함께 수정하는 것을 권장합니다.

| 환경 변수 | 기본값 | 용도 |
|-----------|--------|------|
| `LLM_CODE_REVIEW_MAX_TOKENS` | 2500 | 코드 리뷰 응답 상한 |
| `LLM_CODE_REVIEW_TEMPERATURE` | 0.1 | 코드 리뷰 샘플링 |
| `LLM_AGENT_TEMPERATURE` | 0 | ReAct 에이전트 (`/api/agent/`) |
| `LLM_AGENT_RECURSION_LIMIT` | 25 | LangGraph 도구 루프 최대 깊이(스텝). 초과 시 그래프 중단 |
| `LLM_SIMPLE_CHAT_TEMPERATURE` | 0.2 | 단순 챗 (`/api/chat/`) |
| `LLM_CHAT_RAG_TEMPERATURE` | 0.2 | RAG 챗 (`/api/chat/rag/`) |
| `LLM_RAG_CHAIN_TEMPERATURE` | 0.2 | retrieve→generate 체인 (`rag_chain_invoke`, MCP `rag_ask`) |
| `RAG_DEFAULT_K` | 5 | 기본 retrieve top-k (에이전트 `search_rag`, RAG 챗, 쿼리 기본값) |
| `RAG_QUERY_MAX_K` | 20 | `POST /api/rag/query/` 의 `k` 상한 |
| `MCP_RAG_QUERY_MAX_K` | 10 | MCP `search_rag` / `rag_ask` 의 k 상한 |
| `CHAT_RAG_CACHE_TTL_SEC` | 300 | `/api/chat/rag/` in-memory 캐시 TTL. **`0`이면 캐시 비활성** |
| `ANALYZE_GRAPH_RECURSION_LIMIT` | 22 | 배포 심의 LangGraph `recursion_limit` |
| `LLM_MAP_FILTER_MAX_TOKENS` | 2500 | Dependency Map 노이즈 필터 JSON 응답 |
| `LLM_MAP_FILTER_TEMPERATURE` | 0.1 | 위 필터 LLM |

## 캐시 무효화

- `/api/chat/rag/` 캐시는 **질문 문자열** 기준 in-memory TTL만 적용됩니다.
- RAG ingest 후에도 **캐시는 자동으로 비우지 않습니다.** 문서/인덱스를 바꾼 뒤에는 `CHAT_RAG_CACHE_TTL_SEC=0`으로 끄거나 서버 재시작·별도 캐시 클리어 전략을 쓰세요.

## RAG ingest 한도

- `RAG_INGEST_MAX_DOCS` (기본 3000): DB에서 Document로 올릴 최대 건수. 임베딩 비용·시간과 직결됩니다.
