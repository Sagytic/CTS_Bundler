"""
Centralized LLM system/user prompt text.

Versioning: bump PROMPTS_REVISION when changing behavior-critical strings
so operators can grep git history by revision comment.

PROMPTS_REVISION: 2025-03-17 — initial extraction from views.
"""
from __future__ import annotations

PROMPTS_REVISION = "2025-03-17"

from api.prompts.agent import build_agent_system_prompt
from api.prompts.chat_rag import RAG_CHAT_SYSTEM_PROMPT, rag_chat_system_with_context_hint
from api.prompts.code_review import CODE_REVIEW_SYSTEM, build_code_review_prompt_template
from api.prompts.dependency_map import dependency_map_prompt_template
from api.prompts.rag_chain import RAG_CHAIN_SYSTEM, RAG_CHAIN_HUMAN
from api.prompts.simple_chat import SIMPLE_CHAT_SYSTEM_PROMPT

__all__ = [
    "PROMPTS_REVISION",
    "build_agent_system_prompt",
    "RAG_CHAT_SYSTEM_PROMPT",
    "rag_chat_system_with_context_hint",
    "CODE_REVIEW_SYSTEM",
    "build_code_review_prompt_template",
    "dependency_map_prompt_template",
    "RAG_CHAIN_SYSTEM",
    "RAG_CHAIN_HUMAN",
    "SIMPLE_CHAT_SYSTEM_PROMPT",
]
