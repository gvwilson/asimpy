"""Base class for active process."""

from abc import ABC, abstractmethod
from functools import partial
from typing import TYPE_CHECKING, Any

from .event import _PENDING, _CANCELLED
from .interrupt import Interrupt

if TYPE_CHECKING:
    from .environment import Environment


class Process(ABC):
    """Abstract base class for active process."""

    def __init__(self, env: "Environment", *args: Any, **kwargs: Any):
        """
        Construct new process.

        Args:
            env: simulation environment.
            args: extra constructor arguments passed to `init()`.
        """
        self._env = env
        self._done = False
        self._started = False   # True after the first coro.send(None) call
        self._interrupt = None
        self._current_event = None

        self.init(*args, **kwargs)

        self._coro = self.run()
        self._env.immediate(self._loop)

    def init(self, *args: Any, **kwargs: Any):
        """
        Extra construction after generic setup but before coroutine created.

        Args:
            args: extra constructor arguments passed to `init()`.
            kwargs: extra construct arguments passed to `init()`.
        """
        pass

    @abstractmethod
    def run(self):
        """Implementation of process behavior."""
        pass

    @property
    def now(self):
        """Shortcut to access simulation time."""
        return self._env.now

    def timeout(self, delay: int | float):
        """
        Delay this process for a specified time.

        Args:
            delay: how long to wait.
        """
        return self._env.timeout(delay)

    def interrupt(self, cause: Any):
        """
        Interrupt this process

        Args:
            cause: reason for interrupt.
        """
        if not self._done:
            self._interrupt = Interrupt(cause)
            self._env.immediate(self._loop)

    def _loop(self, value=None) -> None:
        if self._done:
            return

        try:
            self._env.active_process = self

            while True:
                # ── Advance the coroutine ─────────────────────────────────
                if self._interrupt is not None and self._started:
                    # An interrupt is pending and the coroutine has been
                    # started, so it is safe to throw into it.
                    # Cancel the event we are currently awaiting so it
                    # won't fire and call resume() later.
                    if self._current_event is not None:
                        self._current_event.cancel()
                        self._current_event = None
                    exc = self._interrupt
                    self._interrupt = None
                    yielded = self._coro.throw(exc)
                else:
                    # Either no interrupt is pending, or the coroutine has
                    # not been started yet (throwing into an unstarted
                    # coroutine bypasses its try/except blocks).
                    self._started = True
                    yielded = self._coro.send(value)

                # ── Tight loop: skip the heap for already-triggered events ─
                self._current_event = yielded
                v = yielded._value
                if v is not _PENDING and v is not _CANCELLED:
                    if self._interrupt is not None:
                        # Interrupt arrived while in the tight loop.
                        # Loop again: the interrupt branch above will deliver
                        # it via throw into the coroutine's current yield.
                        continue
                    value = v
                    self._current_event = None
                    continue    # resume immediately without a heap round-trip

                # ── Event not yet done: park until it fires ───────────────
                yielded._add_waiter(self.resume)
                break

        except StopIteration:
            self._done = True
            self._current_event = None

        except Exception as exc:
            self._done = True
            self._current_event = None
            raise exc

        finally:
            self._env.active_process = None

    def resume(self, value=None) -> None:
        if not self._done:
            # partial is a C-level callable — cheaper than a Python closure.
            self._env.immediate(partial(self._loop, value))
