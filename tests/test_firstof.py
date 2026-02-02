"""Test asimpy FirstOf."""

from asimpy import Environment, FirstOf, Process, Timeout


def test_firstof_single_event():
    """Test FirstOf with single event."""

    class FirstOfUser(Process):
        def init(self):
            self.result = ()

        async def run(self):
            self.result = await FirstOf(self._env, a=self.timeout(5))

    env = Environment()
    proc = FirstOfUser(env)
    env.run()
    assert proc.result == ("a", None)


def test_firstof_multiple_events_first_wins():
    """Test FirstOf returns first completed event."""

    class MultiFirstOf(Process):
        def init(self):
            self.result = ()

        async def run(self):
            self.result = await FirstOf(
                self._env, fast=self.timeout(3), slow=self.timeout(10)
            )

    env = Environment()
    proc = MultiFirstOf(env)
    env.run()
    assert proc.result == ("fast", None)
    assert env.now == 3


def test_firstof_cancels_others():
    """Test FirstOf cancels other events."""

    class CancelTest(Process):
        def init(self):
            self.result = None
            self.timeout1 = Timeout(self._env, 5)
            self.timeout2 = Timeout(self._env, 10)

        async def run(self):
            self.result = await FirstOf(self._env, a=self.timeout1, b=self.timeout2)

    env = Environment()
    proc = CancelTest(env)
    env.run()
    assert proc.timeout2._cancelled is True
