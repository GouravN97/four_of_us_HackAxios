#!/usr/bin/env python3
"""
Quick test to debug the datetime timezone issue.
"""

from datetime import datetime, timezone
from hypothesis import strategies as st

def test_timezone_strategy():
    """Test the timezone strategy to see what it generates."""
    print('Testing timezone strategy...')
    
    # Test timezone-naive strategy
    strategy_naive = st.datetimes(
        min_value=datetime(2020, 1, 1), 
        max_value=datetime.utcnow(), 
        timezones=st.none()
    )
    
    # Test timezone-aware strategy  
    strategy_aware = st.datetimes(
        min_value=datetime(2020, 1, 1), 
        max_value=datetime.utcnow(), 
        timezones=st.just(timezone.utc)
    )
    
    print("Generating timezone-naive samples:")
    for i in range(3):
        sample = strategy_naive.example()
        print(f'  Sample {i+1}: {sample}, tzinfo: {sample.tzinfo}')
    
    print("\nGenerating timezone-aware samples:")
    for i in range(3):
        sample = strategy_aware.example()
        print(f'  Sample {i+1}: {sample}, tzinfo: {sample.tzinfo}')
    
    # Test the comparison that's failing
    print("\nTesting datetime comparison:")
    naive_dt = datetime(2020, 1, 1)
    aware_dt = datetime(2020, 1, 1, tzinfo=timezone.utc)
    utc_now = datetime.utcnow()
    
    print(f"naive_dt: {naive_dt}, tzinfo: {naive_dt.tzinfo}")
    print(f"aware_dt: {aware_dt}, tzinfo: {aware_dt.tzinfo}")
    print(f"utc_now: {utc_now}, tzinfo: {utc_now.tzinfo}")
    
    try:
        result = naive_dt > utc_now
        print(f"naive_dt > utc_now: {result}")
    except Exception as e:
        print(f"naive_dt > utc_now failed: {e}")
    
    try:
        result = aware_dt > utc_now
        print(f"aware_dt > utc_now: {result}")
    except Exception as e:
        print(f"aware_dt > utc_now failed: {e}")

if __name__ == "__main__":
    test_timezone_strategy()