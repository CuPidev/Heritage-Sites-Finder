"""Simple TF-IDF indexer for heritage site documents."""

from typing import List, Dict, Any, Optional
import os
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


class HeritageIndexer:
    """A small TF-IDF based indexer for site documents.

    Documents expected format: list[dict] where each dict contains at least
    'id', 'name', and 'description' (description may be empty).
    """

    def __init__(self):
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.doc_ids: List[str] = []
        self.docs: List[Dict[str, Any]] = []
        self.tfidf_matrix = None

    def fit(self, docs: List[Dict[str, Any]]):
        """Fit the TF-IDF model from documents.

        Args:
            docs: list of dicts with keys 'id', 'name', 'description'
        """
        self.docs = docs
        self.doc_ids = [str(d.get("id", i)) for i, d in enumerate(docs)]
        texts = [
            ((d.get("name") or "") + " \n " + (d.get("description") or ""))
            for d in docs
        ]
        self.vectorizer = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), max_features=10000
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search the fitted index for the query and return top_k documents with scores.

        Returns a list of dicts: {'id','name','description','score'}
        """
        if self.vectorizer is None or self.tfidf_matrix is None:
            raise RuntimeError("Index has not been fitted yet")

        q_vec = self.vectorizer.transform([query])
        cosine_similarities = linear_kernel(q_vec, self.tfidf_matrix).flatten()
        top_indices = cosine_similarities.argsort()[::-1][:top_k]
        results = []
        for idx in top_indices:
            results.append(
                {
                    "id": self.doc_ids[idx],
                    "name": self.docs[idx].get("name"),
                    "description": self.docs[idx].get("description"),
                    "score": float(cosine_similarities[idx]),
                }
            )
        return results

    def save(self, path: str):
        """Save the indexer (vectorizer, docs, matrix) to a file using pickle."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        joblib.dump(
            {
                "vectorizer": self.vectorizer,
                "doc_ids": self.doc_ids,
                "docs": self.docs,
                "tfidf_matrix": self.tfidf_matrix,
            },
            path,
        )

    def load(self, path: str):
        """Load previously saved indexer state."""
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        state = joblib.load(path)
        self.vectorizer = state.get("vectorizer")
        self.doc_ids = state.get("doc_ids", [])
        self.docs = state.get("docs", [])
        self.tfidf_matrix = state.get("tfidf_matrix")

    def load_or_build(
        self, index_path: str, docs: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Try to load index from index_path; if missing and docs provided, build and save it."""
        try:
            self.load(index_path)
        except Exception:
            if docs is None:
                raise
            self.fit(docs)
            self.save(index_path)
