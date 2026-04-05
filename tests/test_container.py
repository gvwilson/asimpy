"""Test asimpy Container."""

import pytest
from asimpy import Container, ContainerEmpty, ContainerFull, Environment, Process


def test_container_default_init():
    env = Environment()
    c = Container(env, capacity=10)
    assert c.level == 0
    assert c.capacity == 10


def test_container_with_init_level():
    env = Environment()
    c = Container(env, capacity=10, init=5)
    assert c.level == 5


def test_container_invalid_capacity():
    env = Environment()
    with pytest.raises(ValueError, match="capacity must be positive"):
        Container(env, capacity=0)
    with pytest.raises(ValueError, match="capacity must be positive"):
        Container(env, capacity=-1)


def test_container_negative_init():
    env = Environment()
    with pytest.raises(ValueError, match="init must be non-negative"):
        Container(env, capacity=10, init=-1)


def test_container_init_exceeds_capacity():
    env = Environment()
    with pytest.raises(ValueError, match="must be <= capacity"):
        Container(env, capacity=5, init=10)


def test_container_level_property():
    env = Environment()
    c = Container(env, capacity=100, init=42)
    assert c.level == 42


def test_container_capacity_property():
    env = Environment()
    c = Container(env, capacity=50)
    assert c.capacity == 50


def test_container_get_immediate():
    """get() returns a pre-triggered event when level >= amount."""

    class Getter(Process):
        def init(self, c):
            self.c = c
            self.got = None

        async def run(self):
            self.got = await self.c.get(3)

    env = Environment()
    c = Container(env, capacity=10, init=5)
    proc = Getter(env, c)
    env.run()
    assert proc.got == 3
    assert c.level == 2


def test_container_get_blocks_until_level_available():
    """get() blocks when level < amount, resumes after put()."""

    class Getter(Process):
        def init(self, c):
            self.c = c
            self.got = None
            self.t = None

        async def run(self):
            self.got = await self.c.get(5)
            self.t = self.now

    class Putter(Process):
        def init(self, c):
            self.c = c

        async def run(self):
            await self.timeout(10)
            await self.c.put(5)

    env = Environment()
    c = Container(env, capacity=10)
    g = Getter(env, c)
    Putter(env, c)
    env.run()
    assert g.got == 5
    assert g.t == 10


def test_container_get_invalid_amount():
    env = Environment()
    c = Container(env, capacity=10, init=5)
    with pytest.raises(ValueError, match="amount must be positive"):
        c.get(0)
    with pytest.raises(ValueError, match="amount must be positive"):
        c.get(-1)


def test_container_put_immediate():
    """put() returns a pre-triggered event when level + amount <= capacity."""

    class Putter(Process):
        def init(self, c):
            self.c = c
            self.result = None

        async def run(self):
            self.result = await self.c.put(4)

    env = Environment()
    c = Container(env, capacity=10)
    proc = Putter(env, c)
    env.run()
    assert proc.result == 4
    assert c.level == 4


def test_container_put_blocks_when_full():
    """put() blocks when level + amount > capacity."""

    class Putter(Process):
        def init(self, c):
            self.c = c
            self.t = None

        async def run(self):
            await self.c.put(8)  # fills to 8
            await self.c.put(4)  # blocks (8+4 > 10)
            self.t = self.now

    class Getter(Process):
        def init(self, c):
            self.c = c

        async def run(self):
            await self.timeout(5)
            await self.c.get(3)  # drains to 5, now 5+4 <= 10

    env = Environment()
    c = Container(env, capacity=10)
    p = Putter(env, c)
    Getter(env, c)
    env.run()
    assert p.t == 5
    assert c.level == 9


def test_container_put_invalid_amount():
    env = Environment()
    c = Container(env, capacity=10)
    with pytest.raises(ValueError, match="amount must be positive"):
        c.put(0)
    with pytest.raises(ValueError, match="amount must be positive"):
        c.put(-1)


def test_container_try_get_success():
    env = Environment()
    c = Container(env, capacity=10, init=5)
    result = c.try_get(3)
    assert result == 3
    assert c.level == 2


def test_container_try_get_insufficient():
    env = Environment()
    c = Container(env, capacity=10, init=2)
    with pytest.raises(ContainerEmpty):
        c.try_get(5)
    assert c.level == 2  # unchanged


def test_container_try_get_invalid_amount():
    env = Environment()
    c = Container(env, capacity=10, init=5)
    with pytest.raises(ValueError, match="amount must be positive"):
        c.try_get(0)


def test_container_try_put_success():
    env = Environment()
    c = Container(env, capacity=10)
    c.try_put(4)
    assert c.level == 4


def test_container_try_put_overflow():
    env = Environment()
    c = Container(env, capacity=10, init=8)
    with pytest.raises(ContainerFull):
        c.try_put(5)
    assert c.level == 8  # unchanged


def test_container_try_put_invalid_amount():
    env = Environment()
    c = Container(env, capacity=10)
    with pytest.raises(ValueError, match="amount must be positive"):
        c.try_put(0)


def test_container_get_skips_cancelled_getter():
    """_trigger_getters skips a cancelled getter and serves the next valid one."""

    class BlockedGetter(Process):
        def init(self, c):
            self.c = c
            self.got = None

        async def run(self):
            self.got = await self.c.get(3)

    env = Environment()
    c = Container(env, capacity=10)
    g1 = BlockedGetter(env, c)
    g2 = BlockedGetter(env, c)

    # Both getters are parked; cancel g1's event.
    env.run(until=0)
    c._getters[0][1].cancel()

    # Put enough to satisfy g2 only — g1 is cancelled.
    class Putter(Process):
        def init(self, c):
            self.c = c

        async def run(self):
            await self.c.put(3)

    Putter(env, c)
    env.run()
    assert g1.got is None
    assert g2.got == 3


def test_container_put_skips_cancelled_putter():
    """_trigger_putters skips a cancelled putter and serves the next valid one."""

    class BlockedPutter(Process):
        def init(self, c, amount):
            self.c = c
            self.amount = amount
            self.done = False

        async def run(self):
            await self.c.put(self.amount)
            self.done = True

    env = Environment()
    c = Container(env, capacity=5, init=5)  # full
    p1 = BlockedPutter(env, c, 2)
    p2 = BlockedPutter(env, c, 2)

    env.run(until=0)  # let both putters park
    c._putters[0][1].cancel()  # cancel p1's event

    class Getter(Process):
        def init(self, c):
            self.c = c

        async def run(self):
            await self.c.get(2)  # drains 2, triggers _trigger_putters

    Getter(env, c)
    env.run()
    assert not p1.done
    assert p2.done


def test_container_firstof_item_wins():
    """When a pre-triggered get event wins FirstOf, the level stays reduced."""
    from asimpy import FirstOf

    class Racer(Process):
        def init(self, c):
            self.c = c
            self.result = None

        async def run(self):
            self.result = await FirstOf(
                self._env, item=self.c.get(3), deadline=self.timeout(10)
            )

    env = Environment()
    c = Container(env, capacity=10, init=5)
    racer = Racer(env, c)
    env.run(until=0)

    assert racer.result == ("item", 3)
    assert c.level == 2  # consumed by the winning get


def test_container_undo_get_restores_level_directly():
    """_undo_get restores level when a get event is cancelled."""
    env = Environment()
    c = Container(env, capacity=10, init=5)
    evt = c.get(3)
    assert c.level == 2
    evt.cancel()  # fires _on_cancel(_undo_get)
    assert c.level == 5


def test_container_trigger_getters_skips_unsatisfiable():
    """_trigger_getters skips a getter whose amount exceeds current level.

    A small put satisfies the first getter but leaves insufficient level for
    the second, exercising the i += 1 branch in _trigger_getters.
    """

    class SmallGetter(Process):
        def init(self, c):
            self.c = c
            self.got = None

        async def run(self):
            self.got = await self.c.get(2)

    class LargeGetter(Process):
        def init(self, c):
            self.c = c
            self.got = None

        async def run(self):
            self.got = await self.c.get(8)

    class SmallPutter(Process):
        def init(self, c):
            self.c = c

        async def run(self):
            await self.timeout(1)
            await self.c.put(2)  # satisfies SmallGetter; level stays 0 < 8

    env = Environment()
    c = Container(env, capacity=10)
    sg = SmallGetter(env, c)
    lg = LargeGetter(env, c)
    SmallPutter(env, c)
    env.run(until=5)

    assert sg.got == 2
    assert lg.got is None  # still blocked; amount 8 not yet available


def test_container_trigger_putters_skips_oversized():
    """_trigger_putters skips a putter whose amount would exceed capacity.

    A small get satisfies the first putter but fills the container back up,
    leaving no space for the second, exercising the i += 1 branch.
    """

    class SmallPutter(Process):
        def init(self, c):
            self.c = c
            self.done = False

        async def run(self):
            await self.c.put(3)
            self.done = True

    class LargePutter(Process):
        def init(self, c):
            self.c = c
            self.done = False

        async def run(self):
            await self.c.put(8)
            self.done = True

    class Getter(Process):
        def init(self, c, amount, delay):
            self.c = c
            self.amount = amount
            self.delay = delay

        async def run(self):
            await self.timeout(self.delay)
            await self.c.get(self.amount)

    env = Environment()
    c = Container(env, capacity=10, init=10)  # full
    sp = SmallPutter(env, c)
    lp = LargePutter(env, c)
    # t=1: get 3 → level=7; _trigger_putters: sp fits (7+3=10 ✓), lp doesn't (10+8>10, i+=1)
    Getter(env, c, 3, 1)
    # t=2: get 8 → level=2; _trigger_putters: lp fits (2+8=10 ✓)
    Getter(env, c, 8, 2)
    env.run()

    assert sp.done
    assert lp.done
