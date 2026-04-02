from __future__ import annotations

import json

from .models import CandidateFeatures, CandidateMatch, Item, Microcategory


def build_verification_prompt(
    item: Item,
    shortlist: list[tuple[CandidateMatch, CandidateFeatures]],
) -> str:
    candidates = []
    for match, feature in shortlist:
        candidates.append(
            {
                "mcId": match.mc_id,
                "mcTitle": match.mc_title,
                "matchedPhrases": match.matched_phrases,
                "standaloneNearPhrase": feature.standalone_near_phrase,
                "bundledNearPhrase": feature.bundled_near_phrase,
                "phraseMentions": feature.phrase_mentions,
                "sameAsSource": feature.same_as_source,
            }
        )
    candidate_ids = [candidate["mcId"] for candidate in candidates]
    payload = {
        "instruction": "Return one JSON array item for each candidate below. Use only listed mcId values. If ambiguous, set isStandalone to false.",
        "requiredOutput": [{"mcId": mc_id, "isStandalone": False} for mc_id in candidate_ids],
        "sourceMcId": item.mc_id,
        "description": item.description,
        "candidates": candidates,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_draft_prompt(item: Item, microcategory: Microcategory, rationale: str) -> str:
    payload = {
        "task": "Rewrite the source ad into one short draft for the target microcategory.",
        "policy": [
            "Focus only on the target service.",
            "Do not mention unrelated bundled services.",
            "Preserve seller tone if possible.",
            "Return strict JSON only.",
            "Text should be brief.",
        ],
        "outputSchema": {
            "mcId": microcategory.mc_id,
            "mcTitle": microcategory.mc_title,
            "text": "draft text"
        },
        "sourceItem": item.to_dict(),
        "targetMicrocategory": microcategory.to_dict(),
        "acceptedRationale": rationale,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
