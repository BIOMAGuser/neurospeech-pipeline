from typing import Dict, Any
from .whisper_word_count import raw_word_count
from .constants import FILLER_WORDS
from .nlp import get_nlp

ACTORS = {
    "mutter", "mama", "vater", "papa",
    "junge", "kind", "mädchen", "kinder",
}

PLACES = {
    "küche", "wohnraum", "zimmer", "außenbereich", "garten", "fenster",
}

OBJECTS = {
    "teller", "glas", "hocker", "stuhl", "tisch",
    "spülbecken", "wasserhahn", "wasser", "arbeitsplatte",
    "vorhang", "kekse", "geschirr", "schrank", "boden",
}

ACTIONS = {
    "nimmt", "klaut", "greift", "fällt", "rutscht",
    "spült", "trocknet", "gießt", "fragt", "bemerkt", "schaut", "reagiert",
}

PICTURE_CONCEPTS = ACTORS | PLACES | OBJECTS | ACTIONS


def analyze_picture(txt: str) -> Dict[str, Any]:
    nlp = get_nlp()
    doc = nlp(txt)
    lemmas = [t.lemma_.lower() for t in doc if t.is_alpha]
    concepts = {lemma for lemma in lemmas if lemma in PICTURE_CONCEPTS}

    sents = list(doc.sents)
    sentence_count = len(sents)

    pos_counts = {
        "verb_count": sum(1 for t in doc if t.pos_ == "VERB"),
        "noun_count": sum(1 for t in doc if t.pos_ == "NOUN"),
        "pronoun_count": sum(1 for t in doc if t.pos_ == "PRON"),
        "adverb_count": sum(1 for t in doc if t.pos_ == "ADV"),
        "adjective_count": sum(1 for t in doc if t.pos_ == "ADJ"),
    }

    total = sum(pos_counts.values()) or 1
    pos_ratios = {k.replace("_count", "_ratio"): v / total for k, v in pos_counts.items()}

    ttr = len(set(lemmas)) / len(lemmas) if lemmas else 0
    sent_len = len(lemmas) / sentence_count if sentence_count else 0
    fillers = sum(1 for t in doc if t.lemma_.lower() in FILLER_WORDS)

    return {
        "pic_points": len(concepts),
        "total_word_count": raw_word_count(txt),
        "sentence_count": sentence_count,
        **pos_counts,
        **pos_ratios,
        "ttr": round(ttr, 3),
        "filler_word_count": fillers,
        "avg_sentence_length": round(sent_len, 2),
    }
