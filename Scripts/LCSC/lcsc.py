#!/usr/bin/env python3
"""Cache exact MPN -> LCSC matches and enrich KiCad/Eagle libraries (stdlib only)."""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'Data' / 'LCSC'
CACHE = DATA / 'mpn_to_lcsc.csv'
API = 'https://jlcsearch.tscircuit.com/api/search'
PUBLISHED = 'https://yaqwsx.github.io/jlcparts/data'
FIELDS = ['mpn', 'lcsc', 'package', 'manufacturer', 'source', 'checked_at']
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+')


def norm(value):
    return str(value or '').strip().upper()


def real_mpn(value):
    return bool(value and 'N.M.' not in norm(value) and norm(value) not in {'XXXX', '-', 'DNP'})


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        f.write(content.encode('utf-8'))
    try:
        for attempt in range(6):
            try:
                tmp.replace(path)
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.1 * (attempt + 1))
    finally:
        tmp.unlink(missing_ok=True)


def load_cache(path=CACHE):
    if not Path(path).exists():
        return {}
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    result = {}
    for row in rows:
        key = norm(row['mpn'])
        if not re.fullmatch(r'C[1-9]\d*', row['lcsc']):
            raise ValueError(f'Invalid LCSC code in cache: {row}')
        if key in result and result[key] != row:
            raise ValueError(f'Duplicate cache MPN: {key}')
        result[key] = row
    return result


def save_cache(cache, path=CACHE):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=FIELDS, lineterminator='\n')
    writer.writeheader()
    writer.writerows(cache[k] for k in sorted(cache))
    atomic_write(path, out.getvalue())


def sexpr_nodes(text):
    """Return spans and direct children, preserving source text for minimal edits."""
    stack, roots = [], []
    for token in TOKEN.finditer(text):
        value = token.group()
        if value == '(':
            node = {'start': token.start(), 'atoms': [], 'children': []}
            if stack:
                stack[-1]['children'].append(node)
            else:
                roots.append(node)
            stack.append(node)
        elif value == ')':
            if not stack:
                raise ValueError('Unbalanced KiCad file')
            stack.pop()['end'] = token.end()
        elif stack:
            stack[-1]['atoms'].append(value[1:-1] if value.startswith('"') else value)
    if stack:
        raise ValueError('Unbalanced KiCad file')
    return roots


def kicad_parts(text):
    roots = sexpr_nodes(text)
    if len(roots) != 1 or roots[0]['atoms'][0] != 'kicad_symbol_lib':
        raise ValueError('Expected a KiCad symbol library')
    for node in roots[0]['children']:
        if node['atoms'][0] != 'symbol':
            continue
        props = {c['atoms'][1]: c for c in node['children'] if c['atoms'][0] == 'property'}
        if 'MPN' not in props and re.fullmatch(r'(?:RC|CC)\d{4}[A-Z0-9-]+', node['atoms'][1]):
            # Older RC0402 library encodes the full MPN in the symbol name.
            props['MPN'] = {'atoms': ['property', 'MPN', node['atoms'][1]],
                            'end': props['Value']['end']}
        if 'MPN' in props:
            yield node, props


def apply_kicad(text, cache):
    edits = []
    for node, props in kicad_parts(text):
        row = cache.get(norm(props['MPN']['atoms'][2]))
        if not row:
            continue
        if 'LCSC' in props:
            prop = props['LCSC']
            old = prop['atoms'][2]
            if old and old != row['lcsc']:
                raise ValueError(f'LCSC conflict for {row["mpn"]}: {old} vs {row["lcsc"]}')
            if old:
                continue
            value = text[prop['start']:prop['end']].replace('"LCSC" ""', f'"LCSC" "{row["lcsc"]}"', 1)
            edits.append((prop['start'], prop['end'], value))
        else:
            offset = props['MPN']['end']
            newline = '\r\n' if '\r\n' in text else '\n'
            value = f'{newline}\t\t(property "LCSC" "{row["lcsc"]}" (at 0 -30.48 0) (hide yes) (effects (font (size 1.27 1.27))))'
            edits.append((offset, offset, value))
    for start, end, value in sorted(edits, reverse=True):
        text = text[:start] + value + text[end:]
    return text


def apply_eagle(text, cache):
    ET.fromstring(text)
    def update(match):
        block = match.group()
        element = ET.fromstring(block)
        props = {x.get('name'): x.get('value', '') for x in element.findall('attribute')}
        row = cache.get(norm(props.get('MPN')))
        if not row:
            return block
        if props.get('LCSC'):
            if props['LCSC'] != row['lcsc']:
                raise ValueError(f'LCSC conflict for {row["mpn"]}')
            return block
        new = f'<attribute name="LCSC" value="{row["lcsc"]}"/>'
        if 'LCSC' in props:
            return re.sub(r'<attribute\b(?=[^>]*\bname="LCSC")[^>]*/>', new, block)
        newline = '\r\n' if '\r\n' in text else '\n'
        return block.replace('</technology>', new + newline + '</technology>')
    return re.sub(r'<technology\b[^>]*>.*?</technology>', update, text, flags=re.S)


def inventory(paths):
    parts = {}
    for path in paths:
        text = path.read_text(encoding='utf-8')
        if path.suffix == '.kicad_sym':
            entries = [p['MPN']['atoms'][2] for _, p in kicad_parts(text)]
        else:
            entries = [e.get('value') for e in ET.fromstring(text).iter('attribute') if e.get('name') == 'MPN']
        for mpn in entries:
            if real_mpn(mpn):
                parts.setdefault(norm(mpn), mpn)
    return parts


def request(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json, */*'}), timeout=45)


def search_api(mpn):
    url = API + '?' + urllib.parse.urlencode({'q': mpn, 'limit': 100, 'full': 'true'})
    with request(url) as response:
        data = json.load(response)
    if not isinstance(data, dict) or not isinstance(data.get('components'), list):
        raise ValueError('Unexpected search response; not caching as no match')
    if len(data['components']) >= 100:
        raise ValueError('Search result truncated; requires manual review')
    return data['components']


def database_matches(path, wanted):
    """Scan once rather than once per MPN; never modify the source database."""
    result = {k: [] for k in wanted}
    conn = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
        if 'jlc_components' in tables:
            query = 'SELECT lcsc,mfr,package,manufacturer FROM jlc_components WHERE present=1'
        elif 'v_components' in tables:
            query = 'SELECT lcsc,mfr,package,manufacturer FROM v_components'
        else:
            raise ValueError('Unsupported jlcparts SQLite schema')
        if not wanted:
            conn.execute(query + ' LIMIT 0')
            return result
        for row in conn.execute(query):
            key = norm(row['mfr'])
            if key in result:
                result[key].append(dict(row))
    finally:
        conn.close()
    return result


def select_match(mpn, candidates, source):
    exact = {}
    for c in candidates:
        if norm(c.get('mfr')) != norm(mpn):
            continue
        code = str(c.get('lcsc', ''))
        code = code if code.startswith('C') else 'C' + code
        if not re.fullmatch(r'C[1-9]\d*', code):
            raise ValueError('Invalid LCSC number in search result')
        # These libraries use Yageo RC/CC series; package is encoded in the MPN.
        package = str(c.get('package') or '')
        expected = re.match(r'^(?:RC|CC)(\d{4})', norm(mpn))
        if expected and package and package != expected[1]:
            return None, 'package_mismatch'
        manufacturer = c.get('manufacturer') or ''
        if isinstance(manufacturer, dict):
            manufacturer = manufacturer.get('name', '')
        if expected and manufacturer and 'YAGEO' not in norm(manufacturer):
            return None, 'manufacturer_mismatch'
        exact[code] = dict(mpn=mpn, lcsc=code, package=package, manufacturer=manufacturer,
                           source=source, checked_at=datetime.now(timezone.utc).isoformat())
    if len(exact) == 1:
        return next(iter(exact.values())), 'matched'
    return None, 'ambiguous' if exact else 'no_exact_match'


def download_database(destination):
    seven = shutil.which('7z') or str(Path('C:/Program Files/7-Zip/7z.exe'))
    if not Path(seven).is_file():
        raise ValueError('Install 7-Zip to extract the split archive')
    destination.mkdir(parents=True, exist_ok=True)
    # All volumes come from one run; never mix partial downloads or old snapshots.
    with tempfile.TemporaryDirectory(dir=destination) as staging:
        staging = Path(staging)
        for number in range(0, 10000):
            name = 'cache.zip' if number == 0 else f'cache.z{number:02d}'
            try:
                with request(PUBLISHED + '/' + name) as response, (staging / name).open('wb') as out:
                    print(f'Downloading {name} ({response.headers.get("Content-Length", "?")} bytes)', flush=True)
                    shutil.copyfileobj(response, out)
            except urllib.error.HTTPError as e:
                if e.code == 404 and number > 0:
                    break
                raise
        else:
            raise ValueError('Too many archive volumes')
        subprocess.run([seven, 'x', str(staging / 'cache.zip'), 'cache.sqlite3', f'-o{staging}', '-y'], check=True,
                       stdout=subprocess.DEVNULL)
        extracted = staging / 'cache.sqlite3'
        database_matches(extracted, set())  # Check schema before replacing an existing copy.
        extracted.replace(destination / 'cache.sqlite3')
    print(f'Database: {destination / "cache.sqlite3"}')


def sync(args):
    defaults = (list((ROOT / 'Libraries').rglob('*.kicad_sym'))
                + list((ROOT / 'Libraries').rglob('*.lbr'))
                + list((ROOT / 'Scripts').rglob('*.generated.kicad_sym')))
    paths = sorted(set(args.paths or defaults))
    parts = inventory(paths)
    cache = load_cache(args.cache)
    state_path = args.cache.with_name('search_status.json')
    state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    state = {k: v for k, v in state.items() if k not in cache}
    pending = [k for k in parts if k not in cache and (args.retry_missing or k not in state or state[k]['status'] == 'error')]
    if args.limit is not None:
        pending = pending[:args.limit]
    errors = 0
    if not args.offline:
        results = database_matches(args.database, set(pending)) if args.database else None
        source = 'jlcparts SQLite' if results is not None else API
        for index, key in enumerate(pending):
            try:
                candidates = results[key] if results is not None else search_api(parts[key])
                row, status = select_match(parts[key], candidates, source)
                if row:
                    cache[key] = row
                    save_cache(cache, args.cache)
                    state.pop(key, None)
                else:
                    state[key] = {'status': status, 'source': source, 'checked_at': datetime.now(timezone.utc).isoformat(),
                                  'candidates': [{f: c.get(f, '') for f in ['lcsc', 'mfr', 'package', 'manufacturer']}
                                                 for c in candidates if norm(c.get('mfr')) == key]}
            except (OSError, ValueError) as e:
                errors += 1
                status = 'error'
                state[key] = {'status': status, 'message': str(e)}
            atomic_write(state_path, json.dumps(state, indent=2, sort_keys=True) + '\n')
            print(f'{index+1}/{len(pending)} {parts[key]}: {status}', flush=True)
            if errors >= 3:
                print('Stopping after three request errors; rerun to retry.')
                break
            if results is None:
                time.sleep(0.5)
    edits = []
    for path in paths:
        original = path.read_bytes().decode('utf-8')
        updated = (apply_kicad if path.suffix == '.kicad_sym' else apply_eagle)(original, cache)
        if updated != original:
            edits.append((path, updated))
    for path, updated in edits:
        if args.apply:
            atomic_write(path, updated)
    matched = sum(k in cache for k in parts)
    print(f'{matched}/{len(parts)} unique MPNs mapped; {len(parts)-matched} unresolved. '
          f'{len(edits)} libraries {"updated" if args.apply else "would change (use --apply)"}.')
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    dl = commands.add_parser('download', help='Download the public jlcparts snapshot; no API key')
    dl.add_argument('--destination', type=Path, default=DATA / 'jlcparts')
    p = commands.add_parser('sync', help='Search new MPNs, cache results, optionally apply LCSC fields')
    p.add_argument('paths', nargs='*', type=Path)
    p.add_argument('--cache', type=Path, default=CACHE)
    p.add_argument('--database', type=Path, help='Use an extracted jlcparts cache.sqlite3 instead of the API')
    p.add_argument('--offline', action='store_true', help='Apply cached mappings only; perform no searches')
    p.add_argument('--retry-missing', action='store_true', help='Retry previous no-match/ambiguous results')
    p.add_argument('--apply', action='store_true', help='Write LCSC fields to libraries')
    p.add_argument('--limit', type=int, help='Maximum number of new searches this run')
    args = parser.parse_args()
    if args.command == 'sync' and args.limit is not None and args.limit < 0:
        parser.error('--limit must be zero or greater')
    try:
        if args.command == 'download':
            download_database(args.destination)
            return 0
        return sync(args)
    except (OSError, ValueError, sqlite3.Error, subprocess.CalledProcessError) as e:
        parser.exit(1, f'Error: {e}\n')


if __name__ == '__main__':
    raise SystemExit(main())
