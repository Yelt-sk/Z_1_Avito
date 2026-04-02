from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Microcategory:
    mc_id: int
    mc_title: str
    key_phrases: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Microcategory":
        return cls(
            mc_id=int(data["mcId"]),
            mc_title=str(data["mcTitle"]),
            key_phrases=[str(value) for value in data.get("keyPhrases", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mcId": self.mc_id,
            "mcTitle": self.mc_title,
            "keyPhrases": self.key_phrases,
        }


@dataclass(slots=True)
class Item:
    item_id: int
    mc_id: int
    mc_title: str
    description: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Item":
        return cls(
            item_id=int(data["itemId"]),
            mc_id=int(data["mcId"]),
            mc_title=str(data["mcTitle"]),
            description=str(data["description"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "itemId": self.item_id,
            "mcId": self.mc_id,
            "mcTitle": self.mc_title,
            "description": self.description,
        }


@dataclass(slots=True)
class Draft:
    mc_id: int
    mc_title: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"mcId": self.mc_id, "mcTitle": self.mc_title, "text": self.text}


@dataclass(slots=True)
class CandidateMatch:
    mc_id: int
    mc_title: str
    matched_phrases: list[str]
    match_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "mcId": self.mc_id,
            "mcTitle": self.mc_title,
            "matchedPhrases": self.matched_phrases,
            "matchScore": round(self.match_score, 4),
        }


@dataclass(slots=True)
class CandidateFeatures:
    mc_id: int
    standalone_hits: list[str]
    bundled_hits: list[str]
    standalone_near_phrase: int
    bundled_near_phrase: int
    phrase_mentions: int
    independent_mentions: int
    same_as_source: bool
    rule_score: float
    rule_decision: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "mcId": self.mc_id,
            "standaloneHits": self.standalone_hits,
            "bundledHits": self.bundled_hits,
            "standaloneNearPhrase": self.standalone_near_phrase,
            "bundledNearPhrase": self.bundled_near_phrase,
            "phraseMentions": self.phrase_mentions,
            "independentMentions": self.independent_mentions,
            "sameAsSource": self.same_as_source,
            "ruleScore": round(self.rule_score, 4),
            "ruleDecision": self.rule_decision,
        }


@dataclass(slots=True)
class VerificationDecision:
    mc_id: int
    is_standalone: bool
    confidence: float
    rationale: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mcId": self.mc_id,
            "isStandalone": self.is_standalone,
            "confidence": round(self.confidence, 4),
            "rationale": self.rationale,
            "source": self.source,
        }


@dataclass(slots=True)
class PredictionResult:
    should_split: bool
    drafts: list[Draft]
    verified_microcategories: list[dict[str, Any]] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self, include_debug: bool = False) -> dict[str, Any]:
        payload = {
            "shouldSplit": self.should_split,
            "drafts": [draft.to_dict() for draft in self.drafts],
            "verifiedMicrocategories": self.verified_microcategories,
        }
        if include_debug:
            payload["debug"] = self.debug
        return payload
