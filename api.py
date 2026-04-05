from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import urllib.request
import json
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
CORS(app)

API_KEY = 'af7e0d6342mshf4bafbb8b9f34a4p142027jsne77b07afae99'
API_HOST = 'cricbuzz-cricket.p.rapidapi.com'
IPL_SERIES_ID = 9241
IST = timezone(timedelta(hours=5, minutes=30))

# Labels for matches tracked by ID (used in season history for DB-sourced matches)
KNOWN_MATCH_LABELS = {
    '149684': 'Match 7 — CSK vs PBKS',
}

def get_db():
    conn = sqlite3.connect('fantasy.db')
    conn.row_factory = sqlite3.Row
    return conn

# Called at module level so gunicorn (which skips __main__) still creates tables
def _ensure_db():
    conn = get_db()
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
    # One-time data entry: match 7 CSK vs PBKS selections
    conn.execute('''INSERT OR IGNORE INTO selections
        (match_id, amitabh_players, amitabh_captain, shivam_players, shivam_captain, created_at)
        VALUES (?, ?, ?, ?, ?, ?)''', (
        '149684',
        json.dumps(['Cooper', 'Shivam Dube', 'Priyansh Arya', 'Prabhsimran Singh', 'Kartik Sharma']),
        'Cooper',
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
CACHE_TTL = 300  # seconds — refresh at most every 5 minutes

def get_players_cached(match_id):
    if match_id in _player_cache:
        return _player_cache[match_id]
    data = cricbuzz_get(f'/mcenter/v1/{match_id}/hscard')
    result = _parse_players_from_scorecard(data)
    if result['players']:
        _player_cache[match_id] = result
    return result

def _parse_players_from_scorecard(data):
    """
    Extract players grouped by team from an hscard response.
    The API returns batteamname/batteamsname directly on each innings object.
    Inn[0] batsmen = team1, inn[0] bowlers = team2.
    Inn[1] batsmen = team2, inn[1] bowlers = team1.
    """
    scorecard = data.get('scorecard', [])
    t1, t2 = set(), set()
    if len(scorecard) >= 1:
        for b in scorecard[0].get('batsman', []): t1.add(b['name'])
        for b in scorecard[0].get('bowler', []):  t2.add(b['name'])
    if len(scorecard) >= 2:
        for b in scorecard[1].get('batsman', []): t2.add(b['name'])
        for b in scorecard[1].get('bowler', []):  t1.add(b['name'])
    team1_name  = scorecard[0].get('batteamname',  '') if scorecard else ''
    team1_short = scorecard[0].get('batteamsname', '') if scorecard else ''
    team2_name  = scorecard[1].get('batteamname',  '') if len(scorecard) > 1 else ''
    team2_short = scorecard[1].get('batteamsname', '') if len(scorecard) > 1 else ''
    return {
        'players': sorted(t1 | t2),
        'team1': team1_name, 'team1_short': team1_short, 'team1_players': sorted(t1),
        'team2': team2_name, 'team2_short': team2_short, 'team2_players': sorted(t2),
    }

def draft_turn(first, n):
    second = 'shivam' if first == 'amitabh' else 'amitabh'
    return None if n >= 10 else (first if n % 2 == 0 else second)

def get_toss_winner_name(match_id):
    """Return the team name that won the toss, or '' if not yet known."""
    data = cricbuzz_get(f'/mcenter/v1/{match_id}/hscard')
    toss = (data.get('tossResults')
            or data.get('matchHeader', {}).get('tossResults')
            or {})
    return toss.get('tossWinnerName', '')

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

def cricbuzz_get(path):
    url = f'https://{API_HOST}{path}'
    req = urllib.request.Request(url, headers={
        'x-rapidapi-host': API_HOST,
        'x-rapidapi-key': API_KEY
    })
    try:
        response = urllib.request.urlopen(req, timeout=10)
        return json.loads(response.read())
    except Exception as e:
        print(f'API error: {e}')
        return {}

def calculate_points(player_name, is_captain, innings_list):
    runs = wickets = catches = runouts = stumpings = 0
    for innings in innings_list:
        for b in innings.get('batsman', []):
            if b['name'] == player_name:
                runs += b.get('runs', 0)
        for b in innings.get('bowler', []):
            if b['name'] == player_name:
                wickets += b.get('wickets', 0)
        for b in innings.get('batsman', []):
            outdec = b.get('outdec', '')
            if not outdec:
                continue
            if f'c {player_name} b' in outdec:
                catches += 1
            if f'c & b {player_name}' in outdec or f'c and b {player_name}' in outdec:
                catches += 1
            if f'st {player_name}' in outdec:
                stumpings += 1
            if 'run out' in outdec and player_name in outdec:
                runouts += 1
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
        'is_captain': is_captain
    }

def score_team(players, captain, innings_list):
    results = []
    total = 0
    for p in players:
        r = calculate_points(p, p == captain, innings_list)
        results.append(r)
        total += r['points']
    return results, total
@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'index.html')
@app.route('/api/fixtures')
def get_fixtures():
    now = time.time()
    if _fixtures_cache['data'] and now - _fixtures_cache['ts'] < CACHE_TTL:
        return jsonify(_fixtures_cache['data'])

    data = cricbuzz_get(f'/series/v1/{IPL_SERIES_ID}')
    matches = []
    for item in data.get('matchDetails', []):
        md = item.get('matchDetailsMap', {})
        for m in md.get('match', []):
            mi = m.get('matchInfo', {})
            ms = m.get('matchScore', {})
            t1 = mi.get('team1', {})
            t2 = mi.get('team2', {})
            t1score = ms.get('team1Score', {}).get('inngs1', {})
            t2score = ms.get('team2Score', {}).get('inngs1', {})
            start_ms = int(mi.get('startDate', 0))
            dt_ist = datetime.fromtimestamp(start_ms / 1000, tz=IST)
            matches.append({
                'match_id': str(mi.get('matchId', '')),
                'desc': mi.get('matchDesc', ''),
                'team1': t1.get('teamName', ''),
                'team1_short': t1.get('teamSName', ''),
                'team1_runs': t1score.get('runs', '-'),
                'team1_wkts': t1score.get('wickets', '-'),
                'team1_overs': t1score.get('overs', '-'),
                'team2': t2.get('teamName', ''),
                'team2_short': t2.get('teamSName', ''),
                'team2_runs': t2score.get('runs', '-'),
                'team2_wkts': t2score.get('wickets', '-'),
                'team2_overs': t2score.get('overs', '-'),
                'status': mi.get('status', ''),
                'state': mi.get('state', ''),
                'start_date': mi.get('startDate', ''),
                'start_ist': dt_ist.strftime('%-d %b · %-I:%M %p IST'),
                'venue': mi.get('venueInfo', {}).get('ground', ''),
                'city': mi.get('venueInfo', {}).get('city', ''),
            })
    matches.sort(key=lambda x: int(x['start_date']) if x['start_date'] else 0)

    if matches:
        _fixtures_cache['data'] = matches
        _fixtures_cache['ts'] = now
    elif _fixtures_cache['data']:
        # API failed (rate limit / outage) — return last good response
        return jsonify(_fixtures_cache['data'])

    return jsonify(matches)

@app.route('/api/players/<match_id>')
def get_players(match_id):
    data = cricbuzz_get(f'/mcenter/v1/{match_id}/hscard')
    if not data.get('scorecard'):
        return jsonify({'error': 'No player data yet.', 'players': []})
    p = _parse_players_from_scorecard(data)
    return jsonify({
        'players': p['players'],
        'team1': p['team1'],
        'team1_short': p['team1_short'],
        'team1_players': p['team1_players'],
        'team2': p['team2'],
        'team2_short': p['team2_short'],
        'team2_players': p['team2_players'],
        'status': data.get('status', ''),
        'match_id': match_id
    })

@app.route('/api/match/<match_id>/players')
def get_match_players(match_id):
    """Fetch players from scorecard + commentary + squads in parallel and merge."""
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_hscard = ex.submit(cricbuzz_get, f'/mcenter/v1/{match_id}/hscard')
        f_comm   = ex.submit(cricbuzz_get, f'/mcenter/v1/{match_id}/comm')
        f_squads = ex.submit(cricbuzz_get, f'/mcenter/v1/{match_id}/squads')
        hscard_data = f_hscard.result()
        comm_data   = f_comm.result()
        squads_data = f_squads.result()

    # ── 1. Squads: full squad as base (all 15–16 players per team) ──────────
    t1_name, t1_short, t2_name, t2_short = '', '', '', ''
    t1_players, t2_players = {}, {}   # name → role

    squads = squads_data.get('squads', [])
    def _extract_squad(entry):
        name  = entry.get('teamName') or entry.get('team', {}).get('name', '')
        short = entry.get('teamShortName') or entry.get('shortName') or entry.get('team', {}).get('shortName', '')
        players = {}
        for p in (entry.get('players') or entry.get('squad', {}).get('players') or []):
            n = p.get('name', '')
            r = p.get('role', '')
            if n:
                players[n] = r
        return name, short, players

    if len(squads) >= 1:
        t1_name, t1_short, t1_players = _extract_squad(squads[0])
    if len(squads) >= 2:
        t2_name, t2_short, t2_players = _extract_squad(squads[1])

    # ── 2. Commentary: parse Playing XI announcement (highest priority) ──────
    # Typical format: "Team Name (Playing XI): P1, P2, P3, ..."
    import re
    comm_xi = {}  # team_name_fragment → set of player names
    for item in (comm_data.get('commentaryList') or []):
        text = item.get('commText', '')
        m = re.search(r'(.+?)\s*\(Playing (?:XI|11)\)\s*:\s*(.+)', text, re.IGNORECASE)
        if m:
            team_frag = m.group(1).strip()
            names = [n.strip() for n in re.split(r',\s*', m.group(2)) if n.strip()]
            comm_xi[team_frag] = names

    def _assign_comm_xi(comm_xi, t1_name, t1_short, t2_name, t2_short):
        xi1, xi2 = [], []
        for frag, names in comm_xi.items():
            # Match fragment against known team names (case-insensitive partial match)
            def matches(frag, name, short):
                f = frag.lower(); n = name.lower(); s = short.lower()
                return f in n or n in f or (s and f in s) or (s and s in f)
            if matches(frag, t1_name, t1_short):
                xi1 = names
            elif matches(frag, t2_name, t2_short):
                xi2 = names
        return xi1, xi2

    xi1, xi2 = _assign_comm_xi(comm_xi, t1_name, t1_short, t2_name, t2_short)

    # ── 3. Scorecard: players who've already batted/bowled ───────────────────
    scorecard = hscard_data.get('scorecard', [])
    sc_t1, sc_t2 = set(), set()
    if len(scorecard) >= 1:
        for b in scorecard[0].get('batsman', []): sc_t1.add(b['name'])
        for b in scorecard[0].get('bowler', []):  sc_t2.add(b['name'])
    if len(scorecard) >= 2:
        for b in scorecard[1].get('batsman', []): sc_t2.add(b['name'])
        for b in scorecard[1].get('bowler', []):  sc_t1.add(b['name'])

    # Fall back to scorecard team names if squads didn't yield them
    if not t1_name and scorecard:
        t1_name  = scorecard[0].get('batteamname', '')
        t1_short = scorecard[0].get('batteamsname', '')
    if not t2_name and len(scorecard) > 1:
        t2_name  = scorecard[1].get('batteamname', '')
        t2_short = scorecard[1].get('batteamsname', '')

    # ── 4. Merge: comm XI > squads > scorecard ───────────────────────────────
    def _build_final(xi, squad_dict, sc_set):
        final = {}
        if xi:
            for n in xi:
                final[n] = squad_dict.get(n, '')
        elif squad_dict:
            final = dict(squad_dict)
        else:
            final = {n: '' for n in sc_set}
        # Always add scorecard players (impact subs / anyone who played)
        for n in sc_set:
            if n not in final:
                final[n] = squad_dict.get(n, '')
        return final

    final_t1 = _build_final(xi1, t1_players, sc_t1)
    final_t2 = _build_final(xi2, t2_players, sc_t2)

    return jsonify({
        'team1': t1_name, 'team1_short': t1_short,
        'team1_players': [{'name': n, 'role': r} for n, r in sorted(final_t1.items())],
        'team2': t2_name, 'team2_short': t2_short,
        'team2_players': [{'name': n, 'role': r} for n, r in sorted(final_t2.items())],
        'players': sorted(set(final_t1) | set(final_t2)),
    })

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

@app.route('/api/live/<match_id>')
def get_live_score(match_id):
    data = cricbuzz_get(f'/mcenter/v1/{match_id}/hscard')
    scorecard = data.get('scorecard', [])
    status = data.get('status', '')
    is_complete = data.get('isMatchComplete', False)
    conn = get_db()
    row = conn.execute('SELECT * FROM selections WHERE match_id = ?', (match_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'No selections found'})
    amitabh = json.loads(row['amitabh_players'])
    amitabh_cap = row['amitabh_captain']
    shivam = json.loads(row['shivam_players'])
    shivam_cap = row['shivam_captain']
    a_players, a_total = score_team(amitabh, amitabh_cap, scorecard)
    s_players, s_total = score_team(shivam, shivam_cap, scorecard)
    return jsonify({
        'match_id': match_id,
        'status': status,
        'is_complete': is_complete,
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
        data = cricbuzz_get(f'/mcenter/v1/{mid}/hscard')
        scorecard = data.get('scorecard', [])
        if not scorecard:
            continue
        amitabh = json.loads(row['amitabh_players'])
        shivam = json.loads(row['shivam_players'])
        a_players, at = score_team(amitabh, row['amitabh_captain'], scorecard)
        s_players, st = score_team(shivam, row['shivam_captain'], scorecard)
        a_total += at
        s_total += st
        past_matches.append({
            'match_id': mid,
            'desc': KNOWN_MATCH_LABELS.get(mid, data.get('status', '')),
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
