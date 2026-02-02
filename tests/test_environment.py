"""Test asimpy Environment."""

from asimpy import Environment


def test_environment_initialization():
    """Test that environment initializes with time zero."""
    env = Environment()
    assert env.now == 0


def test_environment_with_logging():
    """Test environment initialization with logging enabled."""
    env = Environment(logging=True)
    assert env._logging


def test_environment_schedule_single_event():
    """Test scheduling a single event."""
    env = Environment()
    called = []
    env.schedule(5, lambda: called.append(5))
    env.run()
    assert called == [5]
    assert env.now == 5


def test_environment_schedule_multiple_events_in_order():
    """Test that multiple events execute in time order."""
    env = Environment()
    results = []
    env.schedule(10, lambda: results.append(10))
    env.schedule(5, lambda: results.append(5))
    env.schedule(15, lambda: results.append(15))
    env.run()
    assert results == [5, 10, 15]


def test_environment_schedule_same_time_events():
    """Test events scheduled at the same time execute in schedule order."""
    env = Environment()
    results = []
    env.schedule(5, lambda: results.append("a"))
    env.schedule(5, lambda: results.append("b"))
    env.schedule(5, lambda: results.append("c"))
    env.run()
    assert results == ["a", "b", "c"]


def test_environment_run_until():
    """Test running environment until a specific time."""
    env = Environment()
    results = []
    env.schedule(5, lambda: results.append(5))
    env.schedule(10, lambda: results.append(10))
    env.schedule(15, lambda: results.append(15))
    env.run(until=12)
    assert results == [5, 10]
    assert env.now == 10


def test_environment_timeout_creation():
    """Test creating timeout from environment."""
    from asimpy import Environment, Timeout

    env = Environment()
    timeout = env.timeout(5)
    assert isinstance(timeout, Timeout)


def test_environment_immediate_scheduling():
    """Test immediate callback scheduling."""
    env = Environment()
    results = []
    env._immediate(lambda: results.append("immediate"))
    env.run()
    assert results == ["immediate"]
    assert env.now == 0


def test_environment_string_representation():
    """Test environment string representation."""
    env = Environment()
    assert str(env) == "Env(t=0)"
    env._now = 42
    assert str(env) == "Env(t=42)"


def test_environment_empty_run():
    """Test running environment with no events."""
    env = Environment()
    env.run()
    assert env.now == 0
