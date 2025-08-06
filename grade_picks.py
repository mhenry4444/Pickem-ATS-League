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
    
    # Load outcomes JSON for ATS covers
    with open(outcomes_json_path, 'r') as f:
        outcomes = json.load(f)
    
    # Map game to cover: key as "HOME vs AWAY"
    cover_map = {f"{o['home']} vs {o['away']}": o['cover'] for o in outcomes}
    
    # Fetch TD scorers for bonus
    td_scorers = fetch_td_scorers(week, matchups_file)
    
    # Grade each person
    weekly_scores = []
    for _, row in picks_df.iterrows():
        name = row['Name']
        correct = 0
        # Grade 5 ATS picks
        for i in range(1, 6):
            pick_str = row[f'Pick{i}']
            # Parse: "Pick DAL to cover (-1) vs PHI" -> picked_team = 'DAL', game_str = 'DAL vs PHI' or depending
            if ' to cover ' in pick_str:
                parts = pick_str.split(' to cover ')
                picked_team = parts[0].replace('Pick ', '').strip()
                rest = parts[1]
                vs_pos = rest.find(' vs ')
                spread_str = rest[:vs_pos]  # '(-1)'
                opponent = rest[vs_pos + 4:].strip()
                # Determine game key: Try both orders
                game_key1 = f"{picked_team} vs {opponent}"
                game_key2 = f"{opponent} vs {picked_team}"
                actual_cover = cover_map.get(game_key1) or cover_map.get(game_key2)
                if actual_cover and picked_team == actual_cover:
                    correct += 1
        
        # Grade Player TD bonus (1 point if they scored any TD)
        player_td = row['PlayerTD'].strip()
        if player_td in td_scorers:
            correct += 1
        
        weekly_scores.append({'Name': name, 'Week': week, 'Correct': correct})
    
    weekly_df = pd.DataFrame(weekly_scores)
    
    # Update cumulative standings
    if os.path.exists(output_csv_path):
        standings_df = pd.read_csv(output_csv_path)
        for _, wrow in weekly_df.iterrows():
            if wrow['Name'] in standings_df['Name'].values:
                standings_df.loc[standings_df['Name'] == wrow['Name'], 'Total Correct'] += wrow['Correct']
            else:
                new_row = pd.DataFrame({'Name': [wrow['Name']], 'Total Correct': [wrow['Correct']]})
                standings_df = pd.concat([standings_df, new_row], ignore_index=True)
    else:
        standings_df = weekly_df[['Name']].copy()
        standings_df['Total Correct'] = weekly_df['Correct']
    
    # Sort and save
    standings_df = standings_df.sort_values('Total Correct', ascending=False)
    standings_df.to_csv(output_csv_path, index=False)
    print("Standings updated! Open standings.csv to view.")

# How to use: Set week, JSON files
week = 1  # Change this
outcomes_json_path = f'week{week}_outcomes.json'
matchups_file = f'week{week}_matchups.json'
grade_picks(week=week, outcomes_json_path=outcomes_json_path, matchups_file=matchups_file)