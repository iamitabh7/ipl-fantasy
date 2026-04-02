import json

matches = [
    {
        'file': 'match1.json',
        'name': 'Match 1 - RCB vs SRH',
        'amitabh': ['Ishan Kishan', 'Phil Salt', 'Travis Head', 'Rajat Patidar', 'Romario Shepherd'],
        'amitabh_captain': 'Ishan Kishan',
        'shivam': ['Abhishek Sharma', 'Virat Kohli', 'Heinrich Klaasen', 'Harshal Patel', 'Bhuvneshwar Kumar'],
        'shivam_captain': 'Abhishek Sharma',
    },
    {
        'file': 'match2.json',
        'name': 'Match 2 - MI vs KKR',
        'amitabh': ['Rohit Sharma', 'Angkrish Raghuvanshi', 'Finn Allen', 'Hardik Pandya', 'Jasprit Bumrah'],
        'amitabh_captain': 'Angkrish Raghuvanshi',
        'shivam': ['Trent Boult', 'Cameron Green', 'Tilak Varma', 'Sunil Narine', 'Varun Chakaravarthy'],
        'shivam_captain': 'Cameron Green',
    },
    {
        'file': 'match3.json',
        'name': 'Match 3 - RR vs CSK',
        'amitabh': ['Shivam Dube', 'Matthew Short', 'Ayush Mhatre', 'Shimron Hetmyer', 'Vaibhav Sooryavanshi'],
        'amitabh_captain': 'Vaibhav Sooryavanshi',
        'shivam': ['Sanju Samson', 'Riyan Parag', 'Nandre Burger', 'Matt Henry', 'Ruturaj Gaikwad'],
        'shivam_captain': 'Sanju Samson',
    },
    {
        'file': 'match4.json',
        'name': 'Match 4 - GT vs PBKS',
        'amitabh': ['Shubman Gill', 'Sai Sudharsan', 'Glenn Phillips', 'Prabhsimran Singh', 'Priyansh Arya'],
        'amitabh_captain': 'Sai Sudharsan',
        'shivam': ['Jos Buttler', 'Shreyas Iyer', 'Marco Jansen', 'Washington Sundar', 'Mohammed Siraj'],
        'shivam_captain': 'Shreyas Iyer',
    },
    {
        'file': 'match5.json',
        'name': 'Match 5 - LSG vs DC',
        'amitabh': ['KL Rahul', 'Lungi Ngidi', 'Mitchell Marsh', 'Aiden Markram', 'Mohsin Khan'],
        'amitabh_captain': 'KL Rahul',
        'shivam': ['Nicholas Pooran', 'Mohammed Shami', 'Axar Patel', 'Anrich Nortje', 'Pathum Nissanka'],
        'shivam_captain': 'Nicholas Pooran',
    },
]

def calculate_points(player_name, is_captain, innings_list):
    runs = 0
    wickets = 0
    catches = 0
    runouts = 0
    stumpings = 0

    for innings in innings_list:
        for batsman in innings.get('batsman', []):
            if batsman['name'] == player_name:
                runs += batsman.get('runs', 0)

        for bowler in innings.get('bowler', []):
            if bowler['name'] == player_name:
                wickets += bowler.get('wickets', 0)

        for batsman in innings.get('batsman', []):
            outdec = batsman.get('outdec', '')
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
        'base_pts': runs + (wickets * 20) + (catches * 10) + (runouts * 10) + (stumpings * 10),
        'points': pts,
        'captain': is_captain
    }

amitabh_season = 0
shivam_season = 0

print("\n" + "="*60)
print("  IPL 2026 FANTASY — FULL SEASON RESULTS")
print("="*60)

for match in matches:
    try:
        with open(match['file'], 'r') as f:
            data = json.load(f)
    except:
        print(f"\n⚠️  {match['name']} — file not found, skipping")
        continue

    innings_list = data.get('scorecard', [])
    status = data.get('status', '?')

    print(f"\n{'─'*60}")
    print(f"  {match['name']}")
    print(f"  {status}")
    print(f"{'─'*60}")

    a_total = 0
    s_total = 0

    print(f"\n  🟡 AMITABH")
    for player in match['amitabh']:
        is_cap = (player == match['amitabh_captain'])
        r = calculate_points(player, is_cap, innings_list)
        cap = " ⭐C" if is_cap else ""
        print(f"  {r['name']}{cap}: {r['runs']}r {r['wickets']}w {r['catches']}c {r['runouts']}ro → {r['points']}pts")
        a_total += r['points']

    print(f"\n  🔵 SHIVAM")
    for player in match['shivam']:
        is_cap = (player == match['shivam_captain'])
        r = calculate_points(player, is_cap, innings_list)
        cap = " ⭐C" if is_cap else ""
        print(f"  {r['name']}{cap}: {r['runs']}r {r['wickets']}w {r['catches']}c {r['runouts']}ro → {r['points']}pts")
        s_total += r['points']

    winner = "🟡 Amitabh" if a_total > s_total else "🔵 Shivam"
    print(f"\n  Result: Amitabh {a_total} vs Shivam {s_total} → {winner} wins")

    amitabh_season += a_total
    shivam_season += s_total

print(f"\n{'='*60}")
print(f"  SEASON TOTALS")
print(f"  🟡 Amitabh: {amitabh_season} pts")
print(f"  🔵 Shivam:  {shivam_season} pts")
gap = abs(amitabh_season - shivam_season)
leader = "Amitabh" if amitabh_season > shivam_season else "Shivam"
print(f"  {leader} leads by {gap} pts")
print(f"{'='*60}\n")
