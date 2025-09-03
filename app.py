import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timezone, timedelta
from io import StringIO

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
    return len(games) != len(set(games))

# Function to get deadline (Sunday 9:15 AM PST of the current week)
def get_deadline(current_week):
    start_date = datetime(2025, 9, 5, tzinfo=timezone.utc)
    days_to_add = (current_week - 1) * 7
    week_start = start_date + pd.Timedelta(days=days_to_add)
    deadline = week_start + pd.Timedelta(days=2, hours=16, minutes=15)  # Sunday 9:15 AM PST
    return deadline

# Function to compute weekly scores (adapted from grade_picks.py)
def compute_weekly_scores(picks_csv_path, outcomes_json_path, matchups_file, week):
    try:
        picks_df = pd.read_csv(picks_csv_path)
        picks_df = picks_df[picks_df['Week'] == week]
        if picks_df.empty:
            return pd.DataFrame(columns=['Name', 'Email', f'Week {week}'])
        
        with open(outcomes_json_path, 'r') as f:
            outcomes = json.load(f)
        cover_map = {f"{o['home']} vs {o['away']}": o['cover'] for o in outcomes}
        
        td_scorers = set(['Christian McCaffrey', 'Saquon Barkley', 'Jalen Hurts'])  # Mock for testing
        
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
                        opponent = second_part.split(' (')[0].strip() if '(Pick' in second_part else second_part
                    else:
                        picked_team = second_part.split(' (')[0].strip()
                        opponent = first_team
                    game_key = f"{opponent} vs {picked_team}" if '(' in first_team else f"{picked_team} vs {opponent}"
                actual_cover = cover_map.get(game_key)
                if actual_cover and picked_team == actual_cover:
                    correct += 1.0
                elif actual_cover == "Push":
                    correct += 0.5
            
            player_td = row['PlayerTD'].strip()
            if player_td in td_scorers:
                correct += 1.0
            
            weekly_scores.append({'Name': name, 'Email': email, f'Week {week}': correct})
        
        return pd.DataFrame(weekly_scores)
    except Exception as e:
        print(f"Error computing weekly scores: {e}")
        return pd.DataFrame(columns=['Name', 'Email', f'Week {week}'])

# Initialize session state for download
if 'submission_success' not in st.session_state:
    st.session_state['submission_success'] = False
if 'picks_df' not in st.session_state:
    st.session_state['picks_df'] = None
if 'admin_authenticated' not in st.session_state:
    st.session_state['admin_authenticated'] = False

# Set the current week
current_week = 1  # Update manually each Wednesday

# Load games
matchups = load_matchups(current_week)

# Calculate deadline
deadline = get_deadline(current_week)
current_time = datetime.now(timezone.utc)

if current_time >= deadline:
    st.error(f"Submissions are closed for Week {current_week}. Deadline was Sunday, {deadline.astimezone(timezone(timedelta(hours=-7))).strftime('%Y-%m-%d %I:%M %p PST')}")
else:
    # Create pick options
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
            home_pick_str = f"{away} @ {home} (Pick)"
            away_pick_str = f"{away} (Pick) @ {home}"
        
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

    # Admin authentication for download
    admin_password = st.text_input("Admin Password (leave blank if submitting picks)", type="password")
    if admin_password == "Lock$3421":  # Replace with your chosen password
        st.session_state['admin_authenticated'] = True
    else:
        st.session_state['admin_authenticated'] = False

    # Form for user input
    with st.form(key='pick_form'):
        name = st.text_input("Your Name (type anything)")
        email = st.text_input("Your Email (type your address)")
        
        existing_picks = None
        if os.path.exists(r'C:\Users\matth\PYTHONTEST\Pickem ATS league\picks.csv'):
            try:
                picks_df = pd.read_csv(r'C:\Users\matth\PYTHONTEST\Pickem ATS league\picks.csv')
                existing_picks = picks_df[(picks_df['Week'] == current_week) & 
                                        (picks_df['Name'].str.strip() == name.strip()) & 
                                        (picks_df['Email'].str.strip() == email.strip())]
                if not existing_picks.empty:
                    st.warning("You already submitted picks for this week. Submitting again will override your previous picks and update the timestamp.")
            except:
                pass
        
        selected_picks = st.multiselect(
            "Select EXACTLY 5 Teams to Cover the Spread (from any games)",
            pick_options,
            max_selections=5
        )
        if len(selected_picks) != 5:
            st.warning("You must select exactly 5 teams to submit.")
        elif has_duplicate_games(selected_picks):
            st.error("You cannot pick both sides of the same game. Choose 5 different games.")
        
        st.subheader("Pick 1 player to score at least 1 TD")
        player_td = st.text_input("Player Name (type full name, e.g., Patrick Mahomes)")
        
        submit = st.form_submit_button("Submit My Picks")
        
        if submit and len(selected_picks) == 5 and not has_duplicate_games(selected_picks) and player_td.strip() != "":
            timestamp = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-7))).strftime('%Y-%m-%d %H:%M')
            data = {'Week': current_week, 'Name': name.strip(), 'Email': email.strip(), 'PlayerTD': player_td.strip(), 'Timestamp': timestamp}
            for i, pick in enumerate(selected_picks, 1):
                data[f'Pick{i}'] = pick
            
            # Save to specified local path
            picks_path = r'C:\Users\matth\PYTHONTEST\Pickem ATS league\picks.csv'
            if os.path.exists(picks_path):
                picks_df = pd.read_csv(picks_path)
                if 'Timestamp' not in picks_df.columns:
                    picks_df['Timestamp'] = ''
                if not existing_picks.empty:
                    picks_df = picks_df[~((picks_df['Week'] == current_week) & 
                                        (picks_df['Name'].str.strip() == name.strip()) & 
                                        (picks_df['Email'].str.strip() == email.strip()))]
                picks_df = pd.concat([picks_df, pd.DataFrame([data])], ignore_index=True)
                picks_df.to_csv(picks_path, index=False)
                st.session_state['submission_success'] = True
                st.session_state['picks_df'] = picks_df
                st.success(f"Your picks are submitted locally to {picks_path}! Please upload picks.csv to GitHub to persist changes.")
            else:
                pd.DataFrame([data]).to_csv(picks_path, index=False)
                st.session_state['submission_success'] = True
                st.session_state['picks_df'] = pd.DataFrame([data])
                st.success(f"Your picks are submitted locally to {picks_path}! Please upload picks.csv to GitHub to persist changes.")

    # Display download button only for admin
    if st.session_state.get('submission_success', False) and st.session_state.get('admin_authenticated', False):
        if st.session_state['picks_df'] is not None:
            csv_buffer = StringIO()
            st.session_state['picks_df'].to_csv(csv_buffer, index=False)
            st.download_button(label="Download picks.csv", data=csv_buffer.getvalue(), file_name="picks.csv", mime="text/csv")
        st.session_state['submission_success'] = False  # Reset after download option is shown

# Leaderboard
if st.button("View Current Standings"):
    if os.path.exists(r'C:\Users\matth\PYTHONTEST\Pickem ATS league\picks.csv'):
        standings_df = pd.read_csv('standings.csv') if os.path.exists('standings.csv') else pd.DataFrame(columns=['Name', 'Total Correct'])
        
        picks_df = pd.read_csv(r'C:\Users\matth\PYTHONTEST\Pickem ATS league\picks.csv')
        weeks = sorted(picks_df['Week'].unique())
        weekly_dfs = []
        for week in weeks:
            outcomes_file = f'week{week}_outcomes.json'
            matchups_file = f'week{week}_matchups.json'
            if os.path.exists(outcomes_file) and os.path.exists(matchups_file):
                weekly_df = compute_weekly_scores(r'C:\Users\matth\PYTHONTEST\Pickem ATS league\picks.csv', outcomes_file, matchups_file, week)
                if not weekly_df.empty:
                    weekly_dfs.append(weekly_df)
        
        if weekly_dfs:
            leaderboard_df = weekly_dfs[0]
            for df in weekly_dfs[1:]:
                leaderboard_df = leaderboard_df.merge(df, on=['Name', 'Email'], how='outer')
            leaderboard_df = leaderboard_df.fillna(0.0)
            if not standings_df.empty:
                leaderboard_df = leaderboard_df.merge(standings_df[['Name', 'Total Correct']], on='Name', how='outer').fillna(0.0)
            else:
                leaderboard_df['Total Correct'] = leaderboard_df[[col for col in leaderboard_df.columns if col.startswith('Week ')]].sum(axis=1)
            
            leaderboard_df = leaderboard_df.sort_values('Total Correct', ascending=False).reset_index(drop=True)
            leaderboard_df['Rank'] = leaderboard_df.index + 1
            weekly_cols = [col for col in leaderboard_df.columns if col.startswith('Week ')]
            leaderboard_df = leaderboard_df[['Rank', 'Name', 'Email'] + weekly_cols + ['Total Correct']]
            st.dataframe(leaderboard_df, hide_index=True)
        else:
            st.info("No standings or weekly scores available. Grade picks first!")
    else:
        st.info("No picks yet. Submit picks and grade them!")
