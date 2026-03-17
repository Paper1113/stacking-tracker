import pandas as pd
from datetime import datetime
from utils.data_manager import TIMEZONE
from utils.i18n import t

from typing import Optional

def calculate_ao5(group: pd.DataFrame) -> Optional[float]:
    """Calculate Ao5: drop best and worst from last 5, average middle 3."""
    if len(group) >= 5:
        last_5 = group.tail(5)['Time'].tolist()
        last_5.sort()
        return sum(last_5[1:4]) / 3
    return None

def prepare_ao5_data(valid_df_sorted: pd.DataFrame) -> pd.DataFrame:
    """Prepare Ao5 DataFrame."""
    ao5_results = []
    if not valid_df_sorted.empty:
        for (a_name, a_mode), group in valid_df_sorted.groupby(['Name', 'Mode']):
            ao5 = calculate_ao5(group)
            if ao5 is not None:
                ao5_results.append({'Name': a_name, 'Mode': a_mode, 'Ao5': ao5})
    return pd.DataFrame(ao5_results) if ao5_results else pd.DataFrame()

def prepare_pb_data(valid_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare PB DataFrame."""
    if not valid_df.empty:
        # Instead of single global PB, we return the fastest time *per day* for the trend chart
        valid_df_copy = valid_df.copy()
        valid_df_copy['Date'] = pd.to_datetime(valid_df_copy['Timestamp'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        # Group by Name, Mode, and Date, then find the minimum time for each day
        idx = valid_df_copy.groupby(['Name', 'Mode', 'Date'])['Time'].idxmin()
        pb_df = valid_df_copy.loc[idx, ['Name', 'Mode', 'Time', 'Date']].copy()
        
        # Sort by Date chronologically so the line chart draws correctly left-to-right
        pb_df = pb_df.sort_values(by=['Name', 'Mode', 'Date']).reset_index(drop=True)
        return pb_df
    return pd.DataFrame()

def prepare_daily_progress_data(df: pd.DataFrame, goals_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare Daily Progress DataFrame based on Goals."""
    if df.empty:
        return pd.DataFrame()

    today_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    df['DateStr'] = pd.to_datetime(df['Timestamp'], errors='coerce').dt.strftime('%Y-%m-%d')
    today_df = df[df['DateStr'] == today_str].copy()

    progress_data = []
    if not today_df.empty and not goals_df.empty:
        for (p_name, p_mode), group in today_df.groupby(['Name', 'Mode']):
            target = goals_df[((goals_df['Name'] == p_name) | (goals_df['Name'] == 'All')) & (goals_df['Mode'] == p_mode)]
            if not target.empty:
                target_time = target.sort_values(by='Name', ascending=False).iloc[0]['TargetTime']
                total_count = len(group)
                dnf_count = len(group[group['IsScratch']])
                valid_count = total_count - dnf_count
                
                valid_attempts = group[~group['IsScratch']]
                success_count = len(valid_attempts[pd.to_numeric(valid_attempts['Time'], errors='coerce') <= target_time])
                
                overall_rate = (success_count / total_count * 100) if total_count > 0 else 0.0
                valid_rate = (success_count / valid_count * 100) if valid_count > 0 else 0.0
                
                progress_data.append({
                    "Name": p_name,
                    t("col_mode"): p_mode,
                    t("col_total"): f"{total_count} (DNF: {dnf_count})",
                    t("col_success"): f"{success_count}/{total_count}",
                    t("col_strict_rate"): f"{overall_rate:.1f}%",
                    t("col_lenient_rate"): f"{valid_rate:.1f}%",
                    t("col_target"): f"≤{target_time}s"
                })
    return pd.DataFrame(progress_data) if progress_data else pd.DataFrame()
