import pandas as pd
from datetime import datetime
from utils.data_manager import TIMEZONE

from typing import List, Optional, Tuple

DAILY_PROGRESS_COLUMNS = {
    "mode": "Mode",
    "total": "Total",
    "success": "Success",
    "strict_rate": "StrictRate",
    "lenient_rate": "LenientRate",
    "target": "Target",
}

def calculate_ao5(group: pd.DataFrame) -> Optional[float]:
    """Calculate Ao5: drop best and worst from last 5, average middle 3."""
    if len(group) >= 5:
        last_5 = group.tail(5)['Time'].tolist()
        last_5.sort()
        return sum(last_5[1:4]) / 3
    return None

def iter_records_grouped_by_name_and_mode(records_df: pd.DataFrame) -> List[Tuple[str, List[Tuple[str, pd.DataFrame]]]]:
    """Return records grouped in sorted player -> mode order for UI rendering."""
    grouped_records = []
    if records_df.empty:
        return grouped_records

    for name in sorted(records_df['Name'].dropna().unique()):
        player_records = records_df[records_df['Name'] == name].copy().reset_index(drop=True)
        mode_groups = []
        for mode in sorted(player_records['Mode'].dropna().unique()):
            mode_records = player_records[player_records['Mode'] == mode].copy().reset_index(drop=True)
            mode_groups.append((mode, mode_records))
        grouped_records.append((name, mode_groups))

    return grouped_records

def prepare_today_top5_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare today's top-5 fastest attempts per player+mode (Scratch excluded)."""
    if df.empty:
        return pd.DataFrame()

    work_df = df.copy()
    if 'IsScratch' not in work_df.columns:
        work_df['IsScratch'] = False

    work_df['DateStr'] = pd.to_datetime(work_df['Timestamp'], errors='coerce').dt.strftime('%Y-%m-%d')
    work_df['TimeNum'] = pd.to_numeric(work_df['Time'], errors='coerce')
    work_df['TimestampDT'] = pd.to_datetime(work_df['Timestamp'], errors='coerce')

    today_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    today_valid_df = work_df[
        (work_df['DateStr'] == today_str)
        & (~work_df['IsScratch'].fillna(False).astype(bool))
        & (work_df['TimeNum'].notnull())
    ].copy()

    if today_valid_df.empty:
        return pd.DataFrame()

    today_valid_df = today_valid_df.sort_values(
        by=['Name', 'Mode', 'TimeNum', 'TimestampDT'],
        ascending=[True, True, True, True],
        na_position='last'
    )
    today_valid_df['Rank'] = today_valid_df.groupby(['Name', 'Mode']).cumcount() + 1

    top5_df = today_valid_df[today_valid_df['Rank'] <= 5].copy()
    top5_df['Gap'] = top5_df.groupby(['Name', 'Mode'])['TimeNum'].transform(lambda s: s - s.min())
    top5_df = top5_df[['Name', 'Mode', 'Rank', 'TimeNum', 'Gap', 'Timestamp']].rename(columns={'TimeNum': 'Time'})
    return top5_df

def get_personal_pb_rank(
    valid_df: pd.DataFrame,
    name: str,
    mode: str,
    time_val: float,
    timestamp_str: str
) -> Optional[int]:
    """Return PB rank (1-5) for a candidate attempt, or None if outside top 5."""
    try:
        candidate_time = float(time_val)
    except (TypeError, ValueError):
        return None

    if valid_df.empty:
        base_df = pd.DataFrame(columns=['TimeNum', 'Timestamp', '__candidate'])
    else:
        scoped_df = valid_df[(valid_df['Name'] == name) & (valid_df['Mode'] == mode)].copy()
        if 'IsScratch' in scoped_df.columns:
            scoped_df = scoped_df[~scoped_df['IsScratch'].fillna(False).astype(bool)]
        scoped_df['TimeNum'] = pd.to_numeric(scoped_df['Time'], errors='coerce')
        scoped_df = scoped_df[scoped_df['TimeNum'].notnull()].copy()
        base_df = scoped_df[['TimeNum', 'Timestamp']].copy()
        base_df['__candidate'] = False

    candidate_df = pd.DataFrame([{
        'TimeNum': candidate_time,
        'Timestamp': timestamp_str,
        '__candidate': True
    }])

    rank_df = pd.concat([base_df, candidate_df], ignore_index=True)
    rank_df['TimestampDT'] = pd.to_datetime(rank_df['Timestamp'], errors='coerce')
    rank_df = rank_df.sort_values(
        by=['TimeNum', 'TimestampDT', '__candidate'],
        ascending=[True, True, False],
        na_position='last'
    ).reset_index(drop=True)

    top5_df = rank_df.head(5)
    candidate_in_top5 = top5_df[top5_df['__candidate']].head(1)
    if candidate_in_top5.empty:
        return None

    return int(candidate_in_top5.index[0] + 1)

def prepare_ao5_data(valid_df_sorted: pd.DataFrame) -> pd.DataFrame:
    """Prepare Ao5 DataFrame."""
    ao5_results = []
    if not valid_df_sorted.empty:
        for (a_name, a_mode), group in valid_df_sorted.groupby(['Name', 'Mode']):
            ao5 = calculate_ao5(group)
            if ao5 is not None:
                ao5_results.append({'Name': a_name, 'Mode': a_mode, 'Ao5': ao5})
    return pd.DataFrame(ao5_results) if ao5_results else pd.DataFrame()

def prepare_daily_best_data(valid_df: pd.DataFrame) -> pd.DataFrame:
    """Return the fastest valid attempt per player, mode, and day for the PB trend chart."""
    if not valid_df.empty:
        valid_df_copy = valid_df.copy()
        valid_df_copy['Date'] = pd.to_datetime(valid_df_copy['Timestamp'], errors='coerce').dt.strftime('%Y-%m-%d')

        idx = valid_df_copy.groupby(['Name', 'Mode', 'Date'])['Time'].idxmin()
        pb_df = valid_df_copy.loc[idx, ['Name', 'Mode', 'Time', 'Date']].copy()

        pb_df = pb_df.sort_values(by=['Name', 'Mode', 'Date']).reset_index(drop=True)
        return pb_df
    return pd.DataFrame()

def prepare_pb_data(valid_df: pd.DataFrame) -> pd.DataFrame:
    """Backward-compatible alias for callers still using the old trend-chart helper name."""
    return prepare_daily_best_data(valid_df)

def prepare_top_pb_attempts(valid_df: pd.DataFrame, name: str, mode: str, limit: int = 5) -> pd.DataFrame:
    """Return the fastest attempts for a player+mode, including gap from the best time."""
    if valid_df.empty:
        return pd.DataFrame()

    scoped_df = valid_df[(valid_df['Name'] == name) & (valid_df['Mode'] == mode)].copy()
    if scoped_df.empty:
        return pd.DataFrame()

    scoped_df['TimeNum'] = pd.to_numeric(scoped_df['Time'], errors='coerce')
    scoped_df = scoped_df[scoped_df['TimeNum'].notnull()].copy()
    if scoped_df.empty:
        return pd.DataFrame()

    scoped_df['Date'] = pd.to_datetime(scoped_df['Timestamp'], errors='coerce').dt.strftime('%Y-%m-%d')
    scoped_df['TimestampDT'] = pd.to_datetime(scoped_df['Timestamp'], errors='coerce')
    scoped_df = scoped_df.sort_values(by=['TimeNum', 'TimestampDT'], na_position='last').head(limit).reset_index(drop=True)

    best_time = scoped_df.iloc[0]['TimeNum']
    scoped_df.insert(0, 'Rank', range(1, len(scoped_df) + 1))
    scoped_df['Gap'] = scoped_df['TimeNum'] - best_time

    return scoped_df[['Rank', 'TimeNum', 'Gap', 'Date']].rename(columns={'TimeNum': 'Time'})

def prepare_daily_progress_data(df: pd.DataFrame, goals_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare today's progress rows using stable internal column keys."""
    if df.empty:
        return pd.DataFrame()

    today_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    df_copy = df.copy()
    if 'IsScratch' not in df_copy.columns:
        df_copy['IsScratch'] = False
    df_copy['DateStr'] = pd.to_datetime(df_copy['Timestamp'], errors='coerce').dt.strftime('%Y-%m-%d')
    today_df = df_copy[df_copy['DateStr'] == today_str].copy()

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
                    DAILY_PROGRESS_COLUMNS["mode"]: p_mode,
                    DAILY_PROGRESS_COLUMNS["total"]: f"{total_count} (Scratch: {dnf_count})",
                    DAILY_PROGRESS_COLUMNS["success"]: f"{success_count}/{total_count}",
                    DAILY_PROGRESS_COLUMNS["strict_rate"]: f"{overall_rate:.1f}%",
                    DAILY_PROGRESS_COLUMNS["lenient_rate"]: f"{valid_rate:.1f}%",
                    DAILY_PROGRESS_COLUMNS["target"]: f"≤{target_time}s"
                })
    return pd.DataFrame(progress_data) if progress_data else pd.DataFrame()
