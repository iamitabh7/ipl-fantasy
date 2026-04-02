import urllib.request
import json

API_KEY = 'af7e0d6342mshf4bafbb8b9f34a4p142027jsne77b07afae99'
API_HOST = 'cricbuzz-cricket.p.rapidapi.com'

def api_get(path):
    url = f'https://{API_HOST}{path}'
    req = urllib.request.Request(url, headers={
        'x-rapidapi-host': API_HOST,
        'x-rapidapi-key': API_KEY
    })
    return json.loads(urllib.request.urlopen(req).read())

def fetch_players(match_id):
    data = api_get(f'/mcenter/v1/{match_id}/hscard')
    status = data.get('status', '')
    
    # Get team names from appindex
    app = data.get('appindex', {})
    title = app.get('seotitle', '')
    
    # Get players from both innings squads
    players = {}
    scorecard = data.get('scorecard', [])
    
    # Also try getting from commentary/match header
    header = data.get('matchHeader', {})
    team1 = header.get('team1', {}).get('name', 'Team 1')
    team2 = header.get('team2', {}).get('name', 'Team 2')
    
    # Collect all unique player names from batting + bowling
    team1_players = set()
    team2_players = set()
    
    for i, innings in enumerate(scorecard):
        names = set()
        for b in innings.get('batsman', []):
            names.add(b['name'])
        for b in innings.get('bowler', []):
            names.add(b['name'])
        if i == 0:
            team1_players = names
        else:
            team2_players = names
    
    return team1, team2, sorted(team1_players), sorted(team2_players), status

def pick_players(team_name, all_players, label):
    print(f"\n{'='*55}")
    print(f"  {team_name} — Available Players")
    print(f"{'='*55}")
    for i, name in enumerate(all_players, 1):
        print(f"  {i:2}. {name}")
    
    print(f"\n  Select 5 players for {label}")
    print(f"  Enter 5 numbers separated by spaces (e.g. 1 3 5 7 9):")
    
    while True:
        try:
            picks = list(map(int, input("  > ").strip().split()))
            if len(picks) != 5:
                print("  ❌ Please pick exactly 5 players!")
                continue
            if any(p < 1 or p > len(all_players) for p in picks):
                print(f"  ❌ Numbers must be between 1 and {len(all_players)}")
                continue
            selected = [all_players[p-1] for p in picks]
            break
        except ValueError:
            print("  ❌ Please enter numbers only!")
    
    print(f"\n  Your picks:")
    for i, name in enumerate(selected, 1):
        print(f"  {i}. {name}")
    
    print(f"\n  Who is {label}'s captain? Enter number (1-5):")
    while True:
        try:
            cap = int(input("  > ").strip())
            if cap < 1 or cap > 5:
                print("  ❌ Enter a number between 1 and 5")
                continue
            captain = selected[cap-1]
            break
        except ValueError:
            print("  ❌ Please enter a number!")
    
    print(f"\n  ✅ {label}'s team: {', '.join(selected)}")
    print(f"  ⭐ Captain: {captain}")
    
    return selected, captain

def main():
    print("\n" + "="*55)
    print("  IPL 2026 FANTASY — MATCH SETUP")
    print("="*55)
    
    match_id = input("\n  Enter match ID: ").strip()
    
    print(f"\n  Fetching players for match {match_id}...")
    
    try:
        team1, team2, t1_players, t2_players, status = fetch_players(match_id)
    except Exception as e:
        print(f"  ❌ Error fetching data: {e}")
        return
    
    if not t1_players and not t2_players:
        print("  ❌ No player data found. Match may not have started yet.")
        print("  Run this script after the toss when Playing XI is announced.")
        return
    
    all_players = sorted(t1_players | t2_players)
    
    print(f"\n  ✅ Found {len(all_players)} players!")
    print(f"  Match: {status}")
    
    # Amitabh picks
    amitabh_players, amitabh_captain = pick_players(
        f"{team1} + {team2}", all_players, "Amitabh"
    )
    
    # Shivam picks
    shivam_players, shivam_captain = pick_players(
        f"{team1} + {team2}", all_players, "Shivam"
    )
    
    # Save to file
    match_data = {
        'match_id': match_id,
        'status': status,
        'amitabh': amitabh_players,
        'amitabh_captain': amitabh_captain,
        'shivam': shivam_players,
        'shivam_captain': shivam_captain
    }
    
    with open('current_match.json', 'w') as f:
        json.dump(match_data, f, indent=2)
    
    print(f"\n{'='*55}")
    print(f"  ✅ Selections saved to current_match.json!")
    print(f"  After the match, run: python3 scorer.py")
    print(f"{'='*55}\n")

if __name__ == '__main__':
    main()
