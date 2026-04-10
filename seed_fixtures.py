#!/usr/bin/env python3
"""
seed_fixtures.py
One-time script to populate the fixtures table with the correct IPL 2026 schedule.
Run from the project root: python3 seed_fixtures.py
Re-running is safe — uses INSERT OR REPLACE to overwrite stale data.

WARNING: This script ONLY modifies the `fixtures` table.
It NEVER reads from, writes to, or deletes from the `selections` table.
DO NOT add any code here that touches selections — picks data must never be wiped.
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
     'Royal Challengers Bengaluru won by 43 runs', 'Complete'),

    ('149739', 'Match 12',
     'Kolkata Knight Riders', 'KKR', 'Punjab Kings', 'PBKS',
     2026, 4, 6, 19, 30,
     'Eden Gardens', 'Kolkata',
     'Match abandoned - no result', 'Complete'),

    ('149750', 'Match 13',
     'Rajasthan Royals', 'RR', 'Mumbai Indians', 'MI',
     2026, 4, 7, 19, 30,
     'Barsapara Cricket Stadium', 'Guwahati',
     'Rajasthan Royals won by 27 runs (DLS)', 'Complete'),

    ('149761', 'Match 14',
     'Delhi Capitals', 'DC', 'Gujarat Titans', 'GT',
     2026, 4, 8, 19, 30,
     'Arun Jaitley Stadium', 'Delhi',
     'Gujarat Titans won by 1 run', 'Complete'),

    ('149772', 'Match 15',
     'Kolkata Knight Riders', 'KKR', 'Lucknow Super Giants', 'LSG',
     2026, 4, 9, 19, 30,
     'Eden Gardens', 'Kolkata',
     'Lucknow Super Giants won by 3 wickets', 'Complete'),

    # ── Upcoming ─────────────────────────────────────────────────────────────
    ('149783', 'Match 16',
     'Rajasthan Royals', 'RR', 'Royal Challengers Bengaluru', 'RCB',
     2026, 4, 10, 19, 30,
     'Sawai Mansingh Stadium', 'Jaipur',
     'Royal Challengers Bengaluru won by 11 runs', 'Complete'),

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

LOCKED_IDS = {'149618', '149629', '149640', '149651', '149662', '149673'}

# Cricket scores for completed matches
# (match_id): (team1_runs, team1_wkts, team1_overs, team2_runs, team2_wkts, team2_overs)
# team1/team2 match the FIXTURES order above (home team first)
SCORES = {
    '149618': ('203', '4',  '15.4', '201', '9',  '15.4'), # M1  RCB vs SRH
    '149629': ('224', '4',  '19.1', '220', '4',  '19.1'), # M2  MI vs KKR
    '149640': ('128', '2',  '12.1', '127', '-',  '12.1'), # M3  RR vs CSK (DLS)
    '149651': ('165', '7',  '19.1', '162', '6',  '19.1'), # M4  GT vs PBKS
    '149662': ('141', '9',  '17.1', '145', '4',  '17.1'), # M5  LSG vs DC
    '149673': ('141', '10', '20',   '226', '8',  '20'),   # M6  KKR vs SRH (KKR all out)
    '149684': ('209', '5',  '18.4', '210', '5',  '18.4'), # M7  CSK vs PBKS
    '149695': ('164', '4',  '18.1', '162', '6',  '20'),   # M8  DC vs MI
    '149706': ('204', '8',  '20',   '210', '6',  '20'),   # M9  GT vs RR
    '149717': ('156', '9',  '20',   '160', '5',  '19.5'), # M10 SRH vs LSG
    '149728': ('250', '3',  '20',   '207', '10', '19.4'), # M11 RCB vs CSK
    '149739': ('25',  '2',  '3.4',  '-',   '-',  '-'),    # M12 KKR vs PBKS (abandoned)
    '149750': ('150', '3',  '11',   '123', '9',  '11'),   # M13 RR vs MI (DLS)
    '149761': ('209', '8',  '20',   '210', '4',  '20'),   # M14 DC vs GT
    '149772': ('181', '4',  '20',   '182', '7',  '20'),   # M15 KKR vs LSG
    '149783': ('202', '4',  '18',   '201', '8',  '20'),   # M16 RR vs RCB
}

conn = sqlite3.connect(DB)
conn.execute('''CREATE TABLE IF NOT EXISTS fixtures (
    match_id    TEXT PRIMARY KEY,
    desc        TEXT,
    team1       TEXT,  team1_short TEXT,
    team2       TEXT,  team2_short TEXT,
    start_date  INTEGER, start_ist TEXT,
    venue       TEXT,  city TEXT,
    status      TEXT,  state TEXT,
    locked      INTEGER DEFAULT 0,
    team1_runs  TEXT DEFAULT '-', team1_wkts TEXT DEFAULT '-', team1_overs TEXT DEFAULT '-',
    team2_runs  TEXT DEFAULT '-', team2_wkts TEXT DEFAULT '-', team2_overs TEXT DEFAULT '-'
)''')
# Add locked column to existing DBs that predate this migration
try:
    conn.execute('ALTER TABLE fixtures ADD COLUMN locked INTEGER DEFAULT 0')
except Exception:
    pass

inserted = updated = 0
for row in FIXTURES:
    mid, desc, t1, t1s, t2, t2s, y, mo, d, h, mi, venue, city, status, state = row
    start_ms  = epoch_ms(y, mo, d, h, mi)
    start_str = ist_label(y, mo, d, h, mi)
    locked    = 1 if mid in LOCKED_IDS else 0
    existing  = conn.execute('SELECT 1 FROM fixtures WHERE match_id=?', (mid,)).fetchone()
    conn.execute(
        '''INSERT OR REPLACE INTO fixtures
           (match_id, desc, team1, team1_short, team2, team2_short,
            start_date, start_ist, venue, city, status, state, locked,
            team1_runs, team1_wkts, team1_overs,
            team2_runs, team2_wkts, team2_overs)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'-','-','-','-','-','-')''',
        (mid, desc, t1, t1s, t2, t2s, start_ms, start_str, venue, city, status, state, locked),
    )
    if existing:
        updated += 1
    else:
        inserted += 1

conn.commit()

# Apply cricket scores for completed matches
scores_updated = 0
for mid, (t1r, t1w, t1o, t2r, t2w, t2o) in SCORES.items():
    conn.execute(
        '''UPDATE fixtures SET
               team1_runs=?, team1_wkts=?, team1_overs=?,
               team2_runs=?, team2_wkts=?, team2_overs=?
           WHERE match_id=?''',
        (t1r, t1w, t1o, t2r, t2w, t2o, mid),
    )
    scores_updated += 1
conn.commit()
conn.close()

print(f'✓ fixtures seeded — {inserted} inserted, {updated} replaced, {scores_updated} scores set\n')
print(f"  {'ID':<10} {'Match':<10} {'Teams':<22} {'Date & Time':<28} {'State':<10} Result")
print('  ' + '-' * 105)
for row in FIXTURES:
    mid, desc, t1, t1s, t2, t2s, y, mo, d, h, mi, venue, city, status, state = row
    teams = f'{t1s} vs {t2s}'
    date  = ist_label(y, mo, d, h, mi)
    result = status[:40] if status else '—'
    print(f'  {mid:<10} {desc:<10} {teams:<22} {date:<28} {state:<10} {result}')
