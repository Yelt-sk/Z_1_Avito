from __future__ import annotations

from dataclasses import dataclass

from .dictionary_matcher import DictionaryMatcher
from .draft_generator import DraftGenerator
from .feature_extractor import FeatureExtractor
from .models import Draft, Item, Microcategory, PredictionResult, VerificationDecision
from .prompts import build_verification_prompt
from .qwen_client import QwenClient
from .rule_scorer import RuleScorer


@dataclass(slots=True)
class PipelineConfig:
    include_llm_debug: bool = False
    enable_qwen: bool = True
    max_llm_candidates: int = 5
    verification_max_tokens: int = 32
    verification_timeout_seconds: int = 35
    draft_max_tokens: int = 96
    draft_timeout_seconds: int = 45


class AvitoSplitterPipeline:
    def __init__(
        self,
        microcategories: list[Microcategory],
        config: PipelineConfig | None = None,
        qwen_client: QwenClient | None = None,
    ) -> None:
        self.microcategories = microcategories
        self.microcategory_map = {mc.mc_id: mc for mc in microcategories}
        self.config = config or PipelineConfig()
        self.matcher = DictionaryMatcher(microcategories)
        self.extractor = FeatureExtractor()
        self.rule_scorer = RuleScorer()
        self.qwen_client = qwen_client or QwenClient()
        self.draft_generator = DraftGenerator(self.qwen_client)

    def predict(self, item: Item, include_debug: bool = False) -> PredictionResult:
        verification = self.verify_only(item, include_debug=include_debug)
        accepted_ids = [row["mcId"] for row in verification.verified_microcategories]
        if not accepted_ids:
            return verification
        return self.generate_drafts_for_verified(
            item,
            accepted_ids,
            verification_result=verification,
            include_debug=include_debug,
        )

    def verify_only(self, item: Item, include_debug: bool = False) -> PredictionResult:
        matches = self.matcher.match(item.description)
        features = [self.extractor.extract(item, match) for match in matches]
        shortlist = self.rule_scorer.shortlist(matches, features)
        llm_candidates = self._build_llm_candidates(matches, features, shortlist)

        verification_meta: dict
        verification_timed_out = False
        if llm_candidates and self.config.enable_qwen:
            try:
                llm_decisions, verification_meta = self._verify_with_qwen(item, llm_candidates)
            except TimeoutError:
                llm_decisions = []
                verification_meta = {"transport": "timeout"}
                verification_timed_out = True
            except Exception as exc:  # noqa: BLE001
                llm_decisions = self._verify_with_rules_only(llm_candidates or shortlist)
                verification_meta = {"transport": "fallback-after-error", "error": str(exc)}
        else:
            llm_decisions = self._verify_with_rules_only(llm_candidates or shortlist)
            verification_meta = {"transport": "rules-only"}
        if not llm_decisions and llm_candidates:
            llm_decisions = self._verify_with_rules_only(llm_candidates)
            verification_meta = {**verification_meta, "fallbackUsed": "rules-after-empty"}

        verified_microcategories = [
            {
                "mcId": decision.mc_id,
                "mcTitle": self.microcategory_map[decision.mc_id].mc_title,
                "isStandalone": decision.is_standalone,
                "confidence": round(decision.confidence, 4),
                "source": decision.source,
            }
            for decision in llm_decisions
            if decision.is_standalone and decision.mc_id != item.mc_id
        ]

        result = PredictionResult(
            should_split=bool(verified_microcategories),
            drafts=[],
            verified_microcategories=verified_microcategories,
            debug={
                "matches": [match.to_dict() for match in matches],
                "features": [feature.to_dict() for feature in features],
                "shortlist": [
                    {"match": match.to_dict(), "features": feature.to_dict()}
                    for match, feature in shortlist
                ],
                "llmCandidates": [
                    {"match": match.to_dict(), "features": feature.to_dict()}
                    for match, feature in llm_candidates
                ],
                "verification": [decision.to_dict() for decision in llm_decisions],
                "verificationTimedOut": verification_timed_out,
            },
        )
        if include_debug or self.config.include_llm_debug:
            result.debug["qwenVerificationMeta"] = verification_meta
            result.debug["draftGenerationMeta"] = []
        return result

    def generate_drafts_for_verified(
        self,
        item: Item,
        verified_mc_ids: list[int],
        *,
        verification_result: PredictionResult | None = None,
        include_debug: bool = False,
    ) -> PredictionResult:
        verification_result = verification_result or self.verify_only(item, include_debug=include_debug)
        verification_map = {
            row["mcId"]: row for row in verification_result.verified_microcategories
        }
        drafts: list[Draft] = []
        draft_debug: list[dict] = []

        for mc_id in verified_mc_ids:
            if mc_id not in verification_map:
                continue
            microcategory = self.microcategory_map[mc_id]
            if self.config.enable_qwen:
                try:
                    draft, meta = self.draft_generator.generate(
                        item,
                        microcategory,
                        f"Verified standalone category {microcategory.mc_title}",
                        max_tokens=self.config.draft_max_tokens,
                        timeout_seconds=self.config.draft_timeout_seconds,
                    )
                except TimeoutError:
                    draft = Draft(microcategory.mc_id, microcategory.mc_title, f"{microcategory.mc_title}. Генерация черновика превысила timeout.")
                    meta = {"transport": "timeout"}
                except Exception as exc:  # noqa: BLE001
                    draft = Draft(microcategory.mc_id, microcategory.mc_title, f"{microcategory.mc_title}. {item.description.strip()}")
                    meta = {"transport": "fallback-after-error", "error": str(exc)}
            else:
                draft = Draft(microcategory.mc_id, microcategory.mc_title, f"{microcategory.mc_title}. {item.description.strip()}")
                meta = {"transport": "rule-fallback"}
            drafts.append(draft)
            draft_debug.append({"mcId": mc_id, "meta": meta})

        verification_result.drafts = drafts
        verification_result.should_split = bool(verification_result.verified_microcategories)
        if include_debug or self.config.include_llm_debug:
            verification_result.debug["draftGenerationMeta"] = draft_debug
        return verification_result

    def _build_llm_candidates(
        self,
        matches: list,
        features: list,
        shortlist: list[tuple],
    ) -> list[tuple]:
        feature_map = {feature.mc_id: feature for feature in features}
        preferred_ids = {match.mc_id for match, _ in shortlist}
        ranked: list[tuple] = []
        for match in matches:
            feature = feature_map[match.mc_id]
            if feature.same_as_source:
                continue
            ranked.append((match, feature))
        ranked.sort(
            key=lambda pair: (
                -(1 if pair[0].mc_id in preferred_ids else 0),
                -pair[0].match_score,
                -pair[1].phrase_mentions,
                -pair[1].standalone_near_phrase,
                pair[0].mc_title,
            )
        )
        return ranked[: self.config.max_llm_candidates]

    def _verify_with_qwen(self, item: Item, shortlist: list[tuple]) -> tuple[list[VerificationDecision], dict]:
        prompt = build_verification_prompt(item, shortlist)
        payload, meta = self.qwen_client.generate_json(
            prompt,
            max_tokens=self.config.verification_max_tokens,
            timeout_seconds=self.config.verification_timeout_seconds,
        )
        rows = self._coerce_verification_rows(payload)
        feature_map = {feature.mc_id: feature for _, feature in shortlist}
        decisions: list[VerificationDecision] = []
        for row in rows:
            mc_id = int(row["mcId"])
            feature = feature_map.get(mc_id)
            if feature is None:
                continue
            model_is_standalone = bool(row.get("isStandalone", False)) and not feature.same_as_source
            model_confidence = float(row.get("confidence", 0.0) or (0.9 if row.get("isStandalone", False) else 0.1))
            # If rules see a strong standalone signal and the model only gives a weak negative,
            # keep the candidate. This preserves the hybrid design instead of letting one bad
            # short JSON answer erase a strong local pattern.
            if (
                not model_is_standalone
                and feature.rule_decision
                and feature.rule_score >= 0.9
                and model_confidence <= 0.2
            ):
                decisions.append(
                    VerificationDecision(
                        mc_id=mc_id,
                        is_standalone=True,
                        confidence=max(0.56, model_confidence),
                        rationale="Hybrid override: rules detected a strong standalone pattern despite weak model rejection.",
                        source="hybrid-override",
                    )
                )
                continue
            decisions.append(
                VerificationDecision(
                    mc_id=mc_id,
                    is_standalone=model_is_standalone,
                    confidence=model_confidence,
                    rationale=str(row.get("rationale", "")).strip() or "Short JSON verifier response",
                    source="qwen",
                )
            )
        seen = {decision.mc_id for decision in decisions}
        for _, feature in shortlist:
            if feature.mc_id not in seen:
                decisions.append(
                    VerificationDecision(
                        mc_id=feature.mc_id,
                        is_standalone=feature.rule_decision,
                        confidence=0.51 if feature.rule_decision else 0.2,
                        rationale="Filled from rules because model response missed this candidate.",
                        source="rule-fallback",
                    )
                )
        decisions.sort(key=lambda item: (-item.confidence, item.mc_id))
        return decisions, meta

    def _verify_with_rules_only(self, shortlist: list[tuple]) -> list[VerificationDecision]:
        return [
            VerificationDecision(
                mc_id=feature.mc_id,
                is_standalone=feature.rule_decision,
                confidence=0.55 if feature.rule_decision else 0.15,
                rationale="Decided only by rule-based verifier.",
                source="rules",
            )
            for _, feature in shortlist
        ]

    @staticmethod
    def _coerce_verification_rows(payload: object) -> list[dict]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            if all(key in payload for key in ("mcId", "isStandalone")):
                return [payload]
            for key in ("decisions", "results", "items", "candidates"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [row for row in value if isinstance(row, dict)]
        raise TypeError(f"Unsupported verification payload: {type(payload)!r}")
