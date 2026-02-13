"""Test asimpy FirstOf."""

from asimpy import Environment, Event, FirstOf, Process, Timeout


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


def test_firstof_already_triggered_events():
    """Test FirstOf with events that are already triggered hits early return."""
    env = Environment()
    evt_a = Event(env)
    evt_b = Event(env)
    evt_a.succeed("first")
    evt_b.succeed("second")

    class Waiter(Process):
        def init(self, evt_a, evt_b):
            self.evt_a = evt_a
            self.evt_b = evt_b
            self.result = None

        async def run(self):
            self.result = await FirstOf(self._env, a=self.evt_a, b=self.evt_b)

    proc = Waiter(env, evt_a, evt_b)
    env.run()
    assert proc.result == ("a", "first")
