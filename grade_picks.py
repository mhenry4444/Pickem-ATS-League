import pandas as pd
import json
import requests

def fetch_td_scorers(week, matchups_file):
    # Load matchups to get game_ids
    with open(matchups_file, 'r') as f:
        matchups = json.load(f)
    game_ids = [g['game_id'] for g in matchups]
    
    td_scorers = set()
    for game_id in game_ids:
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={game_id}"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error fetching boxscore for {game_id}: {response.status_code}")
            continue
        data = response.json()
        if 'boxscore' not in data or 'players' not in data['boxscore']:
            continue
        
        for team_players in data['boxscore']['players']:
            for stat_category in team_players['statistics']:
                if 'athletes' in stat_category:
                    for athlete in stat_category['athletes']:
                        stats = {k: v for k, v in zip(stat_category['keys'], athlete['stats'])}
                        td_keys = ['passingTouchdowns', 'rushingTouchdowns', 'receivingTouchdowns']
                        for key in td_keys:
                            if key in stats and int(stats[key]) > 0:
                                td_scorers.add(athlete['athlete']['displayName'])
                                break  # Add once per player per game
    
    return td_scorers

def grade_picks(picks_csv_path='picks.csv', outcomes_json_path=None, matchups_file=None, week=None, output_csv_path='standings.csv'):
    # Load picks from CSV
    picks_df = pd.read_csv(picks_csv_path)
    
    if week is None or outcomes_json_path is None or matchups_file is None:
        print("Error: Provide week, outcomes_json_path, and matchups_file.")
        return
    
    # Filter to this week
    picks_df = picks_df[picks_df['Week'] == week]
    
    # Load outcomes (with covers and spreads)
    with open(outcomes_json_path, 'r') as f:
        outcomes = json.load(f)
    
    # Map game to cover for quick lookup (use "HOME vs AWAY" as key)
    cover_map = {f"{o['home']} vs {o['away']}": o['cover'] for o in outcomes}
    
    # Fetch TD scorers
    td_scorers = fetch_td_scorers(week, matchups_file)
    
    # Grade each participant (ATS + TD bonus)
    standings = []
    for _, row in picks_df.iterrows():
        username = row['Name']
        correct = 0
        for i in range(1, 6):
            pick_str = row[f'Pick{i}']
            # Parse pick_str, e.g., "PHI @ DAL (+7.0)" or "PHI (-7.0) @ DAL"
            if ' @ ' in pick_str:
                parts = pick_str.split(' @ ')
                away_team = parts[0].strip()
                home_part = parts[1].strip()
                if '(' in away_team:
                    # Spread on away: picking away, e.g., "PHI (-7.0) @ DAL" -> picked = PHI, game = PHI vs DAL
                    picked_team = away_team.split(' (')[0].strip()
                    opponent = home_part
                else:
                    # Spread on home: picking home, e.g., "PHI @ DAL (+7.0)" -> picked = DAL, game = DAL vs PHI but normalize
                    picked_team = home_part.split(' (')[0].strip()
                    opponent = away_team
                # Game key always home vs away? No, since home/away are fixed, but since away is first, home second
                # Assume first is away, second is home
                game_key = f"{away_team.split(' (')[0]} vs {home_part.split(' (')[0]}"
                actual_cover = cover_map.get(game_key)
                if actual_cover and picked_team == actual_cover:
                    correct += 1
        
        # TD bonus
        player = row['PlayerTD'].strip()
        if player in td_scorers:
            correct += 1
        
        standings.append({'Username': username, 'Correct Picks': correct})
    
    # Sort and save (accumulate by loading prior if needed)
    standings_df = pd.DataFrame(standings).sort_values('Correct Picks', ascending=False)
    standings_df.to_csv(output_csv_path, index=False)
    print("Standings saved to", output_csv_path)

# Example usage
week = 1
grade_picks(week=week, outcomes_json_path=f'week{week}_outcomes.json', matchups_file=f'week{week}_matchups.json')