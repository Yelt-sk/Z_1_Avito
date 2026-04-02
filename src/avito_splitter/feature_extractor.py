from __future__ import annotations

import re

from .dictionary_matcher import _token_similar
from .models import CandidateFeatures, CandidateMatch, Item
from .utils import normalize_text

STANDALONE_MARKERS = [
    "отдельно",
    "как отдельная услуга",
    "отдельная услуга",
    "самостоятельно",
    "только",
    "по отдельности",
    "индивидуально",
]

BUNDLED_MARKERS = [
    "под ключ",
    "в составе",
    "включая",
    "входит в",
    "комплексно",
    "комплекс работ",
    "в рамках",
    "все виды работ",
]

SENTENCE_SPLIT_RE = re.compile(r"[.!?;\n]+")


class FeatureExtractor:
    def extract(self, item: Item, match: CandidateMatch) -> CandidateFeatures:
        normalized_description = normalize_text(item.description)
        sentences = [segment.strip() for segment in SENTENCE_SPLIT_RE.split(normalized_description) if segment.strip()]
        normalized_standalone_markers = [(marker, normalize_text(marker)) for marker in STANDALONE_MARKERS]
        normalized_bundled_markers = [(marker, normalize_text(marker)) for marker in BUNDLED_MARKERS]
        standalone_hits = [marker for marker, normalized in normalized_standalone_markers if normalized in normalized_description]
        bundled_hits = [marker for marker, normalized in normalized_bundled_markers if normalized in normalized_description]

        phrase_mentions = 0
        independent_mentions = 0
        standalone_near_phrase = 0
        bundled_near_phrase = 0
        normalized_phrases = [normalize_text(phrase) for phrase in match.matched_phrases]
        tokens = normalized_description.split()

        for sentence in sentences:
            sentence_tokens = sentence.split()
            contains_phrase = any(self._contains_phrase(sentence_tokens, phrase.split()) for phrase in normalized_phrases)
            if not contains_phrase:
                continue
            phrase_mentions += 1
        for phrase in normalized_phrases:
            phrase_tokens = phrase.split()
            if not phrase_tokens:
                continue
            phrase_len = len(phrase_tokens)
            for index in range(0, len(tokens) - phrase_len + 1):
                if not self._tokens_match(tokens[index : index + phrase_len], phrase_tokens):
                    continue
                left_window = tokens[max(0, index - 4) : index]
                right_window = tokens[index + phrase_len : min(len(tokens), index + phrase_len + 4)]
                around = left_window + right_window
                if any(normalized in " ".join(around) for _, normalized in normalized_standalone_markers):
                    standalone_near_phrase += 1
                    independent_mentions += 1
                if any(normalized in " ".join(around) for _, normalized in normalized_bundled_markers):
                    bundled_near_phrase += 1

        same_as_source = match.mc_id == item.mc_id
        rule_score = (
            match.match_score * 0.4
            + standalone_near_phrase * 0.7
            + independent_mentions * 0.5
            + len(standalone_hits) * 0.2
            - bundled_near_phrase * 0.8
            - len(bundled_hits) * 0.15
            - (0.5 if same_as_source else 0.0)
        )
        rule_decision = (
            not same_as_source
            and phrase_mentions > 0
            and (standalone_near_phrase > bundled_near_phrase or rule_score >= 0.9)
        )

        return CandidateFeatures(
            mc_id=match.mc_id,
            standalone_hits=standalone_hits,
            bundled_hits=bundled_hits,
            standalone_near_phrase=standalone_near_phrase,
            bundled_near_phrase=bundled_near_phrase,
            phrase_mentions=phrase_mentions,
            independent_mentions=independent_mentions,
            same_as_source=same_as_source,
            rule_score=rule_score,
            rule_decision=rule_decision,
        )

    @staticmethod
    def _contains_phrase(sentence_tokens: list[str], phrase_tokens: list[str]) -> bool:
        if not phrase_tokens or len(sentence_tokens) < len(phrase_tokens):
            return False
        phrase_len = len(phrase_tokens)
        for index in range(0, len(sentence_tokens) - phrase_len + 1):
            if FeatureExtractor._tokens_match(sentence_tokens[index : index + phrase_len], phrase_tokens):
                return True
        return False

    @staticmethod
    def _tokens_match(left: list[str], right: list[str]) -> bool:
        if len(left) != len(right):
            return False
        for left_token, right_token in zip(left, right, strict=True):
            if _token_similar(left_token, right_token):
                continue
            return False
        return True
