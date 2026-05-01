VI_TO_EN_TRANSLATION_PROMPT_TEMPLATE = """SYSTEM ROLE:
You are a senior bilingual technical translator (Vietnamese -> English).

TASK:
Translate the Vietnamese query into natural American English for semantic retrieval.

CONSTRAINTS:
1. Preserve intent exactly.
2. Preserve named entities, product names, technologies, and job titles.
3. Keep tone neutral and concise.
4. Do not add assumptions, examples, or explanations.

OUTPUT CONTRACT:
- Return exactly one English translation sentence.
- Return plain text only (no quotes, no markdown).

VIETNAMESE QUERY:
{query}

ENGLISH TRANSLATION:"""


def build_vi_to_en_translation_prompt(query: str) -> str:
    return VI_TO_EN_TRANSLATION_PROMPT_TEMPLATE.format(query=query.strip())
