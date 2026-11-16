import unittest

from triage_knowledge.contracts import (
    KnowledgeError, TableSource, canonical_bytes, sha256, strict_json,
)


class SourceContractTests(unittest.TestCase):
    def test_table_source_rejects_malformed_csv_shapes(self):
        for raw in (
            b"a,a\r\nx,y\r\n",
            b"a,b\r\nx\r\n",
            b"a,b\r\nx,y,z\r\n",
            b"a,b\r\n",
        ):
            with self.subTest(raw=raw), self.assertRaises(KnowledgeError):
                TableSource.from_bytes(raw, source_id="findings", kind="finding_input")

    def test_strict_json_and_canonical_bytes(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '{"a":1.0}', '{"a":'):
            with self.subTest(raw=raw), self.assertRaises(KnowledgeError):
                strict_json(raw)
        expected = b'{"a":1,"b":2}'
        self.assertEqual(expected, canonical_bytes({"b": 2, "a": 1}))
        self.assertEqual(
            "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777",
            sha256(expected),
        )
        self.assertEqual(b'{"check":"\xe2\x9c\x93"}', canonical_bytes({"check": "\u2713"}))


if __name__ == "__main__":
    unittest.main()
