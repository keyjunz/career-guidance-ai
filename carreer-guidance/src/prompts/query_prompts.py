"""Prompts for query decomposition (multi-intent)."""

from __future__ import annotations

MAX_SUB_QUERIES = 4


def build_query_decomposition_prompt(question: str) -> str:
    return f"""You split a user question into separate independent sub-questions when appropriate.

RULES:
1. If the user asks only ONE thing, return needs_decomposition=false and exactly ONE sub_query.
2. If there are MULTIPLE distinct questions, set needs_decomposition=true and return 2–{MAX_SUB_QUERIES} sub_queries in the SAME order as in the user text.
3. suggested_tool must be one of: "rag", "web", "both"
   - "rag": internal academic documents, curricula, courses, career guidance PDFs.
   - "web": fresh public data (salaries by year, company news, market trends).
   - "both": truly needs internal docs AND up-to-date web (rare).
4. section_title: short heading in the SAME language as the sub_query.
5. intent_type: short English label e.g. salary, curriculum, comparison, skills, general.

OUTPUT — STRICT JSON only, no markdown fences:
{{
  "needs_decomposition": true,
  "sub_queries": [
    {{
      "intent_id": "intent_1",
      "query": "clear standalone question text",
      "intent_type": "salary",
      "confidence": 0.9,
      "suggested_tool": "web",
      "section_title": "short heading"
    }}
  ]
}}

User question:
{question.strip()}
"""
