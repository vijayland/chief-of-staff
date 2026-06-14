"""LLM client — OpenAI for both chat and embeddings.

Chat  : gpt-4o-mini           ($0.15/1M input, $0.60/1M output)
Embed : text-embedding-3-small ($0.02/1M tokens, 1536-dim)
"""

import asyncio
import hashlib
import math
import structlog
from openai import AsyncOpenAI, BadRequestError, RateLimitError
from app.config import settings

logger = structlog.get_logger()

# Single OpenAI client for both chat and embeddings
_openai = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    timeout=30.0,
    max_retries=0,
)


def _hash_embedding(text: str, dims: int) -> list[float]:
    """Deterministic fallback when embedding API is unavailable."""
    seed = hashlib.sha256(text.encode()).digest()
    floats: list[float] = []
    i = 0
    while len(floats) < dims:
        chunk = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
        for j in range(0, len(chunk) - 3, 4):
            val = int.from_bytes(chunk[j:j + 4], "big") / 0xFFFFFFFF
            floats.append(val * 2 - 1)
            if len(floats) == dims:
                break
        i += 1
    norm = math.sqrt(sum(x * x for x in floats)) or 1.0
    return [x / norm for x in floats]


async def chat_completion(
    messages: list[dict],
    system: str = "",
    tools: list[dict] | None = None,
    model_override: str | None = None,
) -> object:
    """Send a chat request to OpenAI with automatic retry on rate-limit."""
    all_messages = []
    if system:
        all_messages.append({"role": "system", "content": system})
    all_messages.extend(messages)

    kwargs: dict = {
        "model": model_override or settings.OPENAI_MODEL,
        "max_tokens": settings.OPENAI_MAX_TOKENS,
        "messages": all_messages,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    for attempt in range(4):
        try:
            return await _openai.chat.completions.create(**kwargs)
        except RateLimitError as exc:
            if attempt == 3:
                raise
            # Honour the Retry-After header if present, else exponential backoff
            retry_after = None
            try:
                retry_after = float(exc.response.headers.get("retry-after", 0))
            except Exception:
                pass
            wait = retry_after if retry_after and retry_after > 0 else 15 * (2 ** attempt)
            logger.warning("openai_rate_limit", attempt=attempt + 1, wait=wait, error=str(exc)[:120])
            await asyncio.sleep(wait)
        except BadRequestError:
            if tools:
                kwargs.pop("tools", None)
                kwargs.pop("tool_choice", None)
                tools = None
            else:
                raise

    return await _openai.chat.completions.create(**kwargs)


async def get_embedding(text: str) -> list[float]:
    """Embed text using text-embedding-3-small (1536-dim)."""
    text = text.replace("\n", " ").strip()
    dims = settings.MEMORY_EMBEDDING_DIM

    for attempt in range(3):
        try:
            response = await _openai.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=text,
            )
            return response.data[0].embedding
        except RateLimitError:
            if attempt == 2:
                break
            await asyncio.sleep(5 * (attempt + 1))
        except Exception as exc:
            logger.warning("openai_embedding_failed", error=str(exc)[:200])
            break

    logger.warning("embedding_fallback_to_hash")
    return _hash_embedding(text, dims=dims)
