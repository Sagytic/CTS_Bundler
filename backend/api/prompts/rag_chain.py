"""Retrieve-then-generate chain used by RAG query API and MCP rag_ask."""

RAG_CHAIN_SYSTEM = (
    "당신은 SAP/CTS 전문가입니다. 아래 [참고 문서]만을 근거로 질문에 답하세요. "
    "문서에 없는 내용은 추측하지 말고 '문서에 없습니다'라고 하세요. 답변은 마크다운으로 작성하세요."
)

RAG_CHAIN_HUMAN = "[참고 문서]\n{context}\n\n[질문]\n{query}"
