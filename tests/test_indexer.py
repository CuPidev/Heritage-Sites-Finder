from src.indexer import HeritageIndexer


def test_indexer_basic_search():
    docs = [
        {"id": "a", "name": "Ancient Temple", "description": "stone temple ruins and columns"},
        {"id": "b", "name": "Modern Museum", "description": "contemporary art and exhibitions"},
        {"id": "c", "name": "Coastal Park", "description": "sea cliffs and coastal biodiversity"},
    ]

    idx = HeritageIndexer()
    idx.fit(docs)
    results = idx.search("temple ruins", top_k=2)
    assert results, "Expected non-empty results"
    # top result should be the Ancient Temple (id a)
    assert results[0]["id"] == "a"
    assert results[0]["score"] > 0
