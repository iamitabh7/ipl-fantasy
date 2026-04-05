#!/usr/bin/env python3
"""
seed_fixtures.py
One-time script to populate the fixtures table with the correct IPL 2026 schedule.
Run from the project root: python3 seed_fixtures.py
Re-running is safe — uses INSERT OR REPLACE to overwrite stale data.
"""
import sqlite3
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
DB  = 'fantasy.db'


def epoch_ms(y, mo, d, h=19, mi=30):
    return int(datetime(y, mo, d, h, mi, tzinfo=IST).timestamp() * 1000)


def ist_label(y, mo, d, h=19, mi=30):
    dt = datetime(y, mo, d, h, mi, tzinfo=IST)
    return dt.strftime('%-d %b · %-I:%M %p IST')


# Columns: match_id, desc,
#          team1, team1_short, team2, team2_short,
#          y, mo, d, h, mi,
#          venue, city,
#          status, state
FIXTURES = [
    # ── Completed ────────────────────────────────────────────────────────────
    ('149618', 'Match 1',
     'Royal Challengers Bengaluru', 'RCB', 'Sunrisers Hyderabad', 'SRH',
     2026, 3, 28, 19, 30,
     'M. Chinnaswamy Stadium', 'Bengaluru',
     'Royal Challengers Bengaluru won by 6 wkts', 'Complete'),

    ('149629', 'Match 2',
     'Mumbai Indians', 'MI', 'Kolkata Knight Riders', 'KKR',
     2026, 3, 29, 19, 30,
     'Wankhede Stadium', 'Mumbai',
     'Mumbai Indians won by 6 wkts', 'Complete'),

    ('149640', 'Match 3',
     'Rajasthan Royals', 'RR', 'Chennai Super Kings', 'CSK',
     2026, 3, 30, 19, 30,
     'Barsapara Cricket Stadium', 'Guwahati',
     'Rajasthan Royals won by 8 wkts', 'Complete'),

    ('149651', 'Match 4',
     'Gujarat Titans', 'GT', 'Punjab Kings', 'PBKS',
     2026, 3, 31, 19, 30,
     'Narendra Modi Stadium', 'Ahmedabad',
     'Punjab Kings won by 3 wkts', 'Complete'),

    ('149662', 'Match 5',
     'Lucknow Super Giants', 'LSG', 'Delhi Capitals', 'DC',
     2026, 4, 1, 19, 30,
     'Ekana Cricket Stadium', 'Lucknow',
     'Delhi Capitals won by 6 wkts', 'Complete'),

    ('149673', 'Match 6',
     'Kolkata Knight Riders', 'KKR', 'Sunrisers Hyderabad', 'SRH',
     2026, 4, 2, 19, 30,
     'Eden Gardens', 'Kolkata',
     'Sunrisers Hyderabad won by 85 runs', 'Complete'),

    ('149684', 'Match 7',
     'Chennai Super Kings', 'CSK', 'Punjab Kings', 'PBKS',
     2026, 4, 3, 19, 30,
     'MA Chidambaram Stadium', 'Chennai',
     'Punjab Kings won by 5 wkts', 'Complete'),

    ('149695', 'Match 8',
     'Delhi Capitals', 'DC', 'Mumbai Indians', 'MI',
     2026, 4, 4, 15, 30,
     'Arun Jaitley Stadium', 'Delhi',
     'Delhi Capitals won by 6 wkts', 'Complete'),

    ('149706', 'Match 9',
     'Gujarat Titans', 'GT', 'Rajasthan Royals', 'RR',
     2026, 4, 4, 19, 30,
     'Narendra Modi Stadium', 'Ahmedabad',
     'Rajasthan Royals won by 6 runs', 'Complete'),

    ('149717', 'Match 10',
     'Sunrisers Hyderabad', 'SRH', 'Lucknow Super Giants', 'LSG',
     2026, 4, 5, 15, 30,
     'Rajiv Gandhi International Cricket Stadium', 'Hyderabad',
     'Lucknow Super Giants won by 5 wkts', 'Complete'),

    ('149728', 'Match 11',
     'Royal Challengers Bengaluru', 'RCB', 'Chennai Super Kings', 'CSK',
     2026, 4, 5, 19, 30,
     'M. Chinnaswamy Stadium', 'Bengaluru',
     'Royal Challengers Bengaluru won by big margin', 'Complete'),

    # ── Upcoming ─────────────────────────────────────────────────────────────
    ('149739', 'Match 12',
     'Kolkata Knight Riders', 'KKR', 'Punjab Kings', 'PBKS',
     2026, 4, 6, 19, 30,
     'Eden Gardens', 'Kolkata',
     '', 'Upcoming'),

    ('149750', 'Match 13',
     'Rajasthan Royals', 'RR', 'Mumbai Indians', 'MI',
     2026, 4, 7, 19, 30,
     'ACA-VDCA Cricket Stadium', 'Guwahati',
     '', 'Upcoming'),

    ('149761', 'Match 14',
     'Delhi Capitals', 'DC', 'Gujarat Titans', 'GT',
     2026, 4, 8, 19, 30,
     'Arun Jaitley Stadium', 'Delhi',
     '', 'Upcoming'),

    ('149772', 'Match 15',
     'Kolkata Knight Riders', 'KKR', 'Lucknow Super Giants', 'LSG',
     2026, 4, 9, 19, 30,
     'Eden Gardens', 'Kolkata',
     '', 'Upcoming'),

    ('149783', 'Match 16',
     'Rajasthan Royals', 'RR', 'Royal Challengers Bengaluru', 'RCB',
     2026, 4, 10, 19, 30,
     'ACA-VDCA Cricket Stadium', 'Guwahati',
     '', 'Upcoming'),

    ('149794', 'Match 17',
     'Punjab Kings', 'PBKS', 'Sunrisers Hyderabad', 'SRH',
     2026, 4, 11, 15, 30,
     'HPCA Stadium', 'Dharamsala',
     '', 'Upcoming'),

    ('149805', 'Match 18',
     'Chennai Super Kings', 'CSK', 'Delhi Capitals', 'DC',
     2026, 4, 12, 15, 30,
     'MA Chidambaram Stadium', 'Chennai',
     '', 'Upcoming'),

    ('149816', 'Match 19',
     'Lucknow Super Giants', 'LSG', 'Gujarat Titans', 'GT',
     2026, 4, 12, 19, 30,
     'Ekana Cricket Stadium', 'Lucknow',
     '', 'Upcoming'),

    ('149827', 'Match 20',
     'Mumbai Indians', 'MI', 'Royal Challengers Bengaluru', 'RCB',
     2026, 4, 13, 19, 30,
     'Wankhede Stadium', 'Mumbai',
     '', 'Upcoming'),
]

conn = sqlite3.connect(DB)
conn.execute('''CREATE TABLE IF NOT EXISTS fixtures (
    match_id    TEXT PRIMARY KEY,
    desc        TEXT,
    team1       TEXT,  team1_short TEXT,
    team2       TEXT,  team2_short TEXT,
    start_date  INTEGER, start_ist TEXT,
    venue       TEXT,  city TEXT,
    status      TEXT,  state TEXT,
    team1_runs  TEXT DEFAULT '-', team1_wkts TEXT DEFAULT '-', team1_overs TEXT DEFAULT '-',
    team2_runs  TEXT DEFAULT '-', team2_wkts TEXT DEFAULT '-', team2_overs TEXT DEFAULT '-'
)''')

inserted = updated = 0
for row in FIXTURES:
    mid, desc, t1, t1s, t2, t2s, y, mo, d, h, mi, venue, city, status, state = row
    start_ms  = epoch_ms(y, mo, d, h, mi)
    start_str = ist_label(y, mo, d, h, mi)
    existing  = conn.execute('SELECT 1 FROM fixtures WHERE match_id=?', (mid,)).fetchone()
    conn.execute(
        '''INSERT OR REPLACE INTO fixtures
           (match_id, desc, team1, team1_short, team2, team2_short,
            start_date, start_ist, venue, city, status, state,
            team1_runs, team1_wkts, team1_overs,
            team2_runs, team2_wkts, team2_overs)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'-','-','-','-','-','-')''',
        (mid, desc, t1, t1s, t2, t2s, start_ms, start_str, venue, city, status, state),
    )
    if existing:
        updated += 1
    else:
        inserted += 1

conn.commit()
conn.close()

print(f'✓ fixtures seeded — {inserted} inserted, {updated} replaced\n')
print(f"  {'ID':<10} {'Match':<10} {'Teams':<22} {'Date & Time':<28} {'State':<10} Result")
print('  ' + '-' * 105)
for row in FIXTURES:
    mid, desc, t1, t1s, t2, t2s, y, mo, d, h, mi, venue, city, status, state = row
    teams = f'{t1s} vs {t2s}'
    date  = ist_label(y, mo, d, h, mi)
    result = status[:40] if status else '—'
    print(f'  {mid:<10} {desc:<10} {teams:<22} {date:<28} {state:<10} {result}')
