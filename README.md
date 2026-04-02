# Avito Splitter

Локальный Python-пайплайн для задачи автоматического выделения самостоятельных услуг и генерации черновиков объявлений в категории "Ремонт и отделка".

Проект использует гибридный подход:
- словарный поиск кандидатов по `keyPhrases`;
- explainable rule-based фильтрацию для высокого precision;
- локальный `Qwen 3` как verifier и draft generator;
- CLI для `predict`, `evaluate`, `calibrate`;
- подробную документацию по архитектуре, данным, prompt-ам и оценке.

## Быстрый обзор
- Пакет: `src/avito_splitter`
- Демо-данные: `data/`
- Тесты: `tests/`
- Основная команда:

```bash
python -m avito_splitter predict --item data/input_item.json --dict data/microcategories.json
```

Для запуска без LLM:

```bash
python -m avito_splitter predict --item data/input_item.json --dict data/microcategories.json --disable-qwen --debug
```

## Что делает пайплайн
1. Находит кандидатов-микрокатегории по словарю.
2. Считает объяснимые признаки самостоятельности и bundled-упоминаний.
3. Отправляет shortlist кандидатов в локальный `Qwen 3`.
4. Получает JSON-решение `standalone / not standalone`.
5. Для подтвержденных категорий генерирует узкий `draft` через `Qwen 3`.

## Документация
- [README_START.md](D:\projects\Avito\README_START.md)
- [README_ARCHITECTURE.md](D:\projects\Avito\README_ARCHITECTURE.md)
- [README_DATA.md](D:\projects\Avito\README_DATA.md)
- [README_EVAL.md](D:\projects\Avito\README_EVAL.md)
- [README_PROMPTS.md](D:\projects\Avito\README_PROMPTS.md)
- [README_DECISIONS.md](D:\projects\Avito\README_DECISIONS.md)
