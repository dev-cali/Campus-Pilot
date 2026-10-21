"""Offline tests: no database, API keys, or third-party packages required."""

import re
import unittest
from pathlib import Path

from ai.document_processing import normalize_document_text, split_document_text


class DocumentProcessingTests(unittest.TestCase):
    def setUp(self):
        self.metadata = {
            "document_id": 17,
            "page_no": 2,
            "source_reference": "https://example.invalid/fictional-guide",
            "title": "Fictional Enrollment Guide",
            "version": "test-v1",
        }
        fixture = Path(__file__).parent / "fixtures" / "sample_university_document.txt"
        self.sample = fixture.read_text(encoding="utf-8")

    def split(self, text, **overrides):
        options = {**self.metadata, **overrides}
        return split_document_text(text, **options)

    def assert_complete(self, original, chunks, limit):
        normalized = normalize_document_text(original)
        previous_end = 0
        rebuilt = ""
        for index, chunk in enumerate(chunks):
            self.assertEqual(chunk.chunk_index, index)
            self.assertGreaterEqual(chunk.start_char, previous_end)
            gap = normalized[previous_end:chunk.start_char]
            # The only omitted characters may be boundary whitespace.
            self.assertTrue(not gap or gap.isspace())
            self.assertEqual(chunk.chunk_text,
                             normalized[chunk.start_char:chunk.end_char])
            self.assertTrue(chunk.chunk_text.strip())
            self.assertEqual(chunk.chunk_text, chunk.chunk_text.strip())
            self.assertLessEqual(len(chunk.chunk_text), limit)
            rebuilt += gap + chunk.chunk_text
            previous_end = chunk.end_char
        tail = normalized[previous_end:]
        self.assertTrue(not tail or tail.isspace())
        self.assertEqual(rebuilt + tail, normalized)
        self.assertEqual("".join(re.findall(r"\S", normalized)),
                         "".join(re.findall(r"\S", "".join(c.chunk_text for c in chunks))))

    def test_normal_document(self):
        chunks = self.split(self.sample, max_chars=140)
        self.assertGreater(len(chunks), 1)
        self.assert_complete(self.sample, chunks, 140)

    def test_normalization_preserves_paragraphs(self):
        text = "  First\t paragraph.\r\nWrapped line.\r\n \t\r\n\r\nSecond   paragraph.  "
        expected = "First paragraph. Wrapped line.\n\nSecond paragraph."
        self.assertEqual(normalize_document_text(text), expected)
        self.assertEqual(self.split(text)[0].chunk_text, expected)

    def test_normalization_is_idempotent(self):
        once = normalize_document_text(self.sample)
        self.assertEqual(normalize_document_text(once), once)

    def test_empty_text(self):
        for text in ("", " \t\r\n", "\u00a0\n\n"):
            with self.subTest(text=text):
                self.assertEqual(self.split(text), [])

    def test_incorrect_text_types(self):
        for value in (None, b"binary", 12, [], {}, True):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    self.split(value)

    def test_invalid_integer_types(self):
        for field in ("document_id", "page_no", "max_chars"):
            for value in (True, 1.5, "2", None):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(TypeError):
                        self.split("Example", **{field: value})

    def test_nonpositive_integers(self):
        for field in ("document_id", "page_no", "max_chars"):
            for value in (0, -1):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        self.split("Example", **{field: value})

    def test_invalid_text_metadata(self):
        for field in ("source_reference", "title", "version"):
            with self.subTest(field=field):
                with self.assertRaises(TypeError):
                    self.split("Example", **{field: 3})
                with self.assertRaises(ValueError):
                    self.split("Example", **{field: " \t"})
        for field in ("source_reference", "title"):
            with self.assertRaises(TypeError):
                self.split("Example", **{field: None})

    def test_missing_required_metadata(self):
        for field in ("document_id", "page_no", "source_reference", "title"):
            options = dict(self.metadata)
            del options[field]
            with self.subTest(field=field):
                with self.assertRaises(TypeError):
                    split_document_text("Example", **options)

    def test_empty_text_still_validates_metadata(self):
        with self.assertRaises(ValueError):
            self.split("", page_no=0)

    def test_metadata_preserved_on_every_chunk(self):
        chunks = self.split(self.sample, max_chars=80)
        for chunk in chunks:
            for name, value in self.metadata.items():
                self.assertEqual(getattr(chunk, name), value)
        self.assertEqual(self.split("Text", title=" Exact title ")[0].title,
                         " Exact title ")

    def test_optional_version(self):
        options = dict(self.metadata)
        del options["version"]
        self.assertIsNone(split_document_text("Example", **options)[0].version)

    def test_prefers_paragraph_boundary(self):
        text = "First paragraph.\n\nSecond paragraph is longer."
        chunks = self.split(text, max_chars=25)
        self.assertEqual(chunks[0].chunk_text, "First paragraph.")
        self.assert_complete(text, chunks, 25)

    def test_long_paragraph_prefers_word_boundary(self):
        text = "alpha beta gamma delta"
        chunks = self.split(text, max_chars=12)
        self.assertEqual([c.chunk_text for c in chunks], ["alpha beta", "gamma delta"])
        self.assert_complete(text, chunks, 12)

    def test_oversized_word(self):
        text = "ABCDEFGHIJKLM"
        chunks = self.split(text, max_chars=5)
        self.assertEqual([c.chunk_text for c in chunks], ["ABCDE", "FGHIJ", "KLM"])
        self.assert_complete(text, chunks, 5)

    def test_unicode_text(self):
        text = "Kumusta! Café — 学生 🎓\n\nMga mag-aaral: naïve, e\u0301."
        self.assert_complete(text, self.split(text, max_chars=9), 9)

    def test_limits_and_completeness(self):
        text = "A\n\nBC DEFGHIJKLMNOP\tQ.\nLast line!"
        for limit in range(1, len(normalize_document_text(text)) + 2):
            with self.subTest(limit=limit):
                self.assert_complete(text, self.split(text, max_chars=limit), limit)

    def test_exact_limit(self):
        self.assertEqual([c.chunk_text for c in self.split("abcde fghij", max_chars=5)],
                         ["abcde", "fghij"])

    def test_deterministic_order(self):
        self.assertEqual(self.split(self.sample, max_chars=100),
                         self.split(self.sample, max_chars=100))


if __name__ == "__main__":
    unittest.main()