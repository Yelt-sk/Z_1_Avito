# Avito Splitter

Локальный Python-пайплайн для задачи автоматического выделения самостоятельных услуг и генерации черновиков объявлений в категории "Ремонт и отделка".

Проект использует гибридный подход:
- словарный поиск кандидатов по `keyPhrases`;
- explainable rule-based признаки и hybrid override;
- локальный `Qwen 3` как semantic verifier и generator;
- CLI для `predict`, `evaluate`, `calibrate`;
- отдельный тестовый интерфейс `test_interface.py`;
- подробную документацию по архитектуре, данным, prompt-ам и оценке.

## Быстрый обзор
- Пакет: `src/avito_splitter`
- Демо-данные: `data/`
- Тесты: `tests/`
- Интерфейс для ручной проверки:

```bash
python D:\projects\Avito\test_interface.py
```

- Основные CLI-команды:

```bash
python -m avito_splitter predict --item data/input_item.json --dict data/microcategories.json
python -m avito_splitter evaluate --examples data/examples.jsonl --dict data/microcategories.json --disable-qwen
```

Для запуска без LLM:

```bash
python -m avito_splitter predict --item data/input_item.json --dict data/microcategories.json --disable-qwen --debug
```

## Что делает пайплайн
1. Находит кандидатов-микрокатегории по словарю.
2. Считает объяснимые признаки самостоятельности и bundled-упоминаний.
3. Отправляет разумный набор кандидатов в локальный `Qwen 3` на короткую verification-фазу.
4. Возвращает `verifiedMicrocategories` для дополнительных draft-объявлений.
5. Только на втором шаге генерирует узкие `draft`-тексты для подтвержденных категорий.

## Что важно понимать
- Исходная микрокатегория объявления не дублируется в `verifiedMicrocategories`.
- `verifiedMicrocategories` означает именно дополнительные категории для split, а не все категории, замеченные в тексте.
- В интерфейсе сначала выполняется `Определить категории`, потом отдельно `Сгенерировать draft`.

## Документация
- [README_START.md](D:\projects\Avito\README_START.md)
- [README_ARCHITECTURE.md](D:\projects\Avito\README_ARCHITECTURE.md)
- [README_DATA.md](D:\projects\Avito\README_DATA.md)
- [README_EVAL.md](D:\projects\Avito\README_EVAL.md)
- [README_PROMPTS.md](D:\projects\Avito\README_PROMPTS.md)
- [README_DECISIONS.md](D:\projects\Avito\README_DECISIONS.md)
