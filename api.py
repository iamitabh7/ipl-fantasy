from flask import Flask, jsonify, request
from flask_cors import CORS
import urllib.request
import json
import sqlite3
import time

app = Flask(__name__)
CORS(app)

API_KEY = 'af7e0d6342mshf4bafbb8b9f34a4p142027jsne77b07afae99'
API_HOST = 'cricbuzz-cricket.p.rapidapi.com'

def get_db():
    conn = sqlite3.connect('fantasy.db')
    conn.row_factory = sqlite3.Row
    return conn

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
    conn.commit()
    conn.close()

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

@app.route('/api/fixtures')
def get_fixtures():
    data = cricbuzz_get('/matches/v1/recent')
    matches = []
    for tm in data.get('typeMatches', []):
        for sm in tm.get('seriesMatches', []):
            wrap = sm.get('seriesAdWrapper', {})
            sname = wrap.get('seriesName', '')
            if 'Indian Premier League' not in sname:
                continue
            for m in wrap.get('matches', []):
                mi = m.get('matchInfo', {})
                ms = m.get('matchScore', {})
                t1 = mi.get('team1', {})
                t2 = mi.get('team2', {})
                t1score = ms.get('team1Score', {}).get('inngs1', {})
                t2score = ms.get('team2Score', {}).get('inngs1', {})
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
                    'venue': mi.get('venueInfo', {}).get('ground', ''),
                    'city': mi.get('venueInfo', {}).get('city', ''),
                })
    matches.sort(key=lambda x: x.get('start_date', ''), reverse=True)
    return jsonify(matches)

@app.route('/api/players/<match_id>')
def get_players(match_id):
    data = cricbuzz_get(f'/mcenter/v1/{match_id}/hscard')
    scorecard = data.get('scorecard', [])
    if not scorecard:
        return jsonify({'error': 'No player data yet. Match may not have started.', 'players': []})
    all_players = set()
    for innings in scorecard:
        for b in innings.get('batsman', []):
            all_players.add(b['name'])
        for b in innings.get('bowler', []):
            all_players.add(b['name'])
    header = data.get('matchHeader', {})
    return jsonify({
        'players': sorted(all_players),
        'team1': header.get('team1', {}).get('name', ''),
        'team2': header.get('team2', {}).get('name', ''),
        'status': data.get('status', ''),
        'match_id': match_id
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
    return jsonify({'success': True, 'message': 'Selections saved!'})

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
        return jsonify({'error': 'No selections found for this match'})
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
    past_matches = [
        {'match_id': '149618', 'desc': 'Match 1 - RCB vs SRH', 'amitabh_total': 312, 'shivam_total': 174},
        {'match_id': '149629', 'desc': 'Match 2 - MI vs KKR', 'amitabh_total': 295, 'shivam_total': 96},
        {'match_id': '149640', 'desc': 'Match 3 - RR vs CSK', 'amitabh_total': 142, 'shivam_total': 77},
        {'match_id': '149651', 'desc': 'Match 4 - GT vs PBKS', 'amitabh_total': 154, 'shivam_total': 191},
        {'match_id': '149662', 'desc': 'Match 5 - LSG vs DC', 'amitabh_total': 156, 'shivam_total': 58},
    ]
    a_total = sum(m['amitabh_total'] for m in past_matches)
    s_total = sum(m['shivam_total'] for m in past_matches)
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
        _, at = score_team(amitabh, row['amitabh_captain'], scorecard)
        _, st = score_team(shivam, row['shivam_captain'], scorecard)
        a_total += at
        s_total += st
        past_matches.append({
            'match_id': mid,
            'desc': data.get('status', ''),
            'amitabh_total': at,
            'shivam_total': st
        })
    return jsonify({
        'amitabh_total': a_total,
        'shivam_total': s_total,
        'matches': past_matches,
        'leader': 'amitabh' if a_total > s_total else 'shivam',
        'gap': abs(a_total - s_total)
    })

if __name__ == '__main__':
    init_db()
    print('\n🏏 IPL Fantasy API starting...')
    print('Running at http://localhost:8080\n')
    app.run(debug=True, port=8080)
