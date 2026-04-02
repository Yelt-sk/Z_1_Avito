from avito_splitter.data_loading import load_microcategories
from avito_splitter.models import Item
from avito_splitter.pipeline import AvitoSplitterPipeline, PipelineConfig


class FakeQwenClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_json(self, prompt: str, **_: object):
        self.calls.append(prompt)
        if "Rewrite the source ad" in prompt:
            return (
                {
                    "mcId": 101,
                    "mcTitle": "Сантехника",
                    "text": "Выполняем сантехнические работы отдельно."
                },
                {"transport": "fake"},
            )
        return (
            [
                {
                    "mcId": 101,
                    "isStandalone": True,
                    "confidence": 0.9,
                    "rationale": "The ad explicitly says the service is provided separately."
                }
            ],
            {"transport": "fake"},
        )


def test_pipeline_avoids_split_for_bundled_mentions() -> None:
    pipeline = AvitoSplitterPipeline(
        load_microcategories("data/microcategories.json"),
        config=PipelineConfig(enable_qwen=False),
    )
    item = Item(
        item_id=1,
        mc_id=201,
        mc_title="Ремонт квартир и домов под ключ",
        description="Делаем ремонт под ключ, включая электрику и сантехнику.",
    )
    result = pipeline.predict(item)
    assert result.should_split is False
    assert result.drafts == []


def test_pipeline_splits_when_services_are_explicitly_separate() -> None:
    pipeline = AvitoSplitterPipeline(
        load_microcategories("data/microcategories.json"),
        config=PipelineConfig(enable_qwen=False),
    )
    item = Item(
        item_id=2,
        mc_id=201,
        mc_title="Ремонт квартир и домов под ключ",
        description="Выполняем электрику отдельно, сантехнику отдельно, а также ремонт под ключ.",
    )
    result = pipeline.predict(item)
    mc_ids = {row["mcId"] for row in result.verified_microcategories}
    assert result.should_split is True
    assert {101, 102}.issubset(mc_ids)


def test_pipeline_uses_qwen_even_when_rule_shortlist_is_empty() -> None:
    fake_qwen = FakeQwenClient()
    pipeline = AvitoSplitterPipeline(
        load_microcategories("data/microcategories.json"),
        config=PipelineConfig(enable_qwen=True),
        qwen_client=fake_qwen,
    )
    item = Item(
        item_id=3,
        mc_id=201,
        mc_title="Ремонт квартир и домов под ключ",
        description="Делаем ремонт под ключ и сантехнику как отдельную услугу.",
    )
    result = pipeline.verify_only(item, include_debug=True)
    assert result.should_split is True
    assert any(row["mcId"] == 101 for row in result.verified_microcategories)
    assert result.debug["qwenVerificationMeta"]["transport"] == "fake"
    assert len(fake_qwen.calls) >= 1


def test_generate_drafts_runs_as_second_step() -> None:
    fake_qwen = FakeQwenClient()
    pipeline = AvitoSplitterPipeline(
        load_microcategories("data/microcategories.json"),
        config=PipelineConfig(enable_qwen=True),
        qwen_client=fake_qwen,
    )
    item = Item(
        item_id=4,
        mc_id=201,
        mc_title="Ремонт квартир и домов под ключ",
        description="Делаем ремонт под ключ и сантехнику как отдельную услугу.",
    )
    verification = pipeline.verify_only(item, include_debug=True)
    result = pipeline.generate_drafts_for_verified(item, [101], verification_result=verification, include_debug=True)
    assert any(draft.mc_id == 101 for draft in result.drafts)
    assert len(fake_qwen.calls) >= 2
