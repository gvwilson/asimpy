"""Test asimpy timeout."""

from asimpy import Environment, Timeout


def test_timeout_initialization():
    """Test timeout initialization."""
    env = Environment()
    timeout = Timeout(env, 5)
    assert timeout._env == env


def test_timeout_zero_delay():
    """Test timeout with zero delay."""
    from asimpy import Environment, Timeout

    env = Environment()
    timeout = Timeout(env, 0)
    env.run()
    assert timeout._triggered is True


def test_timeout_positive_delay():
    """Test timeout with positive delay."""
    from asimpy import Environment, Timeout

    env = Environment()
    timeout = Timeout(env, 10)
    assert timeout._triggered is False
    env.run()
    assert timeout._triggered is True
    assert env.now == 10


def test_timeout_schedules_at_correct_time():
    """Test that timeout schedules at the correct time."""
    from asimpy import Environment, Timeout

    env = Environment()
    env._now = 5
    Timeout(env, 10)
    env.run()
    assert env.now == 15


def test_timeout_multiple_timeouts():
    """Test multiple timeouts execute in order."""
    from asimpy import Environment, Timeout

    env = Environment()
    t1 = Timeout(env, 5)
    t2 = Timeout(env, 10)
    t3 = Timeout(env, 3)

    env.run()
    assert t3._triggered is True
    assert t1._triggered is True
    assert t2._triggered is True
