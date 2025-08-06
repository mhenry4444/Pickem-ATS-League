import requests
import json
from datetime import datetime

def fetch_matchups(week, api_key):
    # ESPN API for schedule
    espn_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week={week}"
    espn_response = requests.get(espn_url)
    if espn_response.status_code != 200:
        print("Error fetching ESPN data:", espn_response.status_code)
        return []
    
    events = espn_response.json().get('events', [])
    
    # The Odds API for spreads
    odds_url = f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/?apiKey={api_key}&regions=us&markets=spreads&oddsFormat=american"
    odds_response = requests.get(odds_url)
    if odds_response.status_code != 200:
        print("Error fetching odds data:", odds_response.status_code)
        return []
    
    odds_data = odds_response.json()
    odds_map = {}
    # Team name mapping (Odds API uses full names, ESPN uses short; add more if errors)
    team_map = {
        'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL', 'Buffalo Bills': 'BUF',
        'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI', 'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE',
        'Dallas Cowboys': 'DAL', 'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
        'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX', 'Kansas City Chiefs': 'KC',
        'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC', 'Los Angeles Rams': 'LAR', 'Miami Dolphins': 'MIA',
        'Minnesota Vikings': 'MIN', 'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG',
        'New York Jets': 'NYJ', 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT', 'San Francisco 49ers': 'SF',
        'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB', 'Tennessee Titans': 'TEN', 'Washington Commanders': 'WAS'
    }
    for game in odds_data:
        home_full = game['home_team']
        away_full = game['away_team']
        home = team_map.get(home_full, home_full.upper()[:3])  # Fallback to first 3 letters
        away = team_map.get(away_full, away_full.upper()[:3])
        key = f"{away}@{home}"
        if game['bookmakers']:
            markets = game['bookmakers'][0]['markets']  # First bookmaker
            if markets and markets[0]['key'] == 'spreads':
                outcomes = markets[0]['outcomes']
                home_spread = next((o['point'] for o in outcomes if o['name'] == home_full), None)
                odds_map[key] = home_spread
    
    matchups = []
    for event in events:
        competition = event['competitions'][0]
        home = competition['competitors'][0]['team']['abbreviation']
        away = competition['competitors'][1]['team']['abbreviation']
        key = f"{away}@{home}"
        game_id = event['id']
        date = datetime.fromisoformat(event['date'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
        
        home_spread = odds_map.get(key)
        spread_str = f"{home} ({home_spread}) vs {away}" if home_spread else f"{home} vs {away} (No spread)"
        
        matchups.append({
            'game_id': game_id,
            'home': home,
            'away': away,
            'date': date,
            'home_spread': home_spread,  # Numerical for later use
            'spread_str': spread_str  # For display
        })
    
    return matchups

# How to use: Set your API key and week number
api_key = '75344137e305dc8b4fd8bf1c6c8a3f59'  # Replace this!
week = 1  # Change to the week you want (1-18 for NFL)
games = fetch_matchups(week, api_key)
with open(f'week{week}_matchups.json', 'w') as f:
    json.dump(games, f)
print(json.dumps(games, indent=2))  # This shows the data in your command line