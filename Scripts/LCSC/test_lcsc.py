import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from argparse import Namespace

import lcsc


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.mpn = 'RC0603FR-0710KL'
        self.candidate = {'mfr': self.mpn, 'lcsc': 98220, 'package': '0603', 'manufacturer': 'YAGEO'}
        self.row, _ = lcsc.select_match(self.mpn, [self.candidate], 'test')
        self.cache = {self.mpn: self.row}
        self.library = '(kicad_symbol_lib (version 20251024) (symbol "part" (property "MPN" "RC0603FR-0710KL") (property "Value" "10K") (symbol "part_0_1" (text "quoted (text)"))))'

    def test_only_exact_unambiguous_matches(self):
        self.assertEqual(lcsc.select_match(self.mpn, [dict(self.candidate, mfr=self.mpn+'X')], 'test')[1], 'no_exact_match')
        self.assertEqual(lcsc.select_match(self.mpn, [self.candidate, dict(self.candidate, lcsc=123)], 'test')[1], 'ambiguous')
        self.assertEqual(lcsc.select_match(self.mpn, [dict(self.candidate, package='0402')], 'test')[1], 'package_mismatch')
        self.assertEqual(lcsc.select_match(self.mpn, [dict(self.candidate, manufacturer='Other')], 'test')[1], 'manufacturer_mismatch')

    def test_kicad_minimal_idempotent_and_conflict(self):
        updated = lcsc.apply_kicad(self.library, self.cache)
        self.assertEqual(updated.count('"LCSC"'), 1)
        self.assertEqual(lcsc.apply_kicad(updated, self.cache), updated)
        self.assertEqual(len(lcsc.sexpr_nodes(updated)), 1)
        with self.assertRaises(ValueError):
            lcsc.apply_kicad(updated.replace('C98220', 'C123'), self.cache)

    def test_eagle_xml_and_idempotence(self):
        original = '<?xml version="1.0"?><eagle><technology name=""><attribute name="MPN" value="RC0603FR-0710KL"/></technology></eagle>'
        updated = lcsc.apply_eagle(original, self.cache)
        self.assertIn('value="C98220"', updated)
        self.assertEqual(lcsc.apply_eagle(updated, self.cache), updated)

    def test_offline_sqlite_schemas(self):
        for table in ['jlc_components', 'v_components']:
            with self.subTest(table=table), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'db.sqlite3'
                conn = sqlite3.connect(path)
                conn.execute(f'CREATE TABLE {table} (lcsc INTEGER,mfr TEXT,package TEXT,manufacturer TEXT,present INTEGER)')
                conn.execute(f'INSERT INTO {table} VALUES (98220,?,?,?,1)', (self.mpn, '0603', 'YAGEO'))
                conn.commit()
                conn.close()
                result = lcsc.database_matches(path, {self.mpn})
                self.assertEqual(result[self.mpn][0]['lcsc'], 98220)

    def test_cache_reuse_and_retryable_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            library = directory / 'part.kicad_sym'
            library.write_text(self.library)
            args = Namespace(paths=[library], cache=directory/'cache.csv', retry_missing=False,
                             limit=None, offline=False, database=None, apply=True)
            with patch.object(lcsc, 'search_api', side_effect=OSError('timeout')), patch.object(lcsc.time, 'sleep'):
                self.assertEqual(lcsc.sync(args), 1)
            with patch.object(lcsc, 'search_api', return_value=[self.candidate]) as search, patch.object(lcsc.time, 'sleep'):
                self.assertEqual(lcsc.sync(args), 0)
                search.assert_called_once()
            with patch.object(lcsc, 'search_api', side_effect=AssertionError('cache should prevent network')):
                self.assertEqual(lcsc.sync(args), 0)
            self.assertEqual(lcsc.load_cache(args.cache)[self.mpn]['lcsc'], 'C98220')

    def test_legacy_symbol_name(self):
        library = '(kicad_symbol_lib (symbol "RC0603FR-0710KL" (property "Value" "10K")))'
        self.assertIn('"C98220"', lcsc.apply_kicad(library, self.cache))


if __name__ == '__main__':
    unittest.main()
