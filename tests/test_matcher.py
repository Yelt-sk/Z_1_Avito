from avito_splitter.data_loading import load_microcategories
from avito_splitter.dictionary_matcher import DictionaryMatcher


def test_dictionary_matcher_finds_multiple_categories() -> None:
    microcategories = load_microcategories("data/microcategories.json")
    matcher = DictionaryMatcher(microcategories)
    matches = matcher.match("Отдельно делаем сантехнику, электрику и укладку плитки.")
    mc_ids = {match.mc_id for match in matches}
    assert {101, 102, 104}.issubset(mc_ids)
