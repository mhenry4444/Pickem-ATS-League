import pandas as pd
import json
import requests
import os

def fetch_td_scorers(week, matchups_file):
    try:
        with open(matchups_file, 'r') as f:
            matchups = json.load(f)
    except FileNotFoundError:
        print(f"Error: {matchups_file} not found.")
        return set()
    
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
                                break
    return td_scorers

def grade_picks(picks_csv_path='picks.csv', outcomes_json_path=None, matchups_file=None, override_json_path=None, week=None, output_csv_path='standings.csv'):
    # Load picks from CSV
    try:
        picks_df = pd.read_csv(picks_csv_path)
    except FileNotFoundError:
        print(f"Error: {picks_csv_path} not found. Make sure friends submitted picks via the app.")
        return
    
    if week is None or outcomes_json_path is None or matchups_file is None:
        print("Error: Provide week, outcomes_json_path, and matchups_file.")
        return
    
    # Filter to this week
    picks_df = picks_df[picks_df['Week'] == week]
    
    # Fetch TD scorers
    td_scorers = fetch_td_scorers(week, matchups_file)
    
    # Load outcomes
    with open(outcomes_json_path, 'r') as f:
        outcomes = json.load(f)
    cover_map = {f"{o['home']} vs {o['away']}": o['cover'] for o in outcomes}
    
    weekly_scores = []
    for _, row in picks_df.iterrows():
        name = row['Name']
        email = row['Email']
        correct = 0.0
        for i in range(1, 6):
            pick_str = row[f'Pick{i}']
            if ' @ ' in pick_str:
                parts = pick_str.split(' @ ')
                first_team = parts[0].strip()
                second_part = parts[1].strip()
                if '(' in first_team:
                    picked_team = first_team.split(' (')[0].strip()
                    spread = float(second_part.split(')')[0].split('(')[1]) if '(' in second_part else 0.0
                    opponent = second_part.split(' (')[0].strip() if '(Pick' in second_part else second_part
                else:
                    picked_team = second_part.split(' (')[0].strip()
                    spread = float(first_team.split(')')[0].split('(')[1]) if '(' in first_team else 0.0
                    opponent = first_team
                game_key = f"{opponent} vs {picked_team}" if '(' in first_team else f"{picked_team} vs {opponent}"
                actual_cover = cover_map.get(game_key)
                if actual_cover:
                    if actual_cover == "Push" and spread == 0.0:  # Handle pick'em as 0-point spread
                        correct += 0.5
                    elif picked_team == actual_cover:
                        correct += 1.0
        
        # Grade Player TD bonus
        player_td = row['PlayerTD'].strip()
        if player_td in td_scorers:
            correct += 1.0
        
        weekly_scores.append({'Name': name, 'Week': week, 'Correct': correct})
    
    weekly_df = pd.DataFrame(weekly_scores)
    
    # Update cumulative standings
    if os.path.exists(output_csv_path):
        try:
            standings_df = pd.read_csv(output_csv_path)
        except:
            standings_df = pd.DataFrame(columns=['Name', 'Total Correct'])
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
    print(f"Standings updated! Open {output_csv_path} to view.")

# How to use: Set week and JSON files
week = 1  # Change this
outcomes_json_path = f'week{week}_outcomes.json'
matchups_file = f'week{week}_matchups.json'
override_json_path = f'week{week}_overrides.json'  # Optional
grade_picks(week=week, outcomes_json_path=outcomes_json_path, matchups_file=matchups_file, override_json_path=override_json_path)