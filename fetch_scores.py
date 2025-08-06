import requests
import json

def fetch_scores(week, matchups_file):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week={week}"
    response = requests.get(url)
    if response.status_code != 200:
        print("Error fetching scores:", response.status_code)
        return []
    
    # Load matchups JSON for spreads
    with open(matchups_file, 'r') as f:
        matchups = json.load(f)
    spread_map = {(m['home'], m['away']): m['home_spread'] for m in matchups if m['home_spread'] is not None}
    
    events = response.json().get('events', [])
    outcomes = []
    for event in events:
        if event['status']['type']['completed']:
            competition = event['competitions'][0]
            home = competition['competitors'][0]
            away = competition['competitors'][1]
            home_score = int(home['score'])
            away_score = int(away['score'])
            winner = home['team']['abbreviation'] if home_score > away_score else away['team']['abbreviation'] if away_score > home_score else "Tie"
            
            # Get spread (not used for grading since straight-up, but included)
            key = (home['team']['abbreviation'], away['team']['abbreviation'])
            home_spread = spread_map.get(key)
            cover = "No spread"
            if home_spread is not None:
                if home_score + home_spread > away_score:
                    cover = home['team']['abbreviation']
                elif away_score - home_spread > home_score:
                    cover = away['team']['abbreviation']
                else:
                    cover = "Push"
            
            outcomes.append({
                'game_id': event['id'],
                'home': home['team']['abbreviation'],
                'away': away['team']['abbreviation'],
                'home_score': home_score,
                'away_score': away_score,
                'winner': winner,
                'home_spread': home_spread,
                'cover': cover
            })
    
    return outcomes

# How to use: Set week and the JSON file from Script 1
week = 1  # Change this
matchups_file = f'week{week}_matchups.json'
results = fetch_scores(week, matchups_file)
with open(f'week{week}_outcomes.json', 'w') as f:
    json.dump(results, f)
print(json.dumps(results, indent=2))