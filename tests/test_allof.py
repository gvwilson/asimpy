"""Test asimpy AllOf."""

import pytest
from asimpy import Environment, AllOf, Process


def test_allof_single_event():
    """Test AllOf with single event."""

    class AllOfUser(Process):
        def init(self):
            self.result = {}

        async def run(self):
            self.result = await AllOf(self._env, a=self.timeout(5))

    env = Environment()
    proc = AllOfUser(env)
    env.run()
    assert "a" in proc.result


def test_allof_multiple_events():
    """Test AllOf with multiple events."""

    class MultiAllOf(Process):
        def init(self):
            self.result = {}

        async def run(self):
            self.result = await AllOf(
                self._env, a=self.timeout(5), b=self.timeout(3), c=self.timeout(7)
            )

    env = Environment()
    proc = MultiAllOf(env)
    env.run()
    assert "a" in proc.result
    assert "b" in proc.result
    assert "c" in proc.result
    assert env.now == 7


def test_allof_requires_at_least_one_event():
    """Test that AllOf raises ValueError when given no events."""
    env = Environment()
    with pytest.raises(ValueError, match="at least one event"):
        AllOf(env)


def test_allof_rejects_non_event_argument():
    """AllOf raises TypeError when an argument is not an Event."""
    env = Environment()
    with pytest.raises(TypeError, match="must be an Event"):
        AllOf(env, a=42)
