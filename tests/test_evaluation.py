from avito_splitter.data_loading import load_examples, load_microcategories
from avito_splitter.evaluation import evaluate_examples
from avito_splitter.pipeline import AvitoSplitterPipeline, PipelineConfig


def test_evaluation_returns_metrics() -> None:
    pipeline = AvitoSplitterPipeline(
        load_microcategories("data/microcategories.json"),
        config=PipelineConfig(enable_qwen=False),
    )
    metrics = evaluate_examples(pipeline, load_examples("data/examples.jsonl"))
    assert metrics["count"] == 4
    assert "microcategoryPrecision" in metrics
