import csv
import hashlib
from collections import defaultdict
from pathlib import Path

ROOT = Path('.')

def read_rows(path):
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        return list(csv.reader(handle))

def read_dicts(path):
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))

def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def display_num(value):
    raw = value.replace('$', '').replace(',', '').replace('%', '')
    multiplier = 1
    if raw.endswith('T'):
        raw, multiplier = raw[:-1], 1e12
    elif raw.endswith('B'):
        raw, multiplier = raw[:-1], 1e9
    elif raw.endswith('M'):
        raw, multiplier = raw[:-1], 1e6
    elif raw.endswith('K'):
        raw, multiplier = raw[:-1], 1e3
    try:
        return float(raw) * multiplier
    except ValueError:
        return None

def line_ranges(values):
    values = sorted(values)
    if not values:
        return 'none'
    groups = []
    start = previous = values[0]
    for value in values[1:]:
        if value == previous + 1:
            previous = value
        else:
            groups.append(str(start) if start == previous else f'{start}–{previous}')
            start = previous = value
    groups.append(str(start) if start == previous else f'{start}–{previous}')
    return ', '.join(groups)

csv_files = sorted(path for path in ROOT.glob('*.csv') if path.name != 'consolidated_yield_data.csv')
original_names = {path.name for path in csv_files}
inventory = []
shape_issues = []
hashes = defaultdict(list)
for path in csv_files:
    rows = read_rows(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    inventory.append({
        'name': path.name,
        'rows': max(0, len(rows) - 1),
        'columns': len(rows[0]) if rows else 0,
        'bytes': path.stat().st_size,
        'hash': digest,
    })
    hashes[digest].append(path.name)
    widths = [len(row) for row in rows]
    if len(set(widths)) > 1:
        shape_issues.append((path.name, widths))

quarters = [
    'q3_24_prior', 'q4_24_prior', 'q1_25_prior', 'q2_25_prior',
    'q3_25_current', 'q4_25_current', 'q1_26_current', 'q2_26_current'
]
yield_files = ['yield_data.csv', 'yield_data1.csv']
yield_data = {name: read_dicts(ROOT / name) for name in yield_files}
formula_issues = []
range_issues = []
empty_issues = []
duplicate_keys = []

for filename in yield_files:
    seen = {}
    for line, row in enumerate(yield_data[filename], 2):
        symbol = row.get('symbol', '')
        if symbol in seen:
            duplicate_keys.append((filename, line, 'symbol', symbol, seen[symbol]))
        seen[symbol] = line
        for column, value in row.items():
            if value == '':
                empty_issues.append((filename, line, column))

        def formula_issue(column, message, expected):
            formula_issues.append((filename, line, column, row.get(column, ''), message, expected))

        try:
            prior_expected = sum(float(row[column]) for column in quarters[:4]) / 4
            current_expected = sum(float(row[column]) for column in quarters[4:]) / 4
            if abs(float(row['agg_prior']) - prior_expected) > 0.011:
                formula_issue('agg_prior', 'does not equal the mean of the prior four quarters', prior_expected)
            if abs(float(row['agg_current']) - current_expected) > 0.011:
                formula_issue('agg_current', 'does not equal the mean of the current four quarters', current_expected)
            change_expected = float(row['agg_current']) - float(row['agg_prior'])
            if abs(float(row['change_pp']) - change_expected) > 0.011:
                formula_issue('change_pp', 'does not equal agg_current minus agg_prior', change_expected)
            for start, end, percentage in [
                ('price_start_prior_usd', 'price_end_prior_usd', 'price_change_pct_prior'),
                ('price_start_current_usd', 'price_end_current_usd', 'price_change_pct_current'),
            ]:
                expected = (float(row[end]) / float(row[start]) - 1) * 100
                if abs(float(row[percentage]) - expected) > 0.15:
                    formula_issue(percentage, 'does not reconcile to the start/end price', expected)
            market_expected = (float(row['mcap_end_current_usd']) / float(row['mcap_start_prior_usd']) - 1) * 100
            if abs(float(row['mcap_change_pct']) - market_expected) > 0.15:
                formula_issue('mcap_change_pct', 'does not reconcile full-period market-cap change', market_expected)
            risk_expected = float(row['agg_current']) / (float(row['volatility_annualized_current']) / 100)
            if abs(float(row['risk_adjusted_yield']) - risk_expected) > 0.02:
                formula_issue('risk_adjusted_yield', 'does not equal agg_current divided by volatility percentage', risk_expected)
        except (KeyError, ValueError, ZeroDivisionError) as error:
            formula_issues.append((filename, line, 'row', '', f'formula could not be evaluated: {error}', ''))

        for column, low, high in [
            ('is_annualized', 0, 1),
            ('yield_direction_next_q', 0, 1),
            ('rsi_14d', 0, 100),
            ('investment_score', 0, 100),
            ('correlation_btc', -1, 1),
            ('correlation_eth', -1, 1),
        ]:
            value = num(row.get(column))
            if value is None or not low <= value <= high:
                range_issues.append((filename, line, column, row.get(column, ''), f'expected numeric range {low}..{high}'))

first = yield_data['yield_data.csv']
second = yield_data['yield_data1.csv']
changed_by_column = defaultdict(list)
changed_rows = []
changed_cells = 0
for line, (left, right) in enumerate(zip(first, second), 2):
    differences = [column for column in left if left[column] != right[column]]
    if differences:
        changed_rows.append((line, left.get('symbol', ''), differences))
        changed_cells += len(differences)
        for column in differences:
            changed_by_column[column].append(line)

snapshot_issues = []
for path in sorted(ROOT.glob('table-*.csv')):
    rows = read_dicts(path)
    if not rows or len(rows[0]) < 80:
        continue
    row = rows[0]
    symbol = row.get('symbol', '').replace('-USD', '')
    match = next(((line, item) for line, item in enumerate(first, 2) if item.get('symbol') == symbol), None)
    if match is None:
        snapshot_issues.append((path.name, 2, 'symbol', row.get('symbol', ''), 'no matching symbol in yield_data.csv'))
        continue
    yield_line, yield_row = match
    for source_column, yield_column in [
        ('marketCap', 'mcap_end_current_usd'),
        ('regularMarketPrice', 'price_end_current_usd'),
        ('circulatingSupply', 'circulating_supply'),
    ]:
        if source_column not in row or not row[source_column]:
            continue
        source_value = num(row[source_column])
        yield_value = num(yield_row[yield_column])
        if source_value is not None and yield_value is not None:
            tolerance = max(abs(yield_value) * 0.00001, 0.000001)
            if abs(source_value - yield_value) > tolerance:
                snapshot_issues.append((path.name, 2, source_column, row[source_column], f'vs yield_data.csv:{yield_line}:{yield_column}={yield_row[yield_column]}'))

compact_issues = []
compact_file = 'table-1786044192628.csv'
for line, row in enumerate(read_dicts(ROOT / compact_file), 2):
    match = next(((source_line, item) for source_line, item in enumerate(first, 2) if item.get('symbol') == row['Asset']), None)
    if match is None:
        continue
    yield_line, yield_row = match
    for compact_column, yield_column in [
        ('Yield', 'agg_current'),
        ('Volatility', 'volatility_annualized_current'),
        ('Sharpe', 'sharpe_ratio_current'),
        ('Score', 'investment_score'),
    ]:
        source_value = display_num(row[compact_column])
        yield_value = num(yield_row[yield_column])
        if source_value is not None and yield_value is not None and abs(source_value - yield_value) > max(abs(yield_value) * 0.001, 0.01):
            compact_issues.append((compact_file, line, compact_column, row[compact_column], f'vs yield_data.csv:{yield_line}:{yield_column}={yield_row[yield_column]}'))

metadata_issues = [
    ('table-1786042509301.csv', 5, 'Purpose', 'yield_data.csv: 59 rows × 17 columns', 'actual dimensions are 59 data rows × 59 columns'),
]
actual_sizes = {
    'index.html': (ROOT / 'index.html').stat().st_size,
    'styles.css': (ROOT / 'styles.css').stat().st_size,
    'matrix.js': (ROOT / 'matrix.js').stat().st_size,
    'yield_data.csv': (ROOT / 'yield_data.csv').stat().st_size,
    'DATA_DICTIONARY.md': (ROOT / 'DATA_DICTIONARY.md').stat().st_size,
}
claimed_sizes = {'index.html': 2967, 'styles.css': 6693, 'matrix.js': 9731, 'yield_data.csv': 24354, 'DATA_DICTIONARY.md': 5318}
for filename, claimed in claimed_sizes.items():
    if actual_sizes[filename] != claimed:
        metadata_issues.append(('table-1786044273973.csv', 2, 'Size', f'{filename}: claimed {claimed} B', f'actual {actual_sizes[filename]} B'))

compatible_headers = list(first[0].keys())
assert compatible_headers == list(second[0].keys())
consolidated_path = ROOT / 'consolidated_yield_data.csv'
consolidated_headers = compatible_headers + ['source_file', 'source_row']
with consolidated_path.open('w', encoding='utf-8-sig', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=consolidated_headers, lineterminator='\n')
    writer.writeheader()
    for filename in yield_files:
        for line, row in enumerate(yield_data[filename], 2):
            output = dict(row)
            output['source_file'] = filename
            output['source_row'] = str(line)
            writer.writerow(output)

report = [
    '# CSV validation report',
    '',
    'Generated after inventorying every original CSV in the project and semantically validating the compatible yield files, market snapshots, compact summary, and documented metadata claims.',
    '',
    '## Scope and consolidation policy',
    '',
    f'- Original source CSV files reviewed: **{len(csv_files)}** (generated `consolidated_yield_data.csv` is excluded from the source inventory).',
    '- Strictly compatible data files: `yield_data.csv` and `yield_data1.csv`.',
    f'- Consolidated output: `consolidated_yield_data.csv` with **118 data rows** and **61 columns** (59 shared fields plus `source_file` and `source_row`).',
    '- Every original CSV was preserved; no source file was edited, overwritten, renamed, or deleted.',
    '- The two yield sources were appended as separate versions because all 59 matching symbol records differ. Provenance is retained so a canonical version can be chosen later.',
    '',
    '## Inventory',
    '',
    '| File | Data rows | Columns | Bytes | SHA-256 prefix |',
    '|---|---:|---:|---:|---|',
]
for item in inventory:
    report.append(f"| `{item['name']}` | {item['rows']} | {item['columns']} | {item['bytes']} | `{item['hash']}` |")
report += [
    '',
    '## Compatibility groups',
    '',
    '### Consolidated',
    '',
    '- `yield_data.csv` and `yield_data1.csv` have identical 59-column headers and 59 rows each.',
    f'- They are not value-identical: **{len(changed_rows)}/59 rows** differ across **{changed_cells} cells** and **{len(changed_by_column)} columns**.',
    '',
    '### Not consolidated',
    '',
    '- The nine 87/90-column `table-*.csv` market snapshots are one-row exports with heterogeneous headers and column order.',
    '- The small tables were classified by their headers and contents as metadata, feature descriptions, source notes, or a compact summary; their schemas are not compatible with the yield datasets.',
    '',
    '## Exact issues and warnings',
    '',
    '### Stale metadata',
    '',
]
for filename, line, column, value, message in metadata_issues:
    report.append(f'- **`{filename}:{line}:{column}`** — `{value}`; {message}.')
report += ['', '### Duplicate files', '']
for digest, names in hashes.items():
    if len(names) > 1:
        report.append(f'- **`{names[0]}` and `{names[1]}`** are byte-identical (SHA-256 prefix `{digest}`). This is redundant, not a row-value error.')
report += ['', '### Compact summary conflicts', '']
if compact_issues:
    for filename, line, column, value, message in compact_issues:
        report.append(f'- **`{filename}:{line}:{column}`** — `{value}`; {message}.')
else:
    report.append('- None found.')
report += ['', '### Snapshot precision/value discrepancies', '']
if snapshot_issues:
    for filename, line, column, value, message in snapshot_issues:
        report.append(f'- **`{filename}:{line}:{column}`** — `{value}`; {message}. These may be rounding or snapshot-time differences and were not silently corrected.')
else:
    report.append('- None found.')
report += ['', '### Yield-source version conflicts', '']
report.append(f'- **`yield_data.csv:2–60` versus `yield_data1.csv:2–60`** — every matching symbol row differs ({len(changed_rows)}/59 rows; {changed_cells} changed cells).')
report.append('- Changed columns and exact row ranges:')
for column in sorted(changed_by_column):
    report.append(f"  - `{column}` at rows `{line_ranges(changed_by_column[column])}` in both files.")
report += ['', '## Validation results', '']
report.append(f"- Row-width consistency: **{'pass' if not shape_issues else 'issues found'}**.")
report.append(f"- Duplicate symbols in yield files: **{'none' if not duplicate_keys else len(duplicate_keys)}**.")
report.append(f"- Empty cells in yield files: **{'none' if not empty_issues else len(empty_issues)}**.")
report.append(f"- Formula checks: **{'pass' if not formula_issues else str(len(formula_issues) ) + ' issues'}**.")
report.append(f"- Documented range checks: **{'pass' if not range_issues else str(len(range_issues)) + ' issues'}**.")
report += [
    '',
    '## Interpretation notes',
    '',
    '- The yield files are alternative generated snapshots rather than complementary tables. Their conflicts should be resolved before treating the consolidated file as a single canonical dataset.',
    '- The market snapshots cannot be safely unioned with the yield schema without an explicit field mapping and timestamp policy.',
    '- Small price differences found in snapshot comparisons are consistent with rounded values in the yield file; they are documented rather than changed.',
    '- The ATOM summary row contains substantive yield, volatility, and Sharpe conflicts and should be reconciled before use as a view of `yield_data.csv`.',
    '',
]
(ROOT / 'validate.md').write_text('\n'.join(report), encoding='utf-8')

print('created validate.md:', (ROOT / 'validate.md').stat().st_size, 'bytes')
print('created consolidated_yield_data.csv:', consolidated_path.stat().st_size, 'bytes')
print('consolidated rows:', sum(1 for _ in consolidated_path.open(encoding='utf-8-sig')) - 1)
print('consolidated columns:', len(consolidated_headers))
print('original files preserved:', original_names.issubset({path.name for path in ROOT.glob('*.csv')}))
print('compact conflicts:', len(compact_issues))
print('snapshot warnings:', len(snapshot_issues))
print('metadata issues:', len(metadata_issues))
print('formula issues:', len(formula_issues))
print('range issues:', len(range_issues))
