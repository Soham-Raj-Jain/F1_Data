import pandas as pd
import streamlit as st
import json
from urllib.request import urlopen
from streamlit_autorefresh import st_autorefresh

# Set page config
st.set_page_config(layout="wide", page_title="Live F1 Lap Times", page_icon="🏎️")

# Auto-refresh every 30 seconds
st_autorefresh(interval= 90000 , key="datarefresh")

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

# Sector color code mapping
color_map = {
    0: "⬛",       # Not available
    2048: "🟨",    # Yellow
    2049: "🟩",    # Green
    2050: "❓",    # Unknown
    2051: "🟪",    # Purple
    2052: "❓",    # Unknown
    2064: "🟦",    # Pitlane
    2068: "❓"     # Unknown
}

# Fetch lap + stint data
def fetch_data(session_key):
    lap_url = f'https://api.openf1.org/v1/laps?session_key={session_key}'
    stint_url = f'https://api.openf1.org/v1/stints?session_key={session_key}&tyre_age_at_start>=3'

    lap_data = json.loads(urlopen(lap_url).read().decode('utf-8'))
    stint_data = json.loads(urlopen(stint_url).read().decode('utf-8'))

    return lap_data, stint_data

# Format seconds to M:SS.mmm
def format_lap_time(seconds):
    if pd.isnull(seconds):
        return ""
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:06.3f}"

# Convert lap time string (M:SS.mmm) to seconds
def lap_time_to_seconds(time_str):
    try:
        minutes, sec_ms = time_str.split(":")
        return int(minutes) * 60 + float(sec_ms)
    except:
        return None

# Convert numeric segment codes to colored blocks
def convert_sectors_to_colors(df):
    for sector_col in ['segments_sector_1', 'segments_sector_2', 'segments_sector_3']:
        if sector_col in df.columns:
            df[sector_col] = df[sector_col].apply(
                lambda x: ' '.join([color_map.get(i, '❓') for i in x]) if isinstance(x, list) else ''
            )
    return df

# Main Streamlit app
def app():
    st.title("🏁 Live F1 Sector Visualizer")

    session_key = 'latest'
    lap_data, stint_data = fetch_data(session_key)

    df_lap = pd.DataFrame(lap_data)
    df_stint = pd.DataFrame(stint_data)

    # Merge laps with stint info
    df_merged = pd.merge(df_lap, df_stint, on="driver_number", how="left")

    # Add driver & team names
    df_merged["driver_name"] = df_merged["driver_number"].map(driver_names)
    df_merged["team_name"] = df_merged["driver_number"].map(driver_team)

    # Format lap duration
    if "lap_duration" in df_merged.columns:
        df_merged["lap_duration"] = df_merged["lap_duration"].apply(format_lap_time)

    # Drop unused
    df_merged = df_merged.drop(columns=[
        'meeting_key_y', 'i1_speed', 'i2_speed', 'date_start', 'date_end',
        'deleted', 'lap_distance', 'meeting_key_x', 'session_key_y', 'session_key_x'
    ], errors='ignore')

    # Reorder
    col_order = list(df_merged.columns)
    if "driver_name" in col_order:
        col_order.insert(0, col_order.pop(col_order.index("driver_name")))
    if "compound_name" in col_order:
        col_order.insert(1, col_order.pop(col_order.index("compound_name")))
    if "is_pit_out_lap" in col_order:
        col_order.insert(-1, col_order.pop(col_order.index("is_pit_out_lap")))
    if "driver_number" in col_order:
        col_order.append(col_order.pop(col_order.index("driver_number")))
    df_merged = df_merged[col_order]

    # 🟥 Convert segments to colored blocks
    df_merged = convert_sectors_to_colors(df_merged)

    # Filters
    selected_driver = st.selectbox("👤 Select Driver", ["All Drivers"] + sorted(driver_names.values()))
    selected_team = st.selectbox("🏎️ Select Team", ["All Teams"] + sorted(set(driver_team.values())))
    show_fastest_lap = st.checkbox("⚡ Show only fastest lap")

    # Apply filters
    if selected_driver != "All Drivers":
        df_merged = df_merged[df_merged['driver_name'] == selected_driver]

    if selected_team != "All Teams":
        df_merged = df_merged[df_merged['team_name'] == selected_team]

    if show_fastest_lap and not df_merged.empty:
        valid_laps = df_merged["lap_duration"].apply(lambda x: isinstance(x, str) and ":" in x)
        df_valid = df_merged[valid_laps].copy()
        df_valid["lap_duration_seconds"] = df_valid["lap_duration"].apply(lap_time_to_seconds)
        min_duration = df_valid["lap_duration_seconds"].min()
        df_merged = df_valid[df_valid["lap_duration_seconds"] == min_duration].copy()
        df_merged.drop(columns=["lap_duration_seconds"], inplace=True)

    # Show final
    st.dataframe(df_merged, use_container_width=True)

# Run
if __name__ == "__main__":
    app()


#To Run the code use : streamlit run live_f1_data.py
