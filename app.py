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

# Create pick options: Two per game, one for each team with spread
pick_options = []
for g in matchups:
    home = g['home']
    away = g['away']
    home_spread = g['home_spread']
    if home_spread is not None:
        # Home spread as is (negative if favored)
        home_str = f"{home} ({home_spread:+}) vs {away}"  # + forces sign
        # Away spread is negative of home
        away_spread = -home_spread
        away_str = f"{away} ({away_spread:+}) vs {home}"
    else:
        home_str = f"{home} vs {away} (No spread)"
        away_str = f"{away} vs {home} (No spread)"
    pick_options.append(home_str)
    pick_options.append(away_str)

st.title(f"Football Pick'em League - Week {current_week}")

# Form for user input
with st.form(key='pick_form'):
    name = st.text_input("Your Name (type anything)")
    email = st.text_input("Your Email (type your address)")
    
    # Select exactly 5 picks (teams to cover)
    selected_picks = st.multiselect("Select EXACTLY 5 Teams to Cover the Spread (from any games)", pick_options, max_selections=5)
    if len(selected_picks) != 5:
        st.warning("You must select exactly 5 teams to submit.")
    
    # Player TD picker
    st.subheader("Pick 1 player to score at least 1 TD")
    player_td = st.text_input("Player Name (type full name, e.g., Patrick Mahomes)")
    
    submit = st.form_submit_button("Submit My Picks")
    
    if submit and len(selected_picks) == 5 and player_td.strip() != "":
        # Prepare data to save
        data = {'Week': current_week, 'Name': name, 'Email': email, 'PlayerTD': player_td}
        for i, pick in enumerate(selected_picks, 1):
            data[f'Pick{i}'] = pick  # Save full string, e.g., "DAL (-1) vs PHI"
        
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