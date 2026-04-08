"""Test asimpy Event."""

import pytest
from unittest.mock import Mock
from asimpy import Environment, Event, Process
from asimpy.event import _PENDING


def test_event_initialization():
    """Test event initialization."""
    env = Environment()
    evt = Event(env)
    assert not evt.triggered
    assert not evt.cancelled
    assert evt._value is _PENDING


def test_event_succeed():
    """Test event success."""
    env = Environment()
    evt = Event(env)
    evt.succeed(42)
    assert evt.triggered
    assert evt._value == 42


def test_event_succeed_without_value():
    """Test event success without value."""
    env = Environment()
    evt = Event(env)
    evt.succeed()
    assert evt.triggered
    assert evt._value is None


def test_event_succeed_already_triggered():
    """Test that succeeding an already triggered event has no effect."""
    env = Environment()
    evt = Event(env)
    evt.succeed(1)
    evt.succeed(2)
    assert evt._value == 1


def test_event_cancel():
    """Test event cancellation."""
    env = Environment()
    evt = Event(env)
    evt.cancel()
    assert evt.cancelled


def test_event_cancel_already_triggered():
    """Cancelling an already triggered event marks it cancelled and fires _on_cancel."""
    env = Environment()
    evt = Event(env)
    evt.succeed(42)
    assert evt.triggered
    evt.cancel()
    assert evt.cancelled
    assert not evt.triggered


def test_event_add_waiter_after_triggered():
    """Test adding a callable waiter after event already triggered calls it immediately."""
    env = Environment()
    evt = Event(env)
    evt.succeed(42)

    callback = Mock()
    evt._add_waiter(callback)
    callback.assert_called_once_with(42)


def test_event_add_waiter_before_trigger():
    """Test adding a callable waiter before event triggered queues it."""
    env = Environment()
    evt = Event(env)

    callback = Mock()
    evt._add_waiter(callback)
    assert len(evt._waiters) == 1


def test_event_cancel_callback():
    """Test event cancel callback is invoked with old value."""
    env = Environment()
    evt = Event(env)

    callback = Mock()
    evt._on_cancel = callback
    evt.cancel()
    callback.assert_called_once_with(_PENDING)


def test_event_succeed_notifies_waiters():
    """Test that event success calls all waiter callbacks."""
    env = Environment()
    evt = Event(env)

    callback1 = Mock()
    callback2 = Mock()

    evt._add_waiter(callback1)
    evt._add_waiter(callback2)
    evt.succeed(99)

    callback1.assert_called_once_with(99)
    callback2.assert_called_once_with(99)


def test_event_cancel_already_cancelled_is_noop():
    """Calling cancel() on an already-cancelled event does nothing."""
    env = Environment()
    evt = Event(env)
    cb = Mock()
    evt._on_cancel = cb
    evt.cancel()
    cb.assert_called_once()
    evt.cancel()  # second call must not call _on_cancel again
    cb.assert_called_once()  # still called exactly once


def test_event_fail_requires_baseexception():
    """fail() raises TypeError when given a non-exception argument."""
    env = Environment()
    evt = Event(env)
    with pytest.raises(TypeError):
        evt.fail("not an exception")


def test_event_fail_reraises_in_process():
    """Awaiting a failed event re-raises the exception in the process."""

    class FailReceiver(Process):
        def init(self):
            self.error = None

        async def run(self):
            evt = Event(self._env)
            evt.fail(ValueError("boom"))
            try:
                await evt
            except ValueError as e:
                self.error = e

    env = Environment()
    proc = FailReceiver(env)
    env.run()
    assert str(proc.error) == "boom"
