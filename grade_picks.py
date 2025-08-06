import pandas as pd
import json

def grade_picks(picks_csv_path='picks.csv', outcomes_json_path=None, week=None, output_csv_path='standings.csv'):
    # Load picks from CSV
    picks_df = pd.read_csv(picks_csv_path)
    
    if week is None or outcomes_json_path is None:
        print("Error: Provide week and outcomes_json_path.")
        return
    
    # Filter to this week
    picks_df = picks_df[picks_df['Week'] == week]
    
    # Load outcomes JSON
    with open(outcomes_json_path, 'r') as f:
        outcomes = json.load(f)
    
    # Map "HOME vs AWAY" to winner
    winner_map = {f"{o['home']} vs {o['away']}": o['winner'] for o in outcomes}
    
    # Score each person
    weekly_scores = []
    for _, row in picks_df.iterrows():
        name = row['Name']
        correct = 0
        for i in range(1, 6):
            game_str = row[f'Game{i}']
            pick = row[f'Pick{i}']
            actual_winner = winner_map.get(game_str)
            if actual_winner and pick == actual_winner:
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

# How to use: Set week and JSON file
week = 1  # Change this
outcomes_json_path = f'week{week}_outcomes.json'
grade_picks(week=week, outcomes_json_path=outcomes_json_path)