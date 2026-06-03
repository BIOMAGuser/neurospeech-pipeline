import logging
import time

from openai import OpenAI

from prompt_config import gpt_cfg

logger = logging.getLogger(__name__)


def chat_completion(messages: list, api_key: str, model: str = None, max_tokens: int = None, temperature: float = None) -> str:
    cfg = gpt_cfg()
    used_model = model or cfg["model"]
    try:
        client = OpenAI(api_key=api_key)
        logger.info("GPT request: model=%s", used_model)
        start = time.perf_counter()
        response = client.chat.completions.create(
            model=used_model,
            messages=messages,
            max_tokens=max_tokens if max_tokens is not None else cfg["max_tokens"],
            temperature=temperature if temperature is not None else cfg["temperature"],
        )
        result = response.choices[0].message.content.strip()
        elapsed = time.perf_counter() - start
        logger.info("GPT response: %d chars in %.2fs", len(result), elapsed)
        return result
    except Exception as e:
        logger.error("GPT chat completion error: %s", e)
        return ""
