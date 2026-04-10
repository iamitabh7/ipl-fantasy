from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import urllib.request
import json
import os
import sqlite3
import time
import re
from datetime import datetime, timezone, timedelta

# Disk cache directory — persists across restarts and survives in-memory eviction
os.makedirs('cache', exist_ok=True)

app = Flask(__name__)
CORS(app)

ESPN_LEAGUE_ID = '8048'
IST = timezone(timedelta(hours=5, minutes=30))

# Mapping: Cricbuzz match_id → ESPN match_id
ESPN_MATCH_IDS = {
    '149618': '1527674',  # Match 1  RCB vs SRH
    '149629': '1527675',  # Match 2  MI vs KKR
    '149640': '1527676',  # Match 3  RR vs CSK
    '149651': '1527677',  # Match 4  GT vs PBKS
    '149662': '1527678',  # Match 5  LSG vs DC
    '149673': '1527679',  # Match 6  KKR vs SRH
    '149684': '1527680',  # Match 7  CSK vs PBKS
    '149695': '1527681',  # Match 8  DC vs MI
    '149706': '1527682',  # Match 9  GT vs RR
    '149717': '1527683',  # Match 10 SRH vs LSG
    '149728': '1527684',  # Match 11 RCB vs CSK
    '149739': '1527685',  # Match 12 KKR vs PBKS
    '149750': '1527686',  # Match 13 RR vs MI
    '149761': '1527687',  # Match 14 DC vs GT
    '149772': '1527688',  # Match 15 KKR vs LSG
    '149783': '1527689',  # Match 16 RR vs RCB
    '149794': '1527690',  # Match 17 PBKS vs SRH
    '149805': '1527691',  # Match 18 CSK vs DC
    '149816': '1527692',  # Match 19 LSG vs GT
    '149827': '1527693',  # Match 20 MI vs RCB
}

ESPN_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json',
}

# Labels for matches tracked by ID (used in season history for DB-sourced matches)
KNOWN_MATCH_LABELS = {
    '149684': 'Match 7 — CSK vs PBKS',
    '149695': 'Match 8 — DC vs MI',
    '149706': 'Match 9 — GT vs RR',
    '149717': 'Match 10 — SRH vs LSG',
    '149728': 'Match 11 — RCB vs CSK',
    '149739': 'Match 12 — KKR vs PBKS',
}

# Matches 1-6: hardcoded in /api/season — picks and scores cannot be changed
LOCKED_MATCH_IDS = {'149618', '149629', '149640', '149651', '149662', '149673'}

def get_db():
    conn = sqlite3.connect('fantasy.db')
    conn.row_factory = sqlite3.Row
    return conn

# Called at module level so gunicorn (which skips __main__) still creates tables
def _ensure_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS fixtures (
        match_id TEXT PRIMARY KEY,
        desc TEXT,
        team1 TEXT, team1_short TEXT,
        team2 TEXT, team2_short TEXT,
        start_date INTEGER, start_ist TEXT,
        venue TEXT, city TEXT,
        status TEXT, state TEXT,
        team1_runs TEXT DEFAULT '-', team1_wkts TEXT DEFAULT '-', team1_overs TEXT DEFAULT '-',
        team2_runs TEXT DEFAULT '-', team2_wkts TEXT DEFAULT '-', team2_overs TEXT DEFAULT '-'
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS selections (
        match_id TEXT PRIMARY KEY, amitabh_players TEXT, amitabh_captain TEXT,
        shivam_players TEXT, shivam_captain TEXT, created_at INTEGER)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS drafts (
        match_id TEXT PRIMARY KEY, first_pick TEXT DEFAULT 'amitabh',
        picks TEXT DEFAULT '[]', amitabh_captain TEXT DEFAULT '',
        shivam_captain TEXT DEFAULT '', is_complete INTEGER DEFAULT 0,
        created_at INTEGER)''')
    # Add team-choice columns (safe to run multiple times — ignored if already exist)
    try:
        conn.execute('ALTER TABLE drafts ADD COLUMN amitabh_team_choice TEXT DEFAULT ""')
    except Exception:
        pass
    try:
        conn.execute('ALTER TABLE drafts ADD COLUMN shivam_team_choice TEXT DEFAULT ""')
    except Exception:
        pass
    # Add locked column to fixtures (safe if already exists)
    try:
        conn.execute('ALTER TABLE fixtures ADD COLUMN locked INTEGER DEFAULT 0')
    except Exception:
        pass
    # Lock matches 1-6 — their data is hardcoded and must not be edited
    conn.execute("""UPDATE fixtures SET locked=1 WHERE match_id IN
        ('149618','149629','149640','149651','149662','149673')""")
    # One-time data entry: match 7 CSK vs PBKS selections
    conn.execute('''INSERT OR IGNORE INTO selections
        (match_id, amitabh_players, amitabh_captain, shivam_players, shivam_captain, created_at)
        VALUES (?, ?, ?, ?, ?, ?)''', (
        '149684',
        json.dumps(['Cooper Connolly', 'Shivam Dube', 'Priyansh Arya', 'Prabhsimran Singh', 'Kartik Sharma']),
        'Cooper Connolly',
        json.dumps(['Sanju Samson', 'Shreyas Iyer', 'Marco Jansen', 'Yuzvendra Chahal', 'Marcus Stoinis']),
        'Sanju Samson',
        1743696000,
    ))
    conn.commit()
    conn.close()

_ensure_db()

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS selections (
            match_id TEXT PRIMARY KEY,
            amitabh_players TEXT,
            amitabh_captain TEXT,
            shivam_players TEXT,
            shivam_captain TEXT,
            created_at INTEGER
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS drafts (
            match_id TEXT PRIMARY KEY,
            first_pick TEXT DEFAULT 'amitabh',
            picks TEXT DEFAULT '[]',
            amitabh_captain TEXT DEFAULT '',
            shivam_captain TEXT DEFAULT '',
            is_complete INTEGER DEFAULT 0,
            created_at INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def get_last_match_info():
    """Last completed match result, used to determine first pick in draft."""
    # Match 6 — KKR vs SRH (update when a new match completes)
    a, s = 198, 283
    winner = 'amitabh' if a > s else 'shivam'
    loser  = 'shivam'  if winner == 'amitabh' else 'amitabh'
    return {
        'last_match_desc': 'Match 6 — KKR vs SRH',
        'last_match_winner': winner,
        'last_match_loser': loser,
        'last_match_amitabh': a,
        'last_match_shivam': s,
    }

_player_cache = {}
_fixtures_cache = {'data': None, 'ts': 0}
_season_cache   = {'data': None, 'ts': 0}
_match_players_cache = {}   # match_id → {'data': ..., 'ts': ...}
CACHE_TTL = 3600  # seconds — refresh at most every hour

# ── Disk cache helpers ────────────────────────────────────────────────────────
def _cache_path(api_path):
    safe = api_path.lstrip('/').replace('/', '_')
    return os.path.join('cache', f'{safe}.json')

def _disk_read(api_path, ttl=CACHE_TTL):
    """Return cached data if it exists and is fresher than ttl seconds, else None."""
    p = _cache_path(api_path)
    try:
        if time.time() - os.path.getmtime(p) < ttl:
            with open(p) as f:
                return json.load(f)
    except Exception:
        pass
    return None

def _disk_write(api_path, data):
    try:
        with open(_cache_path(api_path), 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

def _disk_read_stale(api_path):
    """Return cached data regardless of age (stale fallback when API is down)."""
    try:
        with open(_cache_path(api_path)) as f:
            return json.load(f)
    except Exception:
        return {}

def get_players_cached(match_id):
    if match_id in _player_cache:
        return _player_cache[match_id]
    data = espn_get(match_id)
    m = _parse_espn_match(data)
    if not m:
        return {'players': [], 'team1': '', 'team1_short': '', 'team1_players': [],
                'team2': '', 'team2_short': '', 'team2_players': []}
    result = {
        'players': m['players'],
        'team1': m['team1'], 'team1_short': m['team1_short'], 'team1_players': m['team1_players'],
        'team2': m['team2'], 'team2_short': m['team2_short'], 'team2_players': m['team2_players'],
    }
    if result['players']:
        _player_cache[match_id] = result
    return result

def _espn_stats_flat(stats_obj):
    """Flatten ESPN statistics categories into a simple {name: value} dict."""
    result = {}
    for cat in stats_obj.get('categories', []):
        for s in cat.get('stats', []):
            v = s.get('value', 0)
            try:
                result[s['name']] = float(v) if isinstance(v, str) and '.' in v else int(v) if v != '' else 0
            except (ValueError, TypeError):
                result[s['name']] = 0
    return result

def _parse_espn_match(data):
    """
    Parse ESPN API summary response into normalised per-player stats.
    Returns dict with batting/bowling/fielding stats and team info, or None if no data.
    """
    if not data or not data.get('rosters'):
        return None

    batting  = {}   # player_name → {runs, balls, fours, sixes}
    bowling  = {}   # player_name → {wickets, overs, conceded, maidens}
    fielding = {}   # player_name → {catches, stumpings, runouts}
    id_to_name = {}

    for roster_entry in data.get('rosters', []):
        for player in roster_entry.get('roster', []):
            athlete = player.get('athlete', {})
            name = athlete.get('displayName', '')
            athlete_id = athlete.get('id', '')
            if not name:
                continue

            id_to_name[athlete_id] = name
            batting.setdefault(name,  {'runs': 0, 'balls': 0, 'fours': 0, 'sixes': 0})
            bowling.setdefault(name,  {'wickets': 0, 'overs': 0.0, 'conceded': 0, 'maidens': 0})
            fielding.setdefault(name, {'catches': 0, 'stumpings': 0, 'runouts': 0})

            for period in player.get('linescores', []):
                stats = _espn_stats_flat(period.get('statistics', {}))

                if stats.get('batted', 0):
                    batting[name]['runs']  += int(stats.get('runs', 0))
                    batting[name]['balls'] += int(stats.get('ballsFaced', 0))
                    batting[name]['fours'] += int(stats.get('fours', 0))
                    batting[name]['sixes'] += int(stats.get('sixes', 0))

                if stats.get('balls', 0) or stats.get('inningsBowled', 0):
                    bowling[name]['wickets']  += int(stats.get('wickets', 0))
                    bowling[name]['overs']    += float(stats.get('overs', 0))
                    bowling[name]['conceded'] += int(stats.get('conceded', 0))
                    bowling[name]['maidens']  += int(stats.get('maidens', 0))

                # Fielding stats apply regardless of whether player bowled
                caught = int(stats.get('caughtFielder', 0)) + int(stats.get('caughtKeeper', 0))
                fielding[name]['catches']   += caught
                fielding[name]['stumpings'] += int(stats.get('stumped', 0))

    # Parse run-outs: scan every batter's dismissal details
    for roster_entry in data.get('rosters', []):
        for player in roster_entry.get('roster', []):
            for period in player.get('linescores', []):
                bat_detail = period.get('statistics', {}).get('batting', {})
                out_details = bat_detail.get('outDetails', {})
                if out_details.get('dismissalCard') == 'ro':
                    for fielder_info in out_details.get('fielders', []):
                        fid = fielder_info.get('athlete', {}).get('id', '')
                        fname = id_to_name.get(fid, '')
                        if fname and fname in fielding:
                            fielding[fname]['runouts'] += 1

    # Extract team info
    team1 = team2 = team1_short = team2_short = ''
    t1_players: list = []
    t2_players: list = []
    rosters = data.get('rosters', [])
    if rosters:
        t = rosters[0].get('team', {})
        team1       = t.get('displayName', '')
        team1_short = t.get('abbreviation', '')
        t1_players  = [p.get('athlete', {}).get('displayName', '') for p in rosters[0].get('roster', [])]
    if len(rosters) > 1:
        t = rosters[1].get('team', {})
        team2       = t.get('displayName', '')
        team2_short = t.get('abbreviation', '')
        t2_players  = [p.get('athlete', {}).get('displayName', '') for p in rosters[1].get('roster', [])]

    # Extract match status
    status = ''
    is_complete = False
    header = data.get('header', {})
    comps = header.get('competitions', [])
    if comps:
        st = comps[0].get('status', {}).get('type', {})
        status      = st.get('detail', '')
        is_complete = st.get('state', '') == 'post'

    return {
        'batting':  batting,
        'bowling':  bowling,
        'fielding': fielding,
        'team1': team1, 'team1_short': team1_short, 'team1_players': sorted(p for p in t1_players if p),
        'team2': team2, 'team2_short': team2_short, 'team2_players': sorted(p for p in t2_players if p),
        'players':     sorted(batting.keys()),
        'status':      status,
        'is_complete': is_complete,
    }

def _resolve_name(pick_name, espn_names):
    """
    Map a stored pick name to the ESPN display name.
    Tries: exact → substring (pick in espn) → last-name → first-name.
    Returns the ESPN name if found, otherwise the original pick_name.
    """
    if pick_name in espn_names:
        return pick_name
    pick_lower = pick_name.lower()
    # pick is a substring of an ESPN name (e.g. 'Cooper' → 'Cooper Connolly')
    matches = [n for n in espn_names if pick_lower in n.lower()]
    if len(matches) == 1:
        return matches[0]
    # ESPN name is a substring of pick (e.g. 'Prabhsimran' in 'Prabhsimran Singh')
    matches = [n for n in espn_names if n.lower() in pick_lower]
    if len(matches) == 1:
        return matches[0]
    return pick_name

def draft_turn(first, n):
    second = 'shivam' if first == 'amitabh' else 'amitabh'
    return None if n >= 10 else (first if n % 2 == 0 else second)

def get_toss_winner_name(match_id):
    """Return the team name that won the toss, or '' if not yet known."""
    data = espn_get(match_id)
    for note in data.get('notes', []):
        if note.get('type') == 'toss':
            # e.g. "Punjab Kings , elected to field first"
            text = note.get('text', '')
            if text:
                return text.split(',')[0].strip()
    return ''

def build_draft_response(row, picks):
    first = row['first_pick']
    last  = get_last_match_info()
    return {
        'picks': picks,
        'first_pick': first,
        'current_turn': draft_turn(first, len(picks)),
        'amitabh_captain': row['amitabh_captain'] or '',
        'shivam_captain':  row['shivam_captain']  or '',
        'is_complete': bool(row['is_complete']),
        'amitabh_team_choice': row.get('amitabh_team_choice', '') or '',
        'shivam_team_choice':  row.get('shivam_team_choice', '')  or '',
        **last,
    }

def espn_get(match_id):
    """Fetch ESPN match summary using Cricbuzz match_id as the key."""
    espn_id = ESPN_MATCH_IDS.get(str(match_id))
    if not espn_id:
        return {}

    api_path = f'espn_{espn_id}'
    cached = _disk_read(api_path)
    if cached is not None:
        return cached

    url = f'https://site.api.espn.com/apis/site/v2/sports/cricket/{ESPN_LEAGUE_ID}/summary?event={espn_id}'
    req = urllib.request.Request(url, headers=ESPN_HEADERS)
    try:
        response = urllib.request.urlopen(req, timeout=10)
        data = json.loads(response.read())
        _disk_write(api_path, data)
        return data
    except urllib.error.HTTPError as e:
        print(f'ESPN API HTTP error {e.code}: {url}')
        return _disk_read_stale(api_path)
    except Exception as e:
        print(f'ESPN API error: {e}')
        return _disk_read_stale(api_path)

def calculate_points(player_name, is_captain, match_stats):
    """Calculate fantasy points from ESPN match stats dict."""
    bat = match_stats.get('batting',  {}).get(player_name, {})
    bwl = match_stats.get('bowling',  {}).get(player_name, {})
    fld = match_stats.get('fielding', {}).get(player_name, {})

    runs      = bat.get('runs', 0)
    wickets   = bwl.get('wickets', 0)
    catches   = fld.get('catches', 0)
    stumpings = fld.get('stumpings', 0)
    runouts   = fld.get('runouts', 0)

    pts = runs + (wickets * 20) + (catches * 10) + (runouts * 10) + (stumpings * 10)
    if runs >= 100:
        pts += 20
    elif runs >= 50:
        pts += 10
    if wickets >= 5:
        pts += 20
    if is_captain:
        pts *= 2

    return {
        'name': player_name,
        'runs': runs,
        'wickets': wickets,
        'catches': catches,
        'runouts': runouts,
        'stumpings': stumpings,
        'points': pts,
        'is_captain': is_captain,
    }

def score_team(players, captain, match_stats):
    results = []
    total = 0
    for p in players:
        r = calculate_points(p, p == captain, match_stats)
        results.append(r)
        total += r['points']
    return results, total
@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'index.html')
@app.route('/api/fixtures')
def get_fixtures():
    conn = get_db()
    rows = conn.execute('SELECT * FROM fixtures ORDER BY start_date').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/players/<match_id>')
def get_players(match_id):
    data = espn_get(match_id)
    m = _parse_espn_match(data)
    if not m or not m.get('players'):
        return jsonify({'error': 'No player data yet.', 'players': []})
    return jsonify({
        'players': m['players'],
        'team1': m['team1'], 'team1_short': m['team1_short'], 'team1_players': m['team1_players'],
        'team2': m['team2'], 'team2_short': m['team2_short'], 'team2_players': m['team2_players'],
        'status': m['status'],
        'match_id': match_id,
    })

@app.route('/api/match/<match_id>/players')
def get_match_players(match_id):
    """Fetch players from ESPN rosters for this match."""
    now = time.time()
    cached = _match_players_cache.get(match_id)
    if cached and now - cached['ts'] < CACHE_TTL:
        return jsonify(cached['data'])

    data = espn_get(match_id)
    m = _parse_espn_match(data)
    if not m or not m.get('players'):
        return jsonify({
            'team1': '', 'team1_short': '', 'team1_players': [],
            'team2': '', 'team2_short': '', 'team2_players': [],
            'players': [],
        })

    result = {
        'team1': m['team1'], 'team1_short': m['team1_short'],
        'team1_players': [{'name': n, 'role': ''} for n in m['team1_players']],
        'team2': m['team2'], 'team2_short': m['team2_short'],
        'team2_players': [{'name': n, 'role': ''} for n in m['team2_players']],
        'players': m['players'],
    }
    if result['players']:
        _match_players_cache[match_id] = {'data': result, 'ts': now}
    return jsonify(result)

@app.route('/api/draft/<match_id>')
def get_draft(match_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM drafts WHERE match_id = ?', (match_id,)).fetchone()
    if not row:
        first = get_last_match_info()['last_match_winner']  # overridden after toss via /choose_team
        conn.execute(
            'INSERT INTO drafts (match_id, first_pick, picks, amitabh_captain, shivam_captain, is_complete, created_at) VALUES (?,?,?,?,?,?,?)',
            (match_id, first, '[]', '', '', 0, int(time.time()))
        )
        conn.commit()
        row = conn.execute('SELECT * FROM drafts WHERE match_id = ?', (match_id,)).fetchone()
    conn.close()
    player_data = get_players_cached(match_id)
    picks = json.loads(row['picks'])
    return jsonify({**build_draft_response(dict(row), picks), **player_data, 'exists': True})

@app.route('/api/draft/<match_id>/start', methods=['POST'])
def start_draft(match_id):
    conn = get_db()
    row = conn.execute('SELECT match_id FROM drafts WHERE match_id = ?', (match_id,)).fetchone()
    if not row:
        first = get_last_match_info()['last_match_winner']  # overridden after toss via /choose_team
        conn.execute(
            'INSERT INTO drafts (match_id, first_pick, picks, amitabh_captain, shivam_captain, is_complete, created_at) VALUES (?,?,?,?,?,?,?)',
            (match_id, first, '[]', '', '', 0, int(time.time()))
        )
        conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/draft/<match_id>/choose_team', methods=['POST'])
def choose_team(match_id):
    """
    Step 1 of draft order: the winner of the last match chooses which team they want.
    Step 2: once both users have chosen, we fetch the toss result and set first_pick
    to whichever user's chosen team won the toss.
    """
    data = request.json
    user, team = data.get('user'), data.get('team')
    if user not in ('amitabh', 'shivam') or not team:
        return jsonify({'error': 'Invalid input'}), 400
    conn = get_db()
    row = conn.execute('SELECT * FROM drafts WHERE match_id = ?', (match_id,)).fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'Draft not found'}), 400
    col = 'amitabh_team_choice' if user == 'amitabh' else 'shivam_team_choice'
    conn.execute(f'UPDATE drafts SET {col} = ? WHERE match_id = ?', (team, match_id))
    conn.commit()
    row2 = conn.execute('SELECT * FROM drafts WHERE match_id = ?', (match_id,)).fetchone()
    a_choice = row2['amitabh_team_choice'] or ''
    s_choice = row2['shivam_team_choice']  or ''
    # Once both users have chosen a team, resolve first_pick from the toss
    if a_choice and s_choice:
        toss_winner = get_toss_winner_name(match_id)
        if toss_winner:
            tw = toss_winner.lower()
            def _matches(choice):
                c = choice.lower()
                return c in tw or tw in c
            if _matches(a_choice):
                first_pick = 'amitabh'
            elif _matches(s_choice):
                first_pick = 'shivam'
            else:
                first_pick = row2['first_pick']  # toss team unrecognised, keep default
            conn.execute('UPDATE drafts SET first_pick = ? WHERE match_id = ?', (first_pick, match_id))
            conn.commit()
            row2 = conn.execute('SELECT * FROM drafts WHERE match_id = ?', (match_id,)).fetchone()
    picks = json.loads(row2['picks'])
    result = build_draft_response(dict(row2), picks)
    conn.close()
    player_data = get_players_cached(match_id)
    return jsonify({**result, **player_data})

@app.route('/api/draft/<match_id>/pick', methods=['POST'])
def make_pick(match_id):
    data = request.json
    user, player = data.get('user'), data.get('player')
    if user not in ('amitabh', 'shivam') or not player:
        return jsonify({'error': 'Invalid input'}), 400
    conn = get_db()
    row = conn.execute('SELECT * FROM drafts WHERE match_id = ?', (match_id,)).fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'Draft not started'}), 400
    picks = json.loads(row['picks'])
    if len(picks) >= 10:
        conn.close(); return jsonify({'error': 'All picks done'}), 400
    if draft_turn(row['first_pick'], len(picks)) != user:
        conn.close(); return jsonify({'error': 'Not your turn'}), 400
    if any(p['player'] == player for p in picks):
        conn.close(); return jsonify({'error': 'Player already picked'}), 400
    picks.append({'player': player, 'user': user})
    conn.execute('UPDATE drafts SET picks = ? WHERE match_id = ?', (json.dumps(picks), match_id))
    conn.commit()
    result = build_draft_response(dict(row), picks)
    conn.close()
    return jsonify(result)

@app.route('/api/draft/<match_id>/captain', methods=['POST'])
def set_captain(match_id):
    data = request.json
    user, captain = data.get('user'), data.get('captain')
    if user not in ('amitabh', 'shivam') or not captain:
        return jsonify({'error': 'Invalid input'}), 400
    conn = get_db()
    row = conn.execute('SELECT * FROM drafts WHERE match_id = ?', (match_id,)).fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'Draft not found'}), 400
    picks = json.loads(row['picks'])
    if len(picks) < 10:
        conn.close(); return jsonify({'error': 'Draft picks not complete'}), 400
    user_picks = [p['player'] for p in picks if p['user'] == user]
    if captain not in user_picks:
        conn.close(); return jsonify({'error': 'Captain must be one of your picks'}), 400
    col = 'amitabh_captain' if user == 'amitabh' else 'shivam_captain'
    conn.execute(f'UPDATE drafts SET {col} = ? WHERE match_id = ?', (captain, match_id))
    conn.commit()
    row2 = conn.execute('SELECT * FROM drafts WHERE match_id = ?', (match_id,)).fetchone()
    a_cap, s_cap = row2['amitabh_captain'] or '', row2['shivam_captain'] or ''
    if a_cap and s_cap:
        a_players = [p['player'] for p in picks if p['user'] == 'amitabh']
        s_players = [p['player'] for p in picks if p['user'] == 'shivam']
        conn.execute('''INSERT OR REPLACE INTO selections
            (match_id, amitabh_players, amitabh_captain, shivam_players, shivam_captain, created_at)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (match_id, json.dumps(a_players), a_cap, json.dumps(s_players), s_cap, int(time.time())))
        conn.execute('UPDATE drafts SET is_complete = 1 WHERE match_id = ?', (match_id,))
        conn.commit()
    result = build_draft_response(dict(row2), picks)
    conn.close()
    return jsonify(result)

@app.route('/api/selections')
def get_all_selections():
    conn = get_db()
    rows = conn.execute('SELECT match_id FROM selections').fetchall()
    conn.close()
    return jsonify([r['match_id'] for r in rows])

@app.route('/api/selections/<match_id>')
def get_selection(match_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM selections WHERE match_id = ?', (match_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'exists': False, 'match_id': match_id})
    return jsonify({
        'exists': True,
        'match_id': match_id,
        'amitabh_players': json.loads(row['amitabh_players']),
        'amitabh_captain': row['amitabh_captain'],
        'shivam_players': json.loads(row['shivam_players']),
        'shivam_captain': row['shivam_captain'],
    })

@app.route('/api/select', methods=['POST'])
def save_selection():
    data = request.json
    match_id = data.get('match_id')
    if match_id in LOCKED_MATCH_IDS:
        return jsonify({'error': 'This match is locked — picks cannot be changed'}), 403
    amitabh = data.get('amitabh_players', [])
    amitabh_cap = data.get('amitabh_captain', '')
    shivam = data.get('shivam_players', [])
    shivam_cap = data.get('shivam_captain', '')
    if len(amitabh) != 5 or len(shivam) != 5:
        return jsonify({'error': 'Must select exactly 5 players each'}), 400
    conn = get_db()
    conn.execute('''
        INSERT OR REPLACE INTO selections
        (match_id, amitabh_players, amitabh_captain, shivam_players, shivam_captain, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (match_id, json.dumps(amitabh), amitabh_cap,
          json.dumps(shivam), shivam_cap, int(time.time())))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/score/<match_id>')
def score_match(match_id):
    """Calculate fantasy points for a saved selection using ESPN scorecard."""
    if match_id in LOCKED_MATCH_IDS:
        return jsonify({'error': 'This match is locked — use /api/season for historical scores'}), 403
    espn_data = espn_get(match_id)
    match_stats = _parse_espn_match(espn_data)
    conn = get_db()
    row = conn.execute('SELECT * FROM selections WHERE match_id = ?', (match_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'No picks saved for this match yet'}), 404
    if not match_stats:
        return jsonify({'error': 'ESPN scorecard not available yet — try again after the match'}), 404
    espn_names = list(match_stats.get('batting', {}).keys())
    amitabh = [_resolve_name(p, espn_names) for p in json.loads(row['amitabh_players'])]
    amitabh_cap = _resolve_name(row['amitabh_captain'], espn_names)
    shivam = [_resolve_name(p, espn_names) for p in json.loads(row['shivam_players'])]
    shivam_cap = _resolve_name(row['shivam_captain'], espn_names)
    a_players, a_total = score_team(amitabh, amitabh_cap, match_stats)
    s_players, s_total = score_team(shivam, shivam_cap, match_stats)
    status = match_stats.get('status', '')
    # Invalidate season cache so standings update
    _season_cache['data'] = None
    _season_cache['ts'] = 0
    return jsonify({
        'match_id': match_id,
        'status': status,
        'amitabh': {'total': a_total, 'players': a_players, 'captain': amitabh_cap},
        'shivam': {'total': s_total, 'players': s_players, 'captain': shivam_cap},
        'leader': 'amitabh' if a_total > s_total else 'shivam',
        'gap': abs(a_total - s_total),
    })

@app.route('/api/live/<match_id>')
def get_live_score(match_id):
    espn_data = espn_get(match_id)
    match_stats = _parse_espn_match(espn_data)
    conn = get_db()
    row = conn.execute('SELECT * FROM selections WHERE match_id = ?', (match_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'No selections found'})
    if not match_stats:
        return jsonify({'error': 'ESPN scorecard not available yet'})
    espn_names = list(match_stats.get('batting', {}).keys())
    amitabh = [_resolve_name(p, espn_names) for p in json.loads(row['amitabh_players'])]
    amitabh_cap = _resolve_name(row['amitabh_captain'], espn_names)
    shivam = [_resolve_name(p, espn_names) for p in json.loads(row['shivam_players'])]
    shivam_cap = _resolve_name(row['shivam_captain'], espn_names)
    a_players, a_total = score_team(amitabh, amitabh_cap, match_stats)
    s_players, s_total = score_team(shivam, shivam_cap, match_stats)
    return jsonify({
        'match_id': match_id,
        'status': match_stats.get('status', ''),
        'is_complete': match_stats.get('is_complete', False),
        'amitabh': {'total': a_total, 'players': a_players, 'captain': amitabh_cap},
        'shivam': {'total': s_total, 'players': s_players, 'captain': shivam_cap},
        'leader': 'amitabh' if a_total > s_total else 'shivam',
        'gap': abs(a_total - s_total)
    })

@app.route('/api/season')
def get_season():
    now = time.time()
    if _season_cache['data'] and now - _season_cache['ts'] < CACHE_TTL:
        return jsonify(_season_cache['data'])
    past_matches = [
        {
            'match_id': '149618', 'desc': 'Match 1 — RCB vs SRH',
            'amitabh_total': 312, 'shivam_total': 174,
            'amitabh_players': [
                {'name':'Ishan Kishan','runs':80,'wickets':0,'catches':0,'runouts':0,'points':180,'is_captain':True},
                {'name':'Phil Salt','runs':0,'wickets':0,'catches':3,'runouts':0,'points':30,'is_captain':False},
                {'name':'Travis Head','runs':11,'wickets':0,'catches':0,'runouts':0,'points':11,'is_captain':False},
                {'name':'Rajat Patidar','runs':31,'wickets':0,'catches':0,'runouts':0,'points':31,'is_captain':False},
                {'name':'Romario Shepherd','runs':0,'wickets':3,'catches':0,'runouts':0,'points':60,'is_captain':False},
            ],
            'shivam_players': [
                {'name':'Abhishek Sharma','runs':7,'wickets':0,'catches':0,'runouts':0,'points':14,'is_captain':True},
                {'name':'Virat Kohli','runs':69,'wickets':0,'catches':1,'runouts':0,'points':89,'is_captain':False},
                {'name':'Heinrich Klaasen','runs':31,'wickets':0,'catches':2,'runouts':0,'points':51,'is_captain':False},
                {'name':'Harshal Patel','runs':0,'wickets':0,'catches':0,'runouts':0,'points':0,'is_captain':False},
                {'name':'Bhuvneshwar Kumar','runs':0,'wickets':1,'catches':0,'runouts':0,'points':20,'is_captain':False},
            ],
        },
        {
            'match_id': '149629', 'desc': 'Match 2 — MI vs KKR',
            'amitabh_total': 295, 'shivam_total': 96,
            'amitabh_players': [
                {'name':'Angkrish Raghuvanshi','runs':51,'wickets':0,'catches':0,'runouts':0,'points':122,'is_captain':True},
                {'name':'Rohit Sharma','runs':78,'wickets':0,'catches':0,'runouts':0,'points':88,'is_captain':False},
                {'name':'Finn Allen','runs':37,'wickets':0,'catches':0,'runouts':0,'points':37,'is_captain':False},
                {'name':'Hardik Pandya','runs':18,'wickets':1,'catches':1,'runouts':0,'points':48,'is_captain':False},
                {'name':'Jasprit Bumrah','runs':0,'wickets':0,'catches':0,'runouts':0,'points':0,'is_captain':False},
            ],
            'shivam_players': [
                {'name':'Cameron Green','runs':18,'wickets':0,'catches':0,'runouts':0,'points':36,'is_captain':True},
                {'name':'Trent Boult','runs':0,'wickets':0,'catches':0,'runouts':0,'points':0,'is_captain':False},
                {'name':'Tilak Varma','runs':20,'wickets':0,'catches':2,'runouts':0,'points':40,'is_captain':False},
                {'name':'Sunil Narine','runs':0,'wickets':1,'catches':0,'runouts':0,'points':20,'is_captain':False},
                {'name':'Varun Chakaravarthy','runs':0,'wickets':0,'catches':0,'runouts':0,'points':0,'is_captain':False},
            ],
        },
        {
            'match_id': '149640', 'desc': 'Match 3 — RR vs CSK',
            'amitabh_total': 142, 'shivam_total': 77,
            'amitabh_players': [
                {'name':'Vaibhav Sooryavanshi','runs':52,'wickets':0,'catches':0,'runouts':0,'points':124,'is_captain':True},
                {'name':'Shivam Dube','runs':6,'wickets':0,'catches':0,'runouts':0,'points':6,'is_captain':False},
                {'name':'Matthew Short','runs':2,'wickets':0,'catches':0,'runouts':0,'points':2,'is_captain':False},
                {'name':'Ayush Mhatre','runs':0,'wickets':0,'catches':0,'runouts':0,'points':0,'is_captain':False},
                {'name':'Shimron Hetmyer','runs':0,'wickets':0,'catches':0,'runouts':1,'points':10,'is_captain':False},
            ],
            'shivam_players': [
                {'name':'Sanju Samson','runs':6,'wickets':0,'catches':0,'runouts':0,'points':12,'is_captain':True},
                {'name':'Riyan Parag','runs':14,'wickets':0,'catches':0,'runouts':0,'points':14,'is_captain':False},
                {'name':'Nandre Burger','runs':0,'wickets':2,'catches':0,'runouts':0,'points':40,'is_captain':False},
                {'name':'Matt Henry','runs':5,'wickets':0,'catches':0,'runouts':0,'points':5,'is_captain':False},
                {'name':'Ruturaj Gaikwad','runs':6,'wickets':0,'catches':0,'runouts':0,'points':6,'is_captain':False},
            ],
        },
        {
            'match_id': '149651', 'desc': 'Match 4 — GT vs PBKS',
            'amitabh_total': 154, 'shivam_total': 191,
            'amitabh_players': [
                {'name':'Sai Sudharsan','runs':13,'wickets':0,'catches':0,'runouts':0,'points':26,'is_captain':True},
                {'name':'Shubman Gill','runs':39,'wickets':0,'catches':2,'runouts':0,'points':59,'is_captain':False},
                {'name':'Glenn Phillips','runs':25,'wickets':0,'catches':0,'runouts':0,'points':25,'is_captain':False},
                {'name':'Prabhsimran Singh','runs':37,'wickets':0,'catches':0,'runouts':0,'points':37,'is_captain':False},
                {'name':'Priyansh Arya','runs':7,'wickets':0,'catches':0,'runouts':0,'points':7,'is_captain':False},
            ],
            'shivam_players': [
                {'name':'Shreyas Iyer','runs':18,'wickets':0,'catches':1,'runouts':0,'points':56,'is_captain':True},
                {'name':'Jos Buttler','runs':38,'wickets':0,'catches':1,'runouts':0,'points':48,'is_captain':False},
                {'name':'Marco Jansen','runs':9,'wickets':1,'catches':1,'runouts':0,'points':39,'is_captain':False},
                {'name':'Washington Sundar','runs':18,'wickets':1,'catches':1,'runouts':0,'points':48,'is_captain':False},
                {'name':'Mohammed Siraj','runs':0,'wickets':0,'catches':0,'runouts':0,'points':0,'is_captain':False},
            ],
        },
        {
            'match_id': '149662', 'desc': 'Match 5 — LSG vs DC',
            'amitabh_total': 156, 'shivam_total': 58,
            'amitabh_players': [
                {'name':'KL Rahul','runs':0,'wickets':0,'catches':1,'runouts':0,'points':20,'is_captain':True},
                {'name':'Lungi Ngidi','runs':0,'wickets':3,'catches':0,'runouts':0,'points':60,'is_captain':False},
                {'name':'Mitchell Marsh','runs':35,'wickets':0,'catches':0,'runouts':0,'points':35,'is_captain':False},
                {'name':'Aiden Markram','runs':11,'wickets':0,'catches':0,'runouts':0,'points':11,'is_captain':False},
                {'name':'Mohsin Khan','runs':0,'wickets':1,'catches':1,'runouts':0,'points':30,'is_captain':False},
            ],
            'shivam_players': [
                {'name':'Nicholas Pooran','runs':8,'wickets':0,'catches':0,'runouts':0,'points':16,'is_captain':True},
                {'name':'Mohammed Shami','runs':1,'wickets':1,'catches':0,'runouts':0,'points':21,'is_captain':False},
                {'name':'Axar Patel','runs':0,'wickets':1,'catches':0,'runouts':0,'points':20,'is_captain':False},
                {'name':'Anrich Nortje','runs':0,'wickets':0,'catches':0,'runouts':0,'points':0,'is_captain':False},
                {'name':'Pathum Nissanka','runs':1,'wickets':0,'catches':0,'runouts':0,'points':1,'is_captain':False},
            ],
        },
        {
            'match_id': '149673', 'desc': 'Match 6 — KKR vs SRH',
            'amitabh_total': 198, 'shivam_total': 283,
            'amitabh_players': [
                {'name':'Travis Head','runs':46,'wickets':0,'catches':0,'runouts':0,'points':92,'is_captain':True},
                {'name':'Abhishek Sharma','runs':48,'wickets':0,'catches':0,'runouts':0,'points':48,'is_captain':False},
                {'name':'Cameron Green','runs':2,'wickets':0,'catches':1,'runouts':0,'points':12,'is_captain':False},
                {'name':'Ajinkya Rahane','runs':8,'wickets':0,'catches':1,'runouts':0,'points':18,'is_captain':False},
                {'name':'Finn Allen','runs':28,'wickets':0,'catches':0,'runouts':0,'points':28,'is_captain':False},
            ],
            'shivam_players': [
                {'name':'Ishan Kishan','runs':14,'wickets':0,'catches':2,'runouts':0,'points':68,'is_captain':True},
                {'name':'Sunil Narine','runs':12,'wickets':0,'catches':0,'runouts':0,'points':12,'is_captain':False},
                {'name':'Angkrish Raghuvanshi','runs':52,'wickets':0,'catches':0,'runouts':0,'points':62,'is_captain':False},
                {'name':'Heinrich Klaasen','runs':52,'wickets':0,'catches':0,'runouts':0,'points':62,'is_captain':False},
                {'name':'Nitish Kumar Reddy','runs':39,'wickets':2,'catches':0,'runouts':0,'points':79,'is_captain':False},
            ],
        },
    ]

    a_total = sum(m['amitabh_total'] for m in past_matches)
    s_total = sum(m['shivam_total'] for m in past_matches)

    # Add any new matches from DB
    conn = get_db()
    rows = conn.execute('SELECT * FROM selections').fetchall()
    conn.close()
    past_ids = [m['match_id'] for m in past_matches]
    for row in rows:
        mid = row['match_id']
        if mid in past_ids:
            continue
        espn_data = espn_get(mid)
        match_stats = _parse_espn_match(espn_data)
        if not match_stats:
            continue
        espn_names = list(match_stats.get('batting', {}).keys())
        amitabh = [_resolve_name(p, espn_names) for p in json.loads(row['amitabh_players'])]
        a_cap = _resolve_name(row['amitabh_captain'], espn_names)
        shivam = [_resolve_name(p, espn_names) for p in json.loads(row['shivam_players'])]
        s_cap = _resolve_name(row['shivam_captain'], espn_names)
        a_players, at = score_team(amitabh, a_cap, match_stats)
        s_players, st = score_team(shivam, s_cap, match_stats)
        a_total += at
        s_total += st
        past_matches.append({
            'match_id': mid,
            'desc': KNOWN_MATCH_LABELS.get(mid, match_stats.get('status', '')),
            'amitabh_total': at,
            'shivam_total': st,
            'amitabh_players': a_players,
            'shivam_players': s_players,
        })

    result = {
        'amitabh_total': a_total,
        'shivam_total': s_total,
        'matches': past_matches,
        'leader': 'amitabh' if a_total > s_total else 'shivam',
        'gap': abs(a_total - s_total)
    }
    _season_cache['data'] = result
    _season_cache['ts'] = time.time()
    return jsonify(result)

if __name__ == '__main__':
    init_db()
    print('\n🏏 IPL Fantasy API starting...')
    print('Running at http://localhost:8080\n')
    app.run(debug=True, port=8080)
