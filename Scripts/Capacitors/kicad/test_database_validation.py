import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import kicad_capacitor_generator as generator


class DatabaseValidationTests(unittest.TestCase):
    def test_e24_range_and_custom_values(self):
        definition = {"series": "E24", "min_value": "1p", "max_value": "100u"}
        values = generator.range_values(definition)
        self.assertEqual(len(values), 193)
        self.assertTrue({"1p", "4p7", "100p", "3n3", "470n", "10u", "100u"} <= values)
        self.assertNotIn("110u", values)
        config = {"presets": {"E24": definition}}
        self.assertEqual(generator.resolve_requested_values(["2u2"], None, config, "E24"), {"2u2"})
        with self.assertRaises(ValueError):
            generator.range_values({**definition, "min_value": "101u"})

    def test_exact_specs_packaging_and_ambiguous_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "parts.sqlite3"
            conn = sqlite3.connect(path)
            conn.execute("CREATE TABLE jlc_components (lcsc INTEGER, mfr TEXT, package TEXT, manufacturer TEXT, attributes TEXT, datasheet TEXT, present INTEGER)")
            attrs = {"Capacitance": "470nF", "Tolerance": "10%", "Temperature Coefficient": "X7R", "Voltage Rating": "50V"}
            def insert(code, mpn="CC0805KKX7R9BB474", package="0805", manufacturer="YAGEO", attributes=None, present=1):
                conn.execute("INSERT INTO jlc_components VALUES (?,?,?,?,?,?,?)", (code, mpn, package, manufacturer, json.dumps(attrs if attributes is None else attributes), "https://example.test/datasheet.pdf", present))
            insert(1)
            insert(2, attributes={})  # Metadata-free duplicate does not validate.
            insert(3, mpn="CC0805KRX7R9BB474", attributes={**attrs, "Voltage Rating": "25V"})
            insert(4, package="0603")
            insert(5, manufacturer="OTHER")
            insert(6, present=0)
            conn.commit()
            series = generator.SeriesConfig("CC0805", "0805", "", "", "", "Yageo", "BASE", "{value}")
            rows = generator.database_parts(path, series, {"470n", "1u"})
            with patch.object(generator.sqlite3, "connect", side_effect=AssertionError("cache hit must not scan SQLite")):
                self.assertEqual(generator.database_parts(path, series, {"470n", "1u"}), rows)
            path.with_name(path.name + ".capacitors.json").write_text("invalid JSON")
            self.assertEqual(generator.database_parts(path, series, {"470n", "1u"}), rows)
            self.assertEqual([(row.mpn, row.lcsc) for row in rows], [("CC0805KKX7R9BB474", "C1")])
            self.assertEqual(rows[0].verification, "lcsc_database")
            insert(7)  # Two fully validated codes are ambiguous.
            conn.commit()
            self.assertEqual(generator.database_parts(path, series, {"470n"}), [])
            conn.close()

    def test_database_parts_rank_without_curated_preferences(self):
        low = generator.PartRow("1u", "105", "LOW", "X7R", "10%", "25V", "lcsc_database")
        high = generator.PartRow("1u", "105", "HIGH", "X7R", "10%", "50V", "lcsc_database")
        self.assertEqual(generator.select_database_parts([low, high])["1u"], high)
        self.assertEqual(generator.select_database_parts([high])["1u"], high)


if __name__ == "__main__":
    unittest.main()
