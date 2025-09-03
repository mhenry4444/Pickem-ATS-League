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
    return len(games) != len(set(games))

# Function to check if submissions are still open
def is_submission_open(matchups, current_time):
    for game in matchups:
        game_time = datetime.strptime(game['date'], '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)
        if current_time >= game_time:
            return False  # First game started
    return True

# Set the current week (change this each week)
current_week = 1  # Update manually, e.g., 1 for Week 1

# Load games
matchups = load_matchups(current_week)

# Check submission deadline
current_time = datetime.now(timezone.utc)
if not is_submission_open(matchups, current_time):
    st.error("Submissions are closed for this week. The first game has started.")
else:
    # Create pick options: Two per game, away @ home format, spread on picked team, underdog first
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
            home_pick_str = f"{away} @ {home}"
            away_pick_str = f"{away} @ {home}"
        
        # Add underdog option first
        if home_spread is None:
            pick_options.append(away_pick_str)
            pick_options.append(home_pick_str)
        elif home_spread > 0:  # Home is underdog
            pick_options.append(home_pick_str)
            pick_options.append(away_pick_str)
        else:  # Away is underdog or pick'em
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
                # Remove existing picks for this user/week
                if not existing_picks.empty:
                    picks_df = picks_df[~((picks_df['Week'] == current_week) & 
                                        (picks_df['Name'].str.strip() == name.strip()) & 
                                        (picks_df['Email'].str.strip() == email.strip()))]
                picks_df = pd.concat([picks_df, pd.DataFrame([data])], ignore_index=True)
                picks_df.to_csv('picks.csv', index=False)
            else:
                pd.DataFrame([data]).to_csv('picks.csv', index=False)
            st.success("Your picks are submitted! Thanks!")

# Optional button to show standings
if st.button("View Current Standings"):
    if os.path.exists('standings.csv'):
        standings = pd.read_csv('standings.csv')
        st.dataframe(standings)
    else:
        st.info("No standings yet. Grade the picks first!")
