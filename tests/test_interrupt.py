"""Test asimpy interrupt."""

from asimpy import Interrupt


def test_interrupt_creation():
    """Test interrupt exception creation."""
    interrupt = Interrupt("test cause")
    assert interrupt.cause == "test cause"


def test_interrupt_string_representation():
    """Test interrupt string representation."""
    interrupt = Interrupt("my reason")
    assert str(interrupt) == "Interrupt(my reason)"


def test_interrupt_is_exception():
    """Test that Interrupt is an Exception."""
    interrupt = Interrupt("test")
    assert isinstance(interrupt, Exception)
