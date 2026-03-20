"""AI code review prompts (/api/code-review/)."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

CODE_REVIEW_SYSTEM = (
    "You are an SAP ABAP Clean Code Expert. Respond in Korean. Use rich Markdown format."
)


def _tasks_block(has_requirement_spec: bool) -> str:
    if has_requirement_spec:
        return """[수행할 작업]
                1. **현업 요구사항 대비 로직 검증**: 아래 [현업 요구사항 명세]의 각 요구사항이 이 코드에서 논리적으로 충족되는지 검증해줘. 충족 여부를 요구사항별로 짧게 서술하고, 누락·불일치·모호한 부분이 있으면 구체적으로 지적해줘.
                2. 로직 검증: 잠재적인 버그나 성능 저하 요소를 지적해줘.
                3. Clean ABAP 리뷰: 구식 문법을 지적해줘.
                4. 리팩토링 코드: ABAP 7.4+ 문법으로 리팩토링된 코드를 제시해줘.
                5. 공식 문서 근거: 왜 이렇게 고쳐야 하는지 반드시 클릭 가능한 마크다운 링크를 제공해줘.
                [중요] 링크 텍스트 끝에는 반드시 '(새 창 링크)'라는 문구를 넣어 사용자가 클릭할 수 있음을 명확히 인지하게 해줘.
                예시: [SAP Clean ABAP Styleguide (새 창 링크)](https://github.com/SAP/styleguides/blob/main/clean-abap/CleanABAP.md)"""
    return """[수행할 작업]
                1. 로직 검증: 잠재적인 버그나 성능 저하 요소를 지적해줘.
                2. Clean ABAP 리뷰: 구식 문법을 지적해줘.
                3. 리팩토링 코드: ABAP 7.4+ 문법으로 리팩토링된 코드를 제시해줘.
                4. 공식 문서 근거: 왜 이렇게 고쳐야 하는지 반드시 클릭 가능한 마크다운 링크를 제공해줘.
                [중요] 링크 텍스트 끝에는 반드시 '(새 창 링크)'라는 문구를 넣어 사용자가 클릭할 수 있음을 명확히 인지하게 해줘.
                예시: [SAP Clean ABAP Styleguide (새 창 링크)](https://github.com/SAP/styleguides/blob/main/clean-abap/CleanABAP.md)"""


def build_code_review_user_template(has_requirement_spec: bool) -> str:
    """Variables: obj_name, abap_code, requirement_spec (may be empty)."""
    user_content = """
                아래 ABAP 소스코드를 리뷰해줘.

                [오브젝트]: {obj_name}
                [현재 소스코드]:
                {abap_code}
                """
    if has_requirement_spec:
        user_content += """

                [현업 요구사항 명세]
                {requirement_spec}
                """
    user_content += "\n\n" + _tasks_block(has_requirement_spec)
    return user_content


def build_code_review_prompt_template(has_requirement_spec: bool) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", CODE_REVIEW_SYSTEM),
            ("user", build_code_review_user_template(has_requirement_spec)),
        ]
    )
