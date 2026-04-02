from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher

from .models import CandidateMatch, Microcategory
from .utils import normalize_text


def _soft_contains(haystack: str, needle: str, min_ratio: float = 0.84) -> bool:
    if needle in haystack:
        return True
    hay_tokens = haystack.split()
    needle_tokens = needle.split()
    size = len(needle_tokens)
    if not size or len(hay_tokens) < size:
        return False
    for index in range(0, len(hay_tokens) - size + 1):
        window = " ".join(hay_tokens[index : index + size])
        if SequenceMatcher(None, window, needle).ratio() >= min_ratio:
            return True
        if _tokens_match(hay_tokens[index : index + size], needle_tokens):
            return True
    return False


def _stem_token(token: str) -> str:
    endings = (
        "иями",
        "ями",
        "ами",
        "ого",
        "ему",
        "ому",
        "ыми",
        "ими",
        "иях",
        "ах",
        "ях",
        "ия",
        "ий",
        "ый",
        "ой",
        "ая",
        "яя",
        "ое",
        "ее",
        "ые",
        "ие",
        "ов",
        "ев",
        "ом",
        "ем",
        "ам",
        "ям",
        "ую",
        "юю",
        "а",
        "я",
        "ы",
        "и",
        "е",
        "у",
        "ю",
        "о",
    )
    for ending in endings:
        if token.endswith(ending) and len(token) > len(ending) + 2:
            return token[: -len(ending)]
    return token


def _tokens_match(left: list[str], right: list[str]) -> bool:
    if len(left) != len(right):
        return False
    for left_token, right_token in zip(left, right, strict=True):
        if _token_similar(left_token, right_token):
            continue
        return False
    return True


def _token_similar(left_token: str, right_token: str) -> bool:
    if left_token == right_token:
        return True
    left_stem = _stem_token(left_token)
    right_stem = _stem_token(right_token)
    if left_stem == right_stem:
        return True
    common_prefix = 0
    for left_char, right_char in zip(left_stem, right_stem, strict=False):
        if left_char != right_char:
            break
        common_prefix += 1
    return common_prefix >= 5


class DictionaryMatcher:
    def __init__(self, microcategories: list[Microcategory]) -> None:
        self.microcategories = microcategories

    def match(self, description: str) -> list[CandidateMatch]:
        normalized = normalize_text(description)
        found: dict[int, list[str]] = defaultdict(list)
        scores: dict[int, float] = defaultdict(float)

        for microcategory in self.microcategories:
            for phrase in microcategory.key_phrases:
                normalized_phrase = normalize_text(phrase)
                if not normalized_phrase:
                    continue
                if _soft_contains(normalized, normalized_phrase):
                    found[microcategory.mc_id].append(phrase)
                    scores[microcategory.mc_id] += min(1.0, 0.5 + len(normalized_phrase.split()) * 0.15)

        matches: list[CandidateMatch] = []
        for microcategory in self.microcategories:
            matched_phrases = found.get(microcategory.mc_id)
            if not matched_phrases:
                continue
            score = min(1.0, scores[microcategory.mc_id] / max(1, len(microcategory.key_phrases)))
            matches.append(
                CandidateMatch(
                    mc_id=microcategory.mc_id,
                    mc_title=microcategory.mc_title,
                    matched_phrases=sorted(set(matched_phrases)),
                    match_score=score,
                )
            )

        matches.sort(key=lambda item: (-item.match_score, item.mc_title))
        return matches
