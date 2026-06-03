import logging
import re
import json
from typing import Dict, Any
from service.gpt_service import chat_completion
from prompt_config import gpt_cfg
from .whisper_word_count import raw_word_count

logger = logging.getLogger(__name__)


def gpt_extract_vegetables(txt: str, api_key: str) -> Dict[str, Any]:
    cfg = gpt_cfg()["veggie"]
    prompt = cfg["prompt"].replace("{text}", txt.strip())

    try:
        messages = [{"role": "user", "content": prompt}]
        answer = chat_completion(messages, api_key=api_key, max_tokens=cfg["max_tokens"], temperature=0.0)

        json_match = re.search(r'\{.*\}', answer, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return {
                "vegetables": [v.lower().strip() for v in data.get("vegetables", [])],
                "unrelated_foods": [u.lower().strip() for u in data.get("unrelated_foods", [])],
            }
    except Exception as e:
        logger.error("GPT extraction error: %s", e)

    return {"vegetables": [], "unrelated_foods": []}


def analyze_veggie(txt: str, api_key: str = None) -> Dict[str, Any]:
    result = gpt_extract_vegetables(txt, api_key) if api_key else {"vegetables": [], "unrelated_foods": []}
    vegetables = result.get("vegetables", [])
    unrelated = result.get("unrelated_foods", [])

    unique_vegetables = list(dict.fromkeys(vegetables))
    duplicate_count = len(vegetables) - len(unique_vegetables)
    unique_unrelated = list(dict.fromkeys(unrelated))

    return {
        "points": len(unique_vegetables),
        "correct_words": unique_vegetables,
        "unrelated_words": len(unique_unrelated),
        "unrelated_words_list": unique_unrelated,
        "duplicate_count": duplicate_count,
        "total_word_count": raw_word_count(txt),
    }
