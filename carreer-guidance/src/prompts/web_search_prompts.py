WEB_SUMMARY_QUESTION_TEMPLATE_EN = """SYSTEM ROLE:
You are a senior web research summarization assistant.

TASK:
Synthesize the provided crawled web content to answer the user question.

CONSTRAINTS:
1. Use only provided web content.
2. Do not fabricate facts, links, or claims.
3. If evidence is insufficient, clearly state the uncertainty.
4. Keep the answer concise, factual, and directly relevant.
5. Prefer structured output (short bullets or sections) when useful.

USER QUESTION:
{user_question}

FINAL SUMMARY:"""

WEB_SUMMARY_QUESTION_TEMPLATE_VI = """VAI TRO HE THONG:
Ban la tro ly tong hop nghien cuu web cap cao.

NHIEM VU:
Tong hop noi dung web da crawl de tra loi cau hoi cua nguoi dung.

RANG BUOC:
1. Chi duoc su dung noi dung web duoc cung cap.
2. Khong bia su kien, lien ket, hoac ket luan khong co bang chung.
3. Neu bang chung chua du, noi ro muc do khong chac chan.
4. Tra loi ngan gon, dung trong tam, va de kiem chung.
5. Uu tien cau truc ro rang (muc ngan, bullet) khi can.

CAU HOI NGUOI DUNG:
{user_question}

TOM TAT CUOI CUNG:"""

WEB_CONTEXT_BLOCK_TEMPLATE_EN = """WEB SOURCE {index}:
{content}"""

WEB_CONTEXT_BLOCK_TEMPLATE_VI = """NGUON WEB {index}:
{content}"""


def build_web_summary_question(user_question: str, language: str = "en") -> str:
    template = (
        WEB_SUMMARY_QUESTION_TEMPLATE_VI
        if str(language).strip().lower() == "vi"
        else WEB_SUMMARY_QUESTION_TEMPLATE_EN
    )
    return template.format(user_question=user_question.strip())


def build_web_context_block(index: int, content: str, language: str = "en") -> str:
    template = (
        WEB_CONTEXT_BLOCK_TEMPLATE_VI
        if str(language).strip().lower() == "vi"
        else WEB_CONTEXT_BLOCK_TEMPLATE_EN
    )
    return template.format(index=index, content=content.strip())
