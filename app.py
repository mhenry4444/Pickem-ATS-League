import streamlit as st
import pandas as pd
import json
import os

# Function to load JSON (simple data file)
def load_matchups(week):
    file = f'week{week}_matchups.json'
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    else:
        st.error(f"Missing file: {file}. Run fetch_matchups.py first!")
        return []

# Set the current week (change this each week)
current_week = 1  # Update manually

# Load games
matchups = load_matchups(current_week)
game_options = {g['spread_str']: {'home': g['home'], 'away': g['away'], 'clean': f"{g['home']} vs {g['away']}"} for g in matchups}

st.title(f"Football Pick'em League - Week {current_week}")

# Form for user input
with st.form(key='pick_form'):
    name = st.text_input("Your Name (type anything)")
    email = st.text_input("Your Email (type your address)")
    
    # Pick exactly 5 games from dropdown
    selected_games = st.multiselect("Select EXACTLY 5 Games (spreads shown just for info)", list(game_options.keys()), max_selections=5)
    if len(selected_games) != 5:
        st.warning("You must select exactly 5 games to submit.")
    
    # For each game, choose winner
    picks = {}
    for game_str in selected_games:
        teams = game_options[game_str]
        pick = st.selectbox(f"Pick the winner for {game_str}", [teams['home'], teams['away'], "No Pick"])
        picks[game_str] = pick
    
    submit = st.form_submit_button("Submit My Picks")
    
    if submit and len(selected_games) == 5 and all(p != "No Pick" for p in picks.values()):
        # Prepare data to save
        data = {'Week': current_week, 'Name': name, 'Email': email}
        for i, game in enumerate(selected_games, 1):
            data[f'Game{i}'] = game_options[game]['clean']  # Save as "HOME vs AWAY"
            data[f'Pick{i}'] = picks[game]
        
        # Save to picks.csv (creates if not exists)
        df = pd.DataFrame([data])
        if os.path.exists('picks.csv'):
            df.to_csv('picks.csv', mode='a', header=False, index=False)
        else:
            df.to_csv('picks.csv', index=False)
        st.success("Your picks are submitted! Thanks!")

# Optional button to show standings (after grading)
if st.button("View Current Standings"):
    if os.path.exists('standings.csv'):
        standings = pd.read_csv('standings.csv')
        st.dataframe(standings)
    else:
        st.info("No standings yet. Grade the picks first!")