import pytest

from resp_audio_sleep.tasks.synchronous import _HeartRateMonitor


@pytest.mark.parametrize("size", [10, 15])
def test_heartrate_monitor(size: int):
    """Test heart-rate monitor object."""
    hrm = _HeartRateMonitor(size)
    for k in range(20):
        hrm.add_heartbeat(k)
        if k < size - 1:
            assert not hrm.initialized
        else:
            assert hrm.initialized
    assert hrm.mean_delay() == 1
    assert hrm.rate() == 1
    assert hrm.bpm() == 60


def test_heartrate_monitor_errors():
    """Test invalid heart-rate monitor object."""
    hrm = _HeartRateMonitor(size=5)
    with pytest.raises(ValueError, match="The monitor is not initialized yet."):
        hrm.mean_delay()
    with pytest.raises(ValueError, match="The monitor is not initialized yet."):
        hrm.rate()
    with pytest.raises(ValueError, match="The monitor is not initialized yet."):
        hrm.bpm()
    for k in range(7):
        hrm.add_heartbeat(k * 0.5)
    assert hrm.mean_delay() == 0.5
    assert hrm.rate() == 2
    assert hrm.bpm() == 120
