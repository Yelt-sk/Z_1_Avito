# README_EVAL

## Команды

```bash
python -m avito_splitter evaluate --examples data/examples.jsonl --dict data/microcategories.json --disable-qwen
python -m avito_splitter calibrate --examples data/examples.jsonl --dict data/microcategories.json --disable-qwen
```

## Что считает `evaluate`
- `shouldSplitAccuracy`
- `microcategoryPrecision`
- `microcategoryRecall`
- `microcategoryF1`
- `truePositives`
- `falsePositives`
- `falseNegatives`
- `errorTypes`
- `errors`

## Что важно смотреть в первую очередь
- `falsePositives`
  потому что задача precision-first.
- ошибки типа bundled mention
  это главный риск для продукта.
- случаи, где `shouldSplit` сработал, но неверно выбран набор `mcId`.
- отдельно смотреть, не теряются ли категории из-за retrieval, а не из-за LLM.

## Как интерпретировать калибровку
`calibrate` пока делает lightweight-отчет:
- повторно считает метрики;
- предлагает, что тюнить дальше:
  ужесточать bundled penalties или расширять phrase coverage.

## Что улучшать, если качество низкое
- добавить больше `keyPhrases`;
- расширить списки standalone/bundled markers;
- тюнить `llmCandidates`, а не только rule shortlist;
- добавить больше обучающих кейсов со сложными формулировками;
- уточнить prompt verifier'а.
- измерять отдельно verification latency и draft generation latency.
