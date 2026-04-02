# README_PROMPTS

## Prompt contract для verifier
Verifier получает JSON с:
- задачей;
- policy;
- исходным объявлением;
- shortlist-кандидатами;
- feature summary для каждого кандидата.

Модель обязана вернуть только JSON-массив объектов:

```json
[
  {
    "mcId": 101,
    "isStandalone": true,
    "confidence": 0.91,
    "rationale": "The text says the service is done separately."
  }
]
```

Ключевые ограничения:
- если случай неоднозначный, `isStandalone = false`;
- никаких markdown-блоков;
- никакого дополнительного текста вне JSON.

## Prompt contract для draft generation
Generator получает:
- исходное объявление;
- target microcategory;
- принятую rationale.

Модель обязана вернуть:

```json
{
  "mcId": 101,
  "mcTitle": "Сантехника",
  "text": "Выполняем сантехнические работы отдельно: ..."
}
```

## Почему prompts сделаны JSON-first
- проще парсить и валидировать;
- меньше chance на “болтливый” ответ модели;
- удобно хранить сырые `rawText` в debug.

## Retry/fallback стратегия
- сначала обычный запрос;
- если JSON сломан, используется извлечение первого JSON-фрагмента;
- если ответ неполный, недостающие решения добираются rule fallback;
- если draft пустой, используется простой fallback-текст.
