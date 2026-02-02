"""Test asimpy AllOf."""

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


def test_allof_with_coroutines():
    """Test AllOf with coroutine objects."""

    async def coro1():
        return "value1"

    async def coro2():
        return "value2"

    class CoroAllOf(Process):
        def init(self):
            self.result = {}

        async def run(self):
            self.result = await AllOf(self._env, x=coro1(), y=coro2())

    env = Environment()
    proc = CoroAllOf(env)
    env.run()
    assert proc.result["x"] == "value1"
    assert proc.result["y"] == "value2"
