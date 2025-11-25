from app.models import LemmaResult


def mock_result(lemma) -> LemmaResult:
    return {
        "results": [
            {"source": "bwb", "lemma": lemma, "pos": "NOUN"},
            {"source": "wbf", "lemma": lemma, "pos": "NOUN"},
        ]
    }


class Aggregator:
    def query_lemma(self, lemma: str) -> LemmaResult:
        return mock_result(lemma)
