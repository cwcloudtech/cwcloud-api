import re
import math
import langid

from collections import Counter

from utils.common import is_true

_ALLOWED_LANGS = {"fr", "en", "de", "it", "es"}
_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")

def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum((c/n) * math.log2(c/n) for c in counts.values())

def looks_like_gibberish(text: str) -> bool:
    t = (text or "").strip()
    n = len(t)

    if n < 8:
        return True, "message_too_short"

    # If the message is short, be permissive and only reject if it strongly looks like a random token.
    if n <= 12:
        # If it has a space, it's likely human (e.g. "hi there", "merci bcp")
        if " " in t:
            return False, "message_acceptable"

        # Mostly alphanumeric with no spaces can be either a word or a token.
        # Reject only if it looks "token-like": high entropy + low vowel ratio (Latin) / mixed case digits, etc.
        alnum_ratio = sum(ch.isalnum() for ch in t) / n
        if alnum_ratio > 0.95:
            # If Arabic script is present, accept (short Arabic words are common)
            if _ARABIC_RE.search(t):
                return False, "message_acceptable"

            # If Latin letters exist, require a minimal vowel ratio to look like a real word.
            has_latin = any("a" <= ch.lower() <= "z" for ch in t)
            if has_latin:
                vowels = sum(ch.lower() in "aeiouy" for ch in t)
                alpha = sum(ch.isalpha() for ch in t)
                # Very low vowels in a short Latin token often indicates randomness.
                if alpha >= 6 and vowels / max(1, alpha) < 0.15:
                    # Entropy check to avoid rejecting valid short words like "rhythm"
                    if shannon_entropy(t) > 3.2:
                        return True, "gibberish"

        # default: do not reject short messages
        return False, "message_acceptable"

    # Not enough space => random token
    space_ratio = t.count(" ") / max(1, n)
    if space_ratio < 0.03 and n > 20:
        return True, "giberrish"

    # Alnum ration too high, not enough punctuation
    alnum_ratio = sum(ch.isalnum() for ch in t) / n
    if alnum_ratio > 0.92 and " " not in t:
        return True, "giberrish"

    # FR/EN: au moins quelques voyelles si texte latin
    # FR/EN: at least few vowels
    has_arabic = bool(_ARABIC_RE.search(t))
    has_latin = any("a" <= ch.lower() <= "z" for ch in t)
    if has_latin and not has_arabic:
        vowels = sum(ch.lower() in "aeiouy" for ch in t)
        if vowels / max(1, sum(ch.isalpha() for ch in t)) < 0.20:
            return True, "giberrish"

    # High entropy => often random (needs adjusting)
    ent = shannon_entropy(t)
    if ent > 4.3 and n > 25:
        return True, "giberrish"

    # Too many repetitions of the same characteristic
    most_common = Counter(t).most_common(1)[0][1] / n
    if most_common > 0.35:
        return True, "giberrish"

    return False, "message_acceptable"

def detect_lang_light(text: str):
    t = (text or "").strip()
    if _ARABIC_RE.search(t):
        return "ar", 1.0  # arab detected => high confidence

    try:
        return langid.classify(t)
    except Exception:
        return None, None

def is_message_acceptable(message: str) -> tuple[bool, str]:
    is_gibberish, i18n_code = looks_like_gibberish(message)
    if is_true(is_gibberish):
        return False, i18n_code

    lang, score = detect_lang_light(message)

    # Autoriser FR/EN/AR (et tu peux élargir)
    if lang == "ar":
        return True, "ok_ar"

    if lang in _ALLOWED_LANGS:
        # Threshold to be adjusted according to your tests; for Langid, a score > -50 is often OK
        # but it depends on the length of the text.
        if score is None or score > -80:
            return True, f"ok_{lang}"
        return False, "low_confidence_lang"

    # We refused all the other langs
    return False, "lang_not_allowed"
