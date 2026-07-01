"""Tests for bring-your-own-reference material (B19).

Covers the reference store (add/list/delete, text extraction, document building),
the exclude_source_type retrieval filter, and that references are indexed as a distinct
'reference' source separable from canon lore.
"""
import tempfile
import unittest
from pathlib import Path

from libriscribe.services import reference_service
from libriscribe.retrieval.models import RetrievalChunk
from libriscribe.retrieval.keyword_index import KeywordIndex


def _chunk(cid, text, source_type):
    return RetrievalChunk(chunk_id=cid, document_id=f"d-{cid}", project_name="t", text=text,
                          source_type=source_type, chunk_index=0, hash=cid)


class ReferenceStoreTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_add_list_delete_txt(self):
        entry = reference_service.add_reference(self.dir, "bible.txt", b"The empire spans three seas.")
        self.assertEqual(entry["filename"], "bible.txt")
        self.assertGreater(entry["char_count"], 0)
        self.assertEqual(len(reference_service.list_references(self.dir)), 1)

        self.assertTrue(reference_service.delete_reference(self.dir, entry["id"]))
        self.assertEqual(reference_service.list_references(self.dir), [])
        self.assertFalse(reference_service.delete_reference(self.dir, entry["id"]))

    def test_markdown_extracted_as_text(self):
        entry = reference_service.add_reference(self.dir, "style.md", b"# Style\n\nWrite in present tense.")
        self.assertIn("present tense", reference_service._read_text(self.dir, entry["id"]))

    def test_empty_file_rejected(self):
        with self.assertRaises(ValueError):
            reference_service.add_reference(self.dir, "empty.txt", b"   ")

    def test_unsupported_extension_rejected(self):
        with self.assertRaises(ValueError):
            reference_service.extract_text("archive.zip", b"\x00\x01binary")

    def test_build_reference_documents_marks_source_type(self):
        reference_service.add_reference(self.dir, "notes.txt", b"Dragons hoard starlight, not gold.")
        docs = reference_service.build_reference_documents(self.dir)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].source_type, "reference")
        self.assertTrue(docs[0].document_id.startswith("reference::"))
        self.assertIn("starlight", docs[0].text)

    def test_reupload_same_name_replaces(self):
        reference_service.add_reference(self.dir, "a.txt", b"first version text here")
        reference_service.add_reference(self.dir, "a.txt", b"second version text here")
        refs = reference_service.list_references(self.dir)
        self.assertEqual(len(refs), 1)  # replaced, not duplicated


class ExcludeSourceTypeFilterTests(unittest.TestCase):
    def setUp(self):
        self.idx = KeywordIndex(Path(tempfile.mkdtemp()))
        self.idx.build([
            _chunk("c1", "the dragon guards the northern keep", "lore"),
            _chunk("c2", "the dragon in the reference manual is described in detail", "reference"),
        ])

    def test_exclude_reference_keeps_canon_only(self):
        results = self.idx.search("dragon", top_k=10, filters={"exclude_source_type": ["reference"]})
        types = {r.source_type for r in results}
        self.assertIn("lore", types)
        self.assertNotIn("reference", types)

    def test_source_type_filter_selects_reference_only(self):
        results = self.idx.search("dragon", top_k=10, filters={"source_type": "reference"})
        self.assertTrue(results)
        self.assertTrue(all(r.source_type == "reference" for r in results))


if __name__ == "__main__":
    unittest.main()
