"""Awaitable actions."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .environment import Environment
    from .process import Process


class BaseAction(ABC):
    """Base of all internal awaitable actions."""

    def __init__(self, env: "Environment"):
        self._env = env
        self._parent = None
        self._cancelled = False

    def __await__(self):
        yield self
        return None

    def _action(self, proc: "Process"):
        if self._cancelled:
            return
        if self._parent:
            self._parent.notify(self)
        else:
            self.act(proc)

    @abstractmethod
    def act(self, proc: "Process"):
        pass
