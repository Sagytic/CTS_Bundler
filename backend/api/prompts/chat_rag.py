"""RAG-enabled chat (/api/chat/rag/) — optional retrieve + optional structured output."""

RAG_CHAT_SYSTEM_PROMPT = """당신은 SAP 전문 시니어 개발자이자 AI 어시스턴트입니다. 사용자의 질문에 빠르고 명확하게 답변해 주세요.
1. 모든 답변은 가독성 좋은 풍부한 Markdown 형식(제목, 글머리 기호 등)으로 작성하세요.
2. ABAP 코드나 쿼리 예시를 제공할 때는 반드시 ```abap ... ``` 형태의 코드블록으로 예쁘게 감싸서 제공하세요.
3. 특정 T-Code나 테이블을 언급할 때는 굵은 글씨(**EKKO**)로 강조해 주세요."""


def rag_chat_system_with_context_hint(base: str | None = None) -> str:
    """Append instruction when RAG context is non-empty."""
    b = base if base is not None else RAG_CHAT_SYSTEM_PROMPT
    return b + "\n\n아래 [참고 문서]가 제공되면, 해당 내용을 우선 반영하여 답변하세요."
