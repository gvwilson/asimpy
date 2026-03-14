"""Test asimpy Event."""

import pytest
from unittest.mock import Mock
from asimpy import Environment, Event
from asimpy._utils import _ensure_event


def test_ensure_event_rejects_invalid_type():
    """Test that ensure_event raises TypeError for non-Event, non-coroutine."""
    env = Environment()
    with pytest.raises(TypeError, match="Expected Event or coroutine"):
        _ensure_event(env, 42)


def test_event_initialization():
    """Test event initialization."""
    from asimpy.event import _PENDING
    env = Environment()
    evt = Event(env)
    assert not evt._triggered
    assert not evt._cancelled
    assert evt._value is _PENDING


def test_event_succeed():
    """Test event success."""
    env = Environment()
    evt = Event(env)
    evt.succeed(42)
    assert evt._triggered
    assert evt._value == 42


def test_event_succeed_without_value():
    """Test event success without value."""
    env = Environment()
    evt = Event(env)
    evt.succeed()
    assert evt._triggered
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
    assert evt._cancelled


def test_event_cancel_already_triggered():
    """Test cancelling already triggered event has no effect."""
    env = Environment()
    evt = Event(env)
    evt.succeed()
    evt.cancel()
    assert evt._triggered
    assert not evt._cancelled


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
    """Test event cancel callback is invoked."""
    env = Environment()
    evt = Event(env)

    callback = Mock()
    evt._on_cancel = callback
    evt.cancel()
    callback.assert_called_once()


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
