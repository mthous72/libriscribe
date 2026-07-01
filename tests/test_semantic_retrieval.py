"""Tests for semantic / embeddings retrieval (B17).

Uses a deterministic FakeEmbedder (bag-of-words over a fixed vocabulary) so cosine
similarity tracks word overlap — no network or model needed. Covers the SemanticIndex
(ranking, filters, save/load, signature), the hybrid merge, the embedder factory, and the
IndexManager semantic wiring (build when configured, cleanup/fallback otherwise).
"""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from libriscribe.retrieval.models import RetrievalChunk, RetrievalConfig, RetrievalMode, SearchResult
from libriscribe.retrieval.semantic_index import SemanticIndex
from libriscribe.retrieval.search_service import _merge_hybrid
from libriscribe.retrieval.embedder import build_embedder, OpenAICompatibleEmbedder


VOCAB = ["dragon", "castle", "river", "magic", "king", "forest", "sea", "battle"]


class FakeEmbedder:
    signature = "fake|v1"

    def embed(self, texts):
        out = []
        for t in texts:
            tl = (t or "").lower()
            out.append([float(tl.count(w)) for w in VOCAB])
        return out


class OtherEmbedder(FakeEmbedder):
    signature = "fake|v2"  # different embedding space


def _chunk(cid, text, source_type="lore", **kw):
    return RetrievalChunk(
        chunk_id=cid, document_id=f"doc-{cid}", project_name="t", text=text,
        source_type=source_type, chunk_index=0, hash=cid, **kw,
    )


CHUNKS = [
    _chunk("c1", "The dragon guards the castle on the hill."),
    _chunk("c2", "A river runs through the forest to the sea.", source_type="prose"),
    _chunk("c3", "The king studies ancient magic before the battle."),
]


class SemanticIndexTests(unittest.TestCase):
    def setUp(self):
        self.idx = SemanticIndex()
        self.idx.build(CHUNKS, FakeEmbedder())

    def test_ranks_semantically_related_chunk_first(self):
        results = self.idx.search("dragon castle", FakeEmbedder(), top_k=3)
        self.assertTrue(results)
        self.assertEqual(results[0].chunk_id, "c1")
        self.assertEqual(results[0].score_breakdown.get("semantic_score"), results[0].score)

    def test_magic_query_matches_king_chunk(self):
        results = self.idx.search("magic battle king", FakeEmbedder(), top_k=1)
        self.assertEqual(results[0].chunk_id, "c3")

    def test_filters_by_source_type(self):
        results = self.idx.search("river sea forest", FakeEmbedder(), top_k=5,
                                  filters={"source_type": "prose"})
        self.assertTrue(all(r.source_type == "prose" for r in results))
        self.assertEqual(results[0].chunk_id, "c2")

    def test_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "semantic_index.json"
            self.idx.save_to_file(path)
            fresh = SemanticIndex()
            fresh.load_from_file(path)
            self.assertEqual(fresh.signature, "fake|v1")
            self.assertEqual(fresh.search("dragon castle", FakeEmbedder(), top_k=1)[0].chunk_id, "c1")

    def test_is_ready_signature_mismatch(self):
        self.assertTrue(self.idx.is_ready(FakeEmbedder()))
        self.assertFalse(self.idx.is_ready(OtherEmbedder()))   # different embedding space
        self.assertEqual(self.idx.search("dragon", OtherEmbedder(), top_k=1), [])  # -> caller falls back

    def test_empty_index_returns_empty(self):
        self.assertEqual(SemanticIndex().search("dragon", FakeEmbedder(), top_k=3), [])


class HybridMergeTests(unittest.TestCase):
    def _r(self, cid, score):
        return SearchResult(chunk_id=cid, document_id=f"d-{cid}", text=cid, source_type="lore", score=score)

    def test_merges_dedupes_and_reranks(self):
        kw = [self._r("a", 10.0), self._r("b", 2.0)]
        sem = [self._r("b", 0.9), self._r("c", 0.8)]
        merged = _merge_hybrid(kw, sem, top_k=5)
        ids = [r.chunk_id for r in merged]
        self.assertEqual(set(ids), {"a", "b", "c"})          # union, deduped
        self.assertEqual(len(ids), 3)
        # 'b' appears in both lists (normalized: keyword 0.0 + semantic 1.0 = 1.0) and should
        # outrank 'a' (keyword 1.0 + semantic 0.0 = 1.0)? tie -> both 1.0; 'c' is lowest.
        self.assertEqual(ids[-1], "c")
        for r in merged:
            self.assertIn("keyword_norm", r.score_breakdown)
            self.assertIn("semantic_norm", r.score_breakdown)

    def test_empty_inputs(self):
        self.assertEqual(_merge_hybrid([], [], top_k=5), [])


class EmbedderFactoryTests(unittest.TestCase):
    def test_none_for_legacy_or_unconfigured(self):
        self.assertIsNone(build_embedder(SimpleNamespace(retrieval_embedding_provider="sentence-transformers")))
        self.assertIsNone(build_embedder(SimpleNamespace(retrieval_embedding_provider="openai", openai_api_key="")))

    def test_openai_cloud(self):
        emb = build_embedder(SimpleNamespace(
            retrieval_embedding_provider="openai", openai_api_key="sk-x",
            openai_embedding_model="text-embedding-3-small"))
        self.assertIsInstance(emb, OpenAICompatibleEmbedder)
        self.assertEqual(emb.base_url, "")           # cloud -> default endpoint
        self.assertIn("text-embedding-3-small", emb.signature)

    def test_local_uses_base_url_and_normalizes(self):
        emb = build_embedder(SimpleNamespace(
            retrieval_embedding_provider="local", local_base_url="http://localhost:1234",
            local_api_key="", retrieval_embedding_model="", local_model="nomic-embed-text"))
        self.assertIsInstance(emb, OpenAICompatibleEmbedder)
        self.assertTrue(emb.base_url.endswith("/v1"))   # normalize_openai_base_url appended /v1


class IndexManagerSemanticWiringTests(unittest.TestCase):
    def _im(self, mode, embedder):
        from libriscribe.retrieval.index_manager import IndexManager
        from libriscribe.knowledge_base import ProjectKnowledgeBase
        d = Path(tempfile.mkdtemp())
        kb = ProjectKnowledgeBase(project_name="t")
        cfg = RetrievalConfig(enabled=True, mode=mode)
        im = IndexManager(kb, d, cfg, embedder=embedder)
        im.retrieval_dir.mkdir(parents=True, exist_ok=True)
        return im

    def test_builds_semantic_when_configured(self):
        im = self._im(RetrievalMode.SEMANTIC, FakeEmbedder())
        im._rebuild_semantic(CHUNKS)
        self.assertTrue(im.semantic_index_file.exists())
        self.assertTrue(im.semantic_index.is_ready(FakeEmbedder()))

    def test_no_semantic_file_in_keyword_mode(self):
        im = self._im(RetrievalMode.KEYWORD, FakeEmbedder())
        im._rebuild_semantic(CHUNKS)
        self.assertFalse(im.semantic_index_file.exists())

    def test_embed_failure_cleans_up_and_falls_back(self):
        class Boom:
            signature = "boom"
            def embed(self, texts):
                raise RuntimeError("no embedder server")
        im = self._im(RetrievalMode.SEMANTIC, Boom())
        # pre-existing stale file should be removed on failed rebuild
        im.semantic_index_file.write_text("{}", encoding="utf-8")
        im._rebuild_semantic(CHUNKS)
        self.assertFalse(im.semantic_index_file.exists())
        self.assertFalse(im.semantic_index.is_ready(Boom()))


if __name__ == "__main__":
    unittest.main()
