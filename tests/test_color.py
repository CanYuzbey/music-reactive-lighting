import pytest
from app.mapping.color import CircularExponentialMovingAverage, MoodStabilizer

def test_circular_ema_shortest_path():
    """Test that the circular EMA finds the shortest path across the 0/1 boundary."""
    # Alpha=1.0 means it jumps directly to the target (or shortest path equivalent)
    # We test going from 0.9 (magenta) to 0.1 (orange). The shortest distance is +0.2 crossing 0.0.
    cema = CircularExponentialMovingAverage(alpha=0.5, initial_val=0.9)
    
    # 0.9 -> 0.1 distance is 0.2 (+). Half step = 0.1 move. 0.9 + 0.1 = 1.0 -> 0.0
    res = cema.update(0.1)
    assert pytest.approx(res, rel=1e-3) == 0.0
    
    # Another half step should put it at 0.05
    res2 = cema.update(0.1)
    assert pytest.approx(res2, rel=1e-3) == 0.05

def test_circular_ema_standard_path():
    """Test standard linear movement when boundary crossing is not shorter."""
    cema = CircularExponentialMovingAverage(alpha=0.5, initial_val=0.5)
    
    # 0.5 to 0.7 distance is 0.2. Half step is 0.1.
    res = cema.update(0.7)
    assert pytest.approx(res, rel=1e-3) == 0.6

def test_mood_stabilizer_adaptation():
    """Test that stabilizer adapts quickly initially."""
    stab = MoodStabilizer(initial_val=0.5)
    assert stab.is_adapting == True
    
    # Adapt to 0.9 (distance 0.4). Alpha in adapting is 0.05.
    res1 = stab.update(0.9)
    expected1 = 0.5 + (0.9 - 0.5) * 0.05
    assert pytest.approx(res1, rel=1e-3) == expected1

def test_mood_stabilizer_drift_detection():
    """Test that prolonged drift triggers adaptation mode."""
    stab = MoodStabilizer(initial_val=0.5)
    stab.is_adapting = False  # Force stable mode
    
    # Feed it 1.0 (distance 0.5) repeatedly to exceed drift_counter (40 frames)
    for _ in range(45):
        stab.update(1.0)
        
    # Should have triggered adaptation due to prolonged distance > 0.20
    assert stab.is_adapting == True
