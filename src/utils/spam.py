import re
import math
import langid

from collections import Counter

ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")

def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum((c/n) * math.log2(c/n) for c in counts.values())

def looks_like_gibberish(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 8:
        return True

    # Not enough space => random token
    space_ratio = t.count(" ") / max(1, len(t))
    if space_ratio < 0.03 and len(t) > 20:
        return True

    # Alnum ration too high, not enough punctuation
    alnum_ratio = sum(ch.isalnum() for ch in t) / len(t)
    if alnum_ratio > 0.92 and " " not in t:
        return True

    # FR/EN: au moins quelques voyelles si texte latin
    # FR/EN: at least few vowels
    has_arabic = bool(ARABIC_RE.search(t))
    has_latin = any("a" <= ch.lower() <= "z" for ch in t)
    if has_latin and not has_arabic:
        vowels = sum(ch.lower() in "aeiouy" for ch in t)
        if vowels / max(1, sum(ch.isalpha() for ch in t)) < 0.20:
            return True

    # High entropy => often random (needs adjusting)
    ent = shannon_entropy(t)
    if ent > 4.3 and len(t) > 25:
        return True

    # Too many repetitions of the same characteristic
    most_common = Counter(t).most_common(1)[0][1] / len(t)
    if most_common > 0.35:
        return True

    return False

def detect_lang_light(text: str):
    t = (text or "").strip()
    if ARABIC_RE.search(t):
        return "ar", 1.0  # arab detected => high confidence

    try:
        return langid.classify(t)
    except Exception:
        return None, None

def is_message_acceptable(message: str) -> tuple[bool, str]:
    if looks_like_gibberish(message):
        return False, "gibberish"

    lang, score = detect_lang_light(message)

    # Autoriser FR/EN/AR (et tu peux élargir)
    if lang == "ar":
        return True, "ok_ar"

    if lang in {"fr", "en"}:
        # Threshold to be adjusted according to your tests; for Langid, a score > -50 is often OK
        # but it depends on the length of the text.
        if score is None or score > -80:
            return True, f"ok_{lang}"
        return False, "low_confidence_lang"

    # We refused all the other langs
    return False, "lang_not_allowed"
