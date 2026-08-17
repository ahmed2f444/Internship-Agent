import re
import time
import logging
from openai import OpenAI, RateLimitError
from app.config import settings

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)

# Groq models supporting function/tool calling
_FALLBACK_MODELS = [
    "llama-3.1-8b-instant",    # Primary (fast & low latency)
    "llama-3.3-70b-versatile", # High capability fallback
]

def _extract_retry_seconds(error_message: str) -> float:
    """Parse 'Please try again in Xs' from Groq error message."""
    match = re.search(r"try again in ([\d.]+)s", str(error_message))
    if match:
        return float(match.group(1))
    return 4.0   # safe default

def chat_completion(messages: list[dict], tools: list[dict] | None = None, tool_choice: str = "auto"):
    kwargs = {}
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice

    models_to_try = [settings.groq_model] + [m for m in _FALLBACK_MODELS if m != settings.groq_model]

    for i, model in enumerate(models_to_try):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
                **kwargs,
            )
        except RateLimitError as exc:
            wait = _extract_retry_seconds(str(exc))
            if i < len(models_to_try) - 1:
                # Try the next model immediately before sleeping
                logger.warning(f"[Groq] Rate limit on '{model}', trying next model...")
                continue
            else:
                # All models exhausted — wait on the primary and retry once
                logger.warning(f"[Groq] All models rate-limited. Waiting {wait:.1f}s then retrying...")
                time.sleep(wait + 0.5)
                return client.chat.completions.create(
                    model=settings.groq_model,
                    messages=messages,
                    temperature=0.2,
                    **kwargs,
                )
        except Exception as exc:
            if i < len(models_to_try) - 1:
                logger.warning(f"[Groq] Error on '{model}': {exc}. Trying next model...")
                continue
            raise exc

    raise RuntimeError("All Groq models failed unexpectedly.")