from __future__ import annotations
import os
from openai import OpenAI

def answer_with_context(question: str, context_blocks: list[str]) -> str:
    """
    Uses OpenAI Responses API. Requires OPENAI_API_KEY in env.
    """
    model = os.getenv("OPENAI_MODEL", "gpt-5.2")
    client = OpenAI()

    context_text = "\n\n---\n\n".join(context_blocks).strip()
    prompt = (
        "You are a personal daybook assistant. "
        "Answer using ONLY the provided context. "
        "If the answer is not in context, say you don't know.\n\n"
        f"CONTEXT:\n{context_text}\n\n"
        f"QUESTION:\n{question}\n\n"
        "Answer (include short references like [path#chunk] when relevant):"
    )

    resp = client.responses.create(
        model=model,
        input=prompt
    )
    return resp.output_text
