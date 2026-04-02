from __future__ import annotations

from .models import CandidateFeatures, CandidateMatch


class RuleScorer:
    def shortlist(
        self,
        matches: list[CandidateMatch],
        features: list[CandidateFeatures],
    ) -> list[tuple[CandidateMatch, CandidateFeatures]]:
        feature_map = {feature.mc_id: feature for feature in features}
        shortlisted: list[tuple[CandidateMatch, CandidateFeatures]] = []
        for match in matches:
            feature = feature_map[match.mc_id]
            if feature.same_as_source:
                continue
            if feature.rule_decision:
                shortlisted.append((match, feature))
                continue
            if match.match_score >= 0.65 and feature.standalone_near_phrase > 0:
                shortlisted.append((match, feature))
                continue
            if feature.rule_score >= 0.4 and not feature.bundled_near_phrase:
                shortlisted.append((match, feature))
        shortlisted.sort(key=lambda pair: (-pair[1].rule_score, -pair[0].match_score, pair[0].mc_title))
        return shortlisted
