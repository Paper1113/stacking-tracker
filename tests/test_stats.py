import pytest
import pandas as pd
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.stats import calculate_ao5

def test_calculate_ao5_less_than_5_records():
    """Test that Ao5 returns None if there are fewer than 5 records."""
    df = pd.DataFrame({"Time": [3.5, 3.6, 3.7, 3.8]})
    assert calculate_ao5(df) is None

def test_calculate_ao5_exact_5_records():
    """Test that Ao5 correctly drops the highest and lowest, returning the average of the middle 3."""
    # Times: 2.0, 3.0, 4.0, 5.0, 6.0
    # Min: 2.0 (dropped), Max: 6.0 (dropped)
    # Middle 3: 3.0, 4.0, 5.0
    # Average: (3.0 + 4.0 + 5.0) / 3 = 4.0
    df = pd.DataFrame({"Time": [5.0, 2.0, 4.0, 6.0, 3.0]})
    assert calculate_ao5(df) == 4.0

def test_calculate_ao5_more_than_5_records():
    """Test that Ao5 only considers the *last* 5 records in the DataFrame."""
    # DataFrame is assumed to be already sorted by Timestamp in the app.
    # We pass 6 records: we ignore the first one (0.0).
    # Last 5 times: 3.5, 9.9, 3.6, 3.8, 1.0
    # Min: 1.0 (dropped), Max: 9.9 (dropped)
    # Middle 3: 3.5, 3.6, 3.8
    # Average: (3.5 + 3.6 + 3.8) / 3 = 10.9 / 3 = 3.633...
    df = pd.DataFrame({"Time": [0.0, 3.5, 9.9, 3.6, 3.8, 1.0]})
    assert pytest.approx(calculate_ao5(df), 0.001) == 3.633
