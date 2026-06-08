from __future__ import annotations

import unittest

from scripts.kiroku_core.findings import Finding, ValidationResult


class FindingTest(unittest.TestCase):
    def test_entity_ids_are_unique_and_sorted(self) -> None:
        finding = Finding(
            code="EXAMPLE",
            severity="warning",
            path="$.records",
            message="Example finding.",
            entity_ids=("rec_z", "rec_a", "rec_z"),
        )
        self.assertEqual(finding.entity_ids, ("rec_a", "rec_z"))
        self.assertEqual(
            finding.to_dict()["entity_ids"],
            ["rec_a", "rec_z"],
        )

    def test_invalid_finding_fields_are_rejected(self) -> None:
        cases = [
            {"code": "", "severity": "error", "path": "$", "message": "x"},
            {
                "code": "lowercase",
                "severity": "error",
                "path": "$",
                "message": "x",
            },
            {"code": "X", "severity": "fatal", "path": "$", "message": "x"},
            {"code": "X", "severity": "error", "path": "", "message": "x"},
            {"code": "X", "severity": "error", "path": "$", "message": ""},
            {
                "code": "X",
                "severity": "error",
                "path": "$",
                "message": "x",
                "entity_ids": ("rec_a", 1),
            },
        ]
        for fields in cases:
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    Finding(**fields)


class ValidationResultTest(unittest.TestCase):
    def test_findings_are_deterministically_ordered(self) -> None:
        findings = [
            Finding("B", "info", "$.z", "third"),
            Finding("B", "error", "$.z", "second"),
            Finding("A", "error", "$.a", "first"),
        ]
        result = ValidationResult.from_findings(reversed(findings))

        self.assertEqual(
            [(item.severity, item.path, item.code) for item in result.findings],
            [
                ("error", "$.a", "A"),
                ("error", "$.z", "B"),
                ("info", "$.z", "B"),
            ],
        )
        self.assertFalse(result.ok)
        self.assertEqual(len(result.errors), 2)
        self.assertEqual(result.to_dict()["ok"], False)

    def test_warnings_and_info_do_not_make_result_fail(self) -> None:
        result = ValidationResult.from_findings(
            [
                Finding("W", "warning", "$", "warning"),
                Finding("I", "info", "$", "info"),
            ]
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.errors, ())


if __name__ == "__main__":
    unittest.main()
