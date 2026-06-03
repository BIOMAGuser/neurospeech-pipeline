import logging
import re
from typing import Dict, Any
from service.gpt_service import chat_completion
from prompt_config import gpt_cfg
from .whisper_word_count import raw_word_count
from .constants import FILLER_WORDS
from .nlp import get_nlp

logger = logging.getLogger(__name__)


def gpt_score(text: str, api_key: str) -> int:
    cfg = gpt_cfg()["saying"]
    prompt = cfg["prompt"].replace("{text}", text.strip())

    try:
        messages = [{"role": "user", "content": prompt}]
        answer = chat_completion(messages, api_key=api_key, max_tokens=cfg["max_tokens"], temperature=0.0)
        return 1 if re.search(r"\b1\b", answer.strip()) else 0
    except Exception as e:
        logger.error("GPT scoring error: %s", e)
        return 0


def analyze_saying(txt: str, api_key: str = None) -> Dict[str, Any]:
    nlp = get_nlp()
    doc = nlp(txt)
    fillers = sum(1 for t in doc if t.is_alpha and t.lemma_.lower() in FILLER_WORDS)

    return {
        "points": gpt_score(txt, api_key) if api_key else 0,
        "filler_word_count": fillers,
        "total_word_count": raw_word_count(txt),
    }
