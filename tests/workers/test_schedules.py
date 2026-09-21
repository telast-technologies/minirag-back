from src.workers.schedules import beat_schedule


def test_beat_schedule_is_dict():
    assert isinstance(beat_schedule, dict)


def test_beat_schedule_is_empty():
    assert beat_schedule == {}
