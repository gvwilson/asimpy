"""Test asimpy timeout."""

import pytest
from asimpy import Environment, Timeout


def test_timeout_zero_delay():
    """Test timeout with zero delay."""

    env = Environment()
    timeout = Timeout(env, 0)
    env.run()
    assert timeout.triggered is True


def test_timeout_positive_delay():
    """Test timeout with positive delay."""

    env = Environment()
    timeout = Timeout(env, 10)
    assert timeout.triggered is False
    env.run()
    assert timeout.triggered is True
    assert env.now == 10


def test_timeout_schedules_at_correct_time():
    """Test that timeout schedules at the correct time."""

    env = Environment()
    env._now = 5
    Timeout(env, 10)
    env.run()
    assert env.now == 15


def test_timeout_multiple_timeouts():
    """Test multiple timeouts execute in order."""

    env = Environment()
    t1 = Timeout(env, 5)
    t2 = Timeout(env, 10)
    t3 = Timeout(env, 3)

    env.run()
    assert t3.triggered is True
    assert t1.triggered is True
    assert t2.triggered is True


def test_timeout_rejects_negative_delay():
    """Test that Timeout raises ValueError for a negative delay."""
    env = Environment()
    with pytest.raises(ValueError, match="non-negative"):
        Timeout(env, -1)
