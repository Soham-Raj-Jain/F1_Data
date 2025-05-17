import pandas as pd
import streamlit as st
import json
from urllib.request import urlopen
from streamlit_autorefresh import st_autorefresh

# Page config
st.set_page_config(layout="wide", page_title="Live F1 Lap Times", page_icon="🏎️")
st_autorefresh(interval=10000, key="datarefresh")  # refresh every 10s

# Driver and team mappings
driver_names = {
    1: 'Max Verstappen', 16: 'Charles Leclerc', 44: 'Lewis Hamilton', 12: 'Kimi Antonelli',
    63: 'George Russell', 22: 'Yuki Tsunoda', 6: 'Isack Hadjar', 30: 'Liam Lawson',
    14: 'Fernando Alonso', 18: 'Lance Stroll', 4: 'Lando Norris', 81: 'Oscar Piastri',
    43: 'Franco Colapinto', 10: 'Pierre Gasly', 23: 'Alexander Albon', 55: 'Carlos Sainz',
    31: 'Esteban Ocon', 87: 'Oliver Bearman', 27: 'Nico Hulkenberg', 5: 'Gabriel Bortoleto'
}

driver_team = {
    12: 'Mercedes', 63: 'Mercedes', 1: 'Red Bull Racing', 22: 'Red Bull Racing',
    16: 'Ferrari', 44: 'Ferrari', 4: 'McLaren', 81: 'McLaren',
    18: 'Aston Martin', 43: 'Alpine', 55: 'Williams', 30: 'Racing Bulls',
    5: 'Kick Sauber', 31: 'Haas F1 Team', 14: 'Aston Martin', 10: 'Alpine',
    23: 'Williams', 6: 'Racing Bulls', 27: 'Kick Sauber', 87: 'Haas F1 Team'
}

color_map = {
    0: "⬛", 2048: "🟨", 2049: "🟩", 2050: "❓", 2051: "🟪",
    2052: "❓", 2064: "🟦", 2068: "❓"
}

# API Data
def fetch_data(session_key):
    lap_url = f"https://api.openf1.org/v1/laps?session_key={session_key}"
    stint_url = f"https://api.openf1.org/v1/stints?session_key={session_key}&tyre_age_at_start>=3"
    session_url = f"https://api.openf1.org/v1/sessions?session_key={session_key}"

    lap_data = json.loads(urlopen(lap_url).read().decode('utf-8'))
    stint_data = json.loads(urlopen(stint_url).read().decode('utf-8'))
    session_data = json.loads(urlopen(session_url).read().decode('utf-8'))

    event_title = ""
    if session_data and isinstance(session_data, list):
        event = session_data[0]
        country = event.get("country_name", "")
        circuit = event.get("circuit_short_name", "").upper()
        session_name = event.get("session_name", "")
        event_title = f"{country} ({circuit}) - {session_name}"

    return lap_data, stint_data, event_title

def format_lap_time(seconds):
    if pd.isnull(seconds):
        return ""
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:06.3f}"

def lap_time_to_seconds(time_str):
    try:
        minutes, sec_ms = time_str.split(":")
        return int(minutes) * 60 + float(sec_ms)
    except:
        return None

def convert_sectors_to_colors(df):
    for sector_col in ['segments_sector_1', 'segments_sector_2', 'segments_sector_3']:
        if sector_col in df.columns:
            df[sector_col] = df[sector_col].apply(
                lambda x: ' '.join([color_map.get(i, '❓') for i in x]) if isinstance(x, list) else ''
            )
    return df

def reorder_columns(df):
    cols = df.columns.tolist()
    if 'driver_name' in cols:
        cols.remove('driver_name')
        df = df[['driver_name'] + cols]
    return df

def app():
    session_key = "latest"

    try:
        lap_data, stint_data, event_title = fetch_data(session_key)

        st.title(f"🏁 Live F1 Sector Visualizer — {event_title}")

        df_lap = pd.DataFrame(lap_data)
        df_stint = pd.DataFrame(stint_data)
        df = pd.merge(df_lap, df_stint, on="driver_number", how="left")

        df["driver_name"] = df["driver_number"].map(driver_names)
        df["team_name"] = df["driver_number"].map(driver_team)
        df["lap_duration"] = df["lap_duration"].apply(format_lap_time)

        df = df.drop(columns=[
            'meeting_key_y', 'i1_speed', 'i2_speed', 'date_start', 'date_end',
            'deleted', 'lap_distance', 'meeting_key_x', 'session_key_y', 'session_key_x'
        ], errors='ignore')

        df = convert_sectors_to_colors(df)

        selected_drivers = st.multiselect("👤 Select Driver(s)", sorted(driver_names.values()))
        selected_teams = st.multiselect("🏎️ Select Team(s)", sorted(set(driver_team.values())))

        col1, col2 = st.columns(2)
        show_fastest_lap = col1.checkbox("⚡ Show only fastest lap")
        show_current_lap = col2.checkbox("📡 Show only current lap")

        if selected_drivers:
            df = df[df['driver_name'].isin(selected_drivers)]
        if selected_teams:
            df = df[df['team_name'].isin(selected_teams)]

        if show_current_lap:
            df = df.sort_values(by="lap_number", ascending=False)
            df = df.dropna(subset=["driver_name"])
            df_latest = df.groupby("driver_name", as_index=False).first()

            team_order = ['McLaren', 'Ferrari', 'Red Bull Racing', 'Mercedes', 'Aston Martin']
            df_latest["team_name"] = df_latest["team_name"].fillna("Unknown")
            df_latest["team_order"] = pd.Categorical(df_latest["team_name"], categories=team_order, ordered=True)

            df_latest = df_latest.sort_values(by=["team_order", "driver_name"])
            df = df_latest.drop(columns=["team_order"])

        elif show_fastest_lap:
            df = df.copy()
            df["lap_duration_seconds"] = df["lap_duration"].apply(lap_time_to_seconds)
            df = df[df["lap_duration_seconds"] == df["lap_duration_seconds"].min()]
            df.drop(columns=["lap_duration_seconds"], inplace=True)
        else:
            if "lap_number" in df.columns:
                df = df.sort_values(by="lap_number", ascending=False)

        df = reorder_columns(df)
        st.dataframe(df, use_container_width=True)

    except Exception:
        st.markdown("### Updating data... Please wait.")

if __name__ == "__main__":
    app()
