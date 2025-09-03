import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timezone

# Function to load JSON (game data from fetch_matchups.py)
def load_matchups(week):
    file = f'week{week}_matchups.json'
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    else:
        st.error(f"Missing file: {file}. Run fetch_matchups.py first!")
        return []

# Function to check for duplicate games in picks
def has_duplicate_games(selected_picks):
    games = []
    for pick in selected_picks:
        if ' @ ' in pick:
            parts = pick.split(' @ ')
            away = parts[0].split(' (')[0].strip()
            home = parts[1].split(' (')[0].strip()
            game = f"{away} @ {home}"
            games.append(game)
        elif ' vs ' in pick:
            parts = pick.split(' vs ')
            away = parts[0].strip()
            home = parts[1].split(' (')[0].strip()
            game = f"{away} @ {home}"
            games.append(game)
    return len(games) != len(set(games))

# Function to check if submissions are still open
def is_submission_open(matchups, current_time):
    for game in matchups:
        game_time = datetime.strptime(game['date'], '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)
        if current_time >= game_time:
            return False
    return True

# Function to compute weekly scores (adapted from grade_picks.py)
def compute_weekly_scores(picks_csv_path, outcomes_json_path, matchups_file, week):
    try:
        picks_df = pd.read_csv(picks_csv_path)
        picks_df = picks_df[picks_df['Week'] == week]
        if picks_df.empty:
            return pd.DataFrame(columns=['Name', f'Week {week}'])
        
        with open(outcomes_json_path, 'r') as f:
            outcomes = json.load(f)
        cover_map = {f"{o['home']} vs {o['away']}": o['cover'] for o in outcomes}
        
        # Mock TD scorers for testing (replace with fetch_td_scorers in production)
        td_scorers = set(['Christian McCaffrey', 'Saquon Barkley', 'Jalen Hurts'])  # Adjust for real API
        
        weekly_scores = []
        for _, row in picks_df.iterrows():
            name = row['Name']
            correct = 0.0
            for i in range(1, 6):
                pick_str = row[f'Pick{i}']
                if ' @ ' in pick_str:
                    parts = pick_str.split(' @ ')
                    first_team = parts[0].strip()
                    second_part = parts[1].strip()
                    if '(' in first_team:
                        picked_team = first_team.split(' (')[0].strip()
                        opponent = second_part
                    else:
                        picked_team = second_part.split(' (')[0].strip()
                        opponent = first_team
                    game_key = f"{opponent} vs {picked_team}" if '(' in first_team else f"{picked_team} vs {opponent}"
                elif ' vs ' in pick_str:
                    parts = pick_str.split(' vs ')
                    picked_team = parts[0].strip()
                    opponent = parts[1].split(' (')[0].strip()
                    game_key = f"{picked_team} vs {opponent}"
                
                actual_cover = cover_map.get(game_key)
                if actual_cover and picked_team == actual_cover:
                    correct += 1.0
                elif actual_cover == "Push":
                    correct += 0.5
            
            player_td = row['PlayerTD'].strip()
            if player_td in td_scorers:
                correct += 1.0
            
            weekly_scores.append({'Name': name, f'Week {week}': correct})
        
        return pd.DataFrame(weekly_scores)
    except:
        return pd.DataFrame(columns=['Name', f'Week {week}'])

# Set the current week
current_week = 1  # Update manually

# Load games
matchups = load_matchups(current_week)

# Check submission deadline
current_time = datetime.now(timezone.utc)
if not is_submission_open(matchups, current_time):
    st.error("Submissions are closed for this week. The first game has started.")
else:
    # Create pick options: Two per game, away vs home for pick'em, spread on picked team
    pick_options = []
    for g in matchups:
        home = g['home']
        away = g['away']
        home_spread = g['home_spread']
        if home_spread is not None:
            away_spread = -home_spread
            home_pick_str = f"{away} @ {home} ({home_spread:+})"
            away_pick_str = f"{away} ({away_spread:+}) @ {home}"
        else:
            home_pick_str = f"{home} vs {away} (Pick)"
            away_pick_str = f"{away} vs {home} (Pick)"
        
        # Add underdog option first
        if home_spread is None:
            pick_options.append(away_pick_str)
            pick_options.append(home_pick_str)
        elif home_spread > 0:
            pick_options.append(home_pick_str)
            pick_options.append(away_pick_str)
        else:
            pick_options.append(away_pick_str)
            pick_options.append(home_pick_str)

    st.title(f"Football Pick'em League - Week {current_week}")

    # Form for user input
    with st.form(key='pick_form'):
        name = st.text_input("Your Name (type anything)")
        email = st.text_input("Your Email (type your address)")
        
        # Check for existing submission
        existing_picks = None
        if os.path.exists('picks.csv'):
            try:
                picks_df = pd.read_csv('picks.csv')
                existing_picks = picks_df[(picks_df['Week'] == current_week) & 
                                        (picks_df['Name'].str.strip() == name.strip()) & 
                                        (picks_df['Email'].str.strip() == email.strip())]
                if not existing_picks.empty:
                    st.warning("You already submitted picks for this week. Submitting again will override your previous picks.")
            except:
                pass
        
        # Select exactly 5 teams to cover the spread
        selected_picks = st.multiselect(
            "Select EXACTLY 5 Teams to Cover the Spread (from any games)",
            pick_options,
            max_selections=5
        )
        if len(selected_picks) != 5:
            st.warning("You must select exactly 5 teams to submit.")
        elif has_duplicate_games(selected_picks):
            st.error("You cannot pick both sides of the same game. Choose 5 different games.")
        
        # Player TD picker
        st.subheader("Pick 1 player to score at least 1 TD")
        player_td = st.text_input("Player Name (type full name, e.g., Patrick Mahomes)")
        
        submit = st.form_submit_button("Submit My Picks")
        
        if submit and len(selected_picks) == 5 and not has_duplicate_games(selected_picks) and player_td.strip() != "":
            # Prepare data to save
            data = {'Week': current_week, 'Name': name.strip(), 'Email': email.strip(), 'PlayerTD': player_td.strip()}
            for i, pick in enumerate(selected_picks, 1):
                data[f'Pick{i}'] = pick
            
            # Load existing picks or create new DataFrame
            if os.path.exists('picks.csv'):
                picks_df = pd.read_csv('picks.csv')
                if not existing_picks.empty:
                    picks_df = picks_df[~((picks_df['Week'] == current_week) & 
                                        (picks_df['Name'].str.strip() == name.strip()) & 
                                        (picks_df['Email'].str.strip() == email.strip()))]
                picks_df = pd.concat([picks_df, pd.DataFrame([data])], ignore_index=True)
                picks_df.to_csv('picks.csv', index=False)
            else:
                pd.DataFrame([data]).to_csv('picks.csv', index=False)
            st.success("Your picks are submitted! Thanks!")

# Leaderboard
if st.button("View Current Standings"):
    if os.path.exists('standings.csv') or os.path.exists('picks.csv'):
        # Load cumulative standings
        standings_df = pd.read_csv('standings.csv') if os.path.exists('standings.csv') else pd.DataFrame(columns=['Name', 'Total Correct'])
        
        # Compute weekly scores for all weeks
        weekly_dfs = []
        if os.path.exists('picks.csv'):
            picks_df = pd.read_csv('picks.csv')
            weeks = picks_df['Week'].unique()
            for week in weeks:
                outcomes_file = f'week{week}_outcomes.json'
                matchups_file = f'week{week}_matchups.json'
                if os.path.exists(outcomes_file) and os.path.exists(matchups_file):
                    weekly_df = compute_weekly_scores('picks.csv', outcomes_file, matchups_file, week)
                    if not weekly_df.empty:
                        weekly_dfs.append(weekly_df)
        
        # Merge weekly scores
        if weekly_dfs:
            leaderboard_df = weekly_dfs[0]
            for df in weekly_dfs[1:]:
                leaderboard_df = leaderboard_df.merge(df, on='Name', how='outer')
            # Merge with cumulative totals
            if not standings_df.empty:
                leaderboard_df = leaderboard_df.merge(standings_df[['Name', 'Total Correct']], on='Name', how='outer')
            leaderboard_df = leaderboard_df.fillna(0)
            st.dataframe(leaderboard_df)
        else:
            st.info("No standings or weekly scores available. Grade picks first!")
    else:
        st.info("No standings or picks yet. Submit picks and grade them!")
