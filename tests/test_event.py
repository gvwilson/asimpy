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
    env = Environment()
    evt = Event(env)
    assert not evt._triggered
    assert not evt._cancelled
    assert evt._value is None


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
    """Test adding waiter after event already triggered."""
    env = Environment()
    evt = Event(env)
    evt.succeed(42)

    waiter = Mock()
    waiter.resume = Mock()
    evt._add_waiter(waiter)
    waiter.resume.assert_called_once_with(42)


def test_event_add_waiter_before_trigger():
    """Test adding waiter before event triggered."""
    env = Environment()
    evt = Event(env)

    waiter = Mock()
    waiter.resume = Mock()
    evt._add_waiter(waiter)
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
    """Test that event success notifies all waiters."""
    env = Environment()
    evt = Event(env)

    waiter1 = Mock()
    waiter1.resume = Mock()
    waiter2 = Mock()
    waiter2.resume = Mock()

    evt._add_waiter(waiter1)
    evt._add_waiter(waiter2)
    evt.succeed(99)

    waiter1.resume.assert_called_once_with(99)
    waiter2.resume.assert_called_once_with(99)
