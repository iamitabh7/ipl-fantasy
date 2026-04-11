#!/usr/bin/env python3
"""
seed_fixtures.py
Populate (or refresh) the fixtures table with the IPL 2026 schedule.
Re-running is safe — upserts overwrite stale data without touching selections.

Uses PostgreSQL when DATABASE_URL is set (same as api.py), otherwise SQLite.
Run locally:   python3 seed_fixtures.py
Run on Render: set DATABASE_URL first, then python3 seed_fixtures.py
"""
import os
import sys

# Reuse the data and helpers already defined in api.py
# Import carefully — api.py runs _ensure_db() at module level which is fine here.
sys.path.insert(0, os.path.dirname(__file__))
from api import get_db, _seed_fixtures, _FIXTURES, _SCORES, USE_PG

conn = get_db()
_seed_fixtures(conn)
conn.commit()
conn.close()

print(f'\n✓ Fixtures seeded to {"PostgreSQL" if USE_PG else "SQLite"}')
print(f'\n  {"ID":<10} {"Match":<10} {"Teams":<22} {"State":<10} Result')
print('  ' + '-' * 80)
for row in _FIXTURES:
    mid, desc, t1, t1s, t2, t2s, *_, status, state = row
    teams = f'{t1s} vs {t2s}'
    result = status[:35] if status else '—'
    print(f'  {mid:<10} {desc:<10} {teams:<22} {state:<10} {result}')
