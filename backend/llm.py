from groq import Groq
import logging
import os
from dotenv import load_dotenv
import time

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

_MODEL = "llama-3.3-70b-versatile"


def generate_response(query, chunks, memory_context="", retries=3, delay=2):
    try:
        if not GROQ_API_KEY:
            logger.error("GROQ_API_KEY not found in .env file")
            return "Error: GROQ_API_KEY not found in .env file.", []

        if not chunks:
            return "No relevant content found for this query. Try rephrasing.", []

        client = Groq(api_key=GROQ_API_KEY)

        context_parts = [f"[{i}] {chunk['text']}" for i, chunk in enumerate(chunks, 1)]
        context_string = "\n\n".join(context_parts)

        seen_urls = set()
        sources = []
        for chunk in chunks:
            if chunk["url"] not in seen_urls:
                seen_urls.add(chunk["url"])
                sources.append({"url": chunk["url"], "title": chunk["title"]})

        system_msg = (
            "You are a helpful assistant. Answer the user's question using ONLY "
            "the numbered sources provided. Cite sources inline by number, e.g. [1], [2]. "
            "If the sources are insufficient to answer, say so clearly."
        )
        user_msg = (
            f"Conversation History:\n{memory_context}\n\n"
            f"Sources:\n{context_string}\n\n"
            f"Question: {query}"
        )

        for attempt in range(retries):
            try:
                logger.info(f"Calling Groq {_MODEL} (attempt {attempt + 1})")
                completion = client.chat.completions.create(
                    model=_MODEL,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    max_tokens=500,
                    temperature=0.7,
                    top_p=0.9,
                )
                response = completion.choices[0].message.content.strip()

                if not response or len(response.split()) < 5:
                    response = "Sorry, I couldn't generate a clear answer. Please try rephrasing."

                logger.debug(f"Generated response: {response[:200]}")
                return response, sources

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    raise

        raise Exception("All retry attempts failed.")

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return f"Error generating response: {e}", []


def generate_stream(query, chunks, memory_context=""):
    """Yield Groq response tokens one by one (stream=True)."""
    if not GROQ_API_KEY:
        yield "Error: GROQ_API_KEY not found."
        return
    if not chunks:
        yield "No relevant content found for this query. Try rephrasing."
        return

    client = Groq(api_key=GROQ_API_KEY)
    context_parts = [f"[{i}] {chunk['text']}" for i, chunk in enumerate(chunks, 1)]
    context_string = "\n\n".join(context_parts)

    system_msg = (
        "You are a helpful assistant. Answer the user's question using ONLY "
        "the numbered sources provided. Cite sources inline by number, e.g. [1], [2]. "
        "If the sources are insufficient to answer, say so clearly."
    )
    user_msg = (
        f"Conversation History:\n{memory_context}\n\n"
        f"Sources:\n{context_string}\n\n"
        f"Question: {query}"
    )

    try:
        completion = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=500,
            temperature=0.7,
            top_p=0.9,
            stream=True,
        )
        for chunk in completion:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as e:
        logger.error(f"Groq streaming error: {e}")
        yield f"\n\n[Generation error: {str(e)}]"
