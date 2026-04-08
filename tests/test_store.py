"""Test asimpy Store."""

import pytest
from asimpy import Environment, Process, Store, StoreEmpty, StoreFull
from asimpy.event import Event


def test_store_default_capacity():
    env = Environment()
    s = Store(env)
    assert len(s) == 0


def test_store_invalid_capacity():
    env = Environment()
    with pytest.raises(ValueError, match="capacity must be positive"):
        Store(env, capacity=0)
    with pytest.raises(ValueError, match="capacity must be positive"):
        Store(env, capacity=-1)


def test_store_len():
    env = Environment()
    s = Store(env)
    s._items.append("a")
    s._items.append("b")
    assert len(s) == 2


def test_store_get_immediate():
    """get() returns a pre-triggered event when an item is available."""

    class Getter(Process):
        def init(self, s):
            self.s = s
            self.got = None

        async def run(self):
            self.got = await self.s.get()

    env = Environment()
    s = Store(env)
    s._items.append("hello")
    proc = Getter(env, s)
    env.run()
    assert proc.got == "hello"
    assert len(s) == 0


def test_store_get_blocks_then_resolves():
    """get() blocks when empty, resolves after put()."""

    class Getter(Process):
        def init(self, s):
            self.s = s
            self.got = None
            self.t = None

        async def run(self):
            self.got = await self.s.get()
            self.t = self.now

    class Putter(Process):
        def init(self, s):
            self.s = s

        async def run(self):
            await self.timeout(7)
            await self.s.put("item")

    env = Environment()
    s = Store(env)
    g = Getter(env, s)
    Putter(env, s)
    env.run()
    assert g.got == "item"
    assert g.t == 7


def test_store_get_with_filter_immediate():
    """get(filter) returns the first matching item."""

    class FilterGetter(Process):
        def init(self, s):
            self.s = s
            self.got = None

        async def run(self):
            self.got = await self.s.get(lambda x: x % 2 == 0)

    env = Environment()
    s = Store(env)
    s._items.extend([1, 3, 4, 5])
    proc = FilterGetter(env, s)
    env.run()
    assert proc.got == 4
    assert s._items == [1, 3, 5]


def test_store_get_with_filter_blocks():
    """get(filter) blocks when no matching item available."""

    class FilterGetter(Process):
        def init(self, s):
            self.s = s
            self.got = None

        async def run(self):
            self.got = await self.s.get(lambda x: isinstance(x, str))

    class Putter(Process):
        def init(self, s):
            self.s = s

        async def run(self):
            await self.timeout(3)
            await self.s.put("text")

    env = Environment()
    s = Store(env)
    s._items.append(42)  # non-matching item already present
    g = FilterGetter(env, s)
    Putter(env, s)
    env.run()
    assert g.got == "text"


def test_store_put_delivers_to_waiting_getter():
    """put() delivers directly to a parked getter."""

    class Getter(Process):
        def init(self, s):
            self.s = s
            self.got = None

        async def run(self):
            self.got = await self.s.get()

    class Putter(Process):
        def init(self, s):
            self.s = s

        async def run(self):
            await self.timeout(1)
            await self.s.put("direct")

    env = Environment()
    s = Store(env)
    g = Getter(env, s)
    Putter(env, s)
    env.run()
    assert g.got == "direct"
    assert len(s) == 0


def test_store_put_blocks_when_full():
    """put() blocks when store is at capacity."""

    class Putter(Process):
        def init(self, s, value):
            self.s = s
            self.value = value
            self.t = None

        async def run(self):
            await self.s.put(self.value)
            self.t = self.now

    class Getter(Process):
        def init(self, s):
            self.s = s

        async def run(self):
            await self.timeout(5)
            await self.s.get()

    env = Environment()
    s = Store(env, capacity=1)
    p1 = Putter(env, s, "first")
    p2 = Putter(env, s, "second")  # blocks
    Getter(env, s)
    env.run()
    assert p1.t == 0
    assert p2.t == 5


def test_store_put_skips_cancelled_getter():
    """put() skips a cancelled getter and delivers to the next valid one."""

    class Getter(Process):
        def init(self, s):
            self.s = s
            self.got = None

        async def run(self):
            self.got = await self.s.get()

    class Putter(Process):
        def init(self, s):
            self.s = s

        async def run(self):
            await self.timeout(1)
            await self.s.put("item")

    env = Environment()
    s = Store(env)
    g1 = Getter(env, s)
    g2 = Getter(env, s)

    env.run(until=0)
    s._getters[0][1].cancel()  # cancel g1

    Putter(env, s)
    env.run()
    assert g1.got is None
    assert g2.got == "item"


def test_store_put_filter_mismatch_stores_item():
    """put() stores item when no waiting getter's filter matches."""

    class FilterGetter(Process):
        def init(self, s):
            self.s = s
            self.got = None

        async def run(self):
            # Only accepts strings
            self.got = await self.s.get(lambda x: isinstance(x, str))

    class Putter(Process):
        def init(self, s):
            self.s = s

        async def run(self):
            await self.timeout(1)
            await self.s.put(42)  # doesn't match filter
            await self.timeout(1)
            await self.s.put("hello")  # matches filter

    env = Environment()
    s = Store(env)
    g = FilterGetter(env, s)
    Putter(env, s)
    env.run()
    assert g.got == "hello"
    assert 42 in s._items


def test_store_try_get_success():
    env = Environment()
    s = Store(env)
    s._items.extend(["a", "b", "c"])
    item = s.try_get()
    assert item == "a"
    assert s._items == ["b", "c"]


def test_store_try_get_with_filter():
    env = Environment()
    s = Store(env)
    s._items.extend([1, 2, 3, 4])
    item = s.try_get(lambda x: x % 2 == 0)
    assert item == 2


def test_store_try_get_empty():
    env = Environment()
    s = Store(env)
    with pytest.raises(StoreEmpty):
        s.try_get()


def test_store_try_get_no_match():
    env = Environment()
    s = Store(env)
    s._items.extend([1, 3, 5])
    with pytest.raises(StoreEmpty):
        s.try_get(lambda x: x % 2 == 0)


def test_store_try_put_success():
    env = Environment()
    s = Store(env, capacity=3)
    s.try_put("x")
    assert "x" in s._items


def test_store_try_put_full():
    env = Environment()
    s = Store(env, capacity=1)
    s._items.append("existing")
    with pytest.raises(StoreFull):
        s.try_put("overflow")


def test_store_promote_putter_skips_cancelled():
    """_promote_putter skips a cancelled putter and unblocks the next valid one."""

    class BlockedPutter(Process):
        def init(self, s, value):
            self.s = s
            self.value = value
            self.done = False

        async def run(self):
            await self.s.put(self.value)
            self.done = True

    class Getter(Process):
        def init(self, s):
            self.s = s
            self.got = None

        async def run(self):
            await self.timeout(1)
            self.got = await self.s.get()

    env = Environment()
    s = Store(env, capacity=1)
    s._items.append("initial")  # fill store
    p1 = BlockedPutter(env, s, "p1")
    p2 = BlockedPutter(env, s, "p2")
    env.run(until=0)

    # Cancel p1's putter event.
    s._putters[0][1].cancel()

    Getter(env, s)
    env.run()
    assert not p1.done
    assert p2.done


def test_store_sleep_wake_pattern():
    """A sleeping process parks itself in a Store; a waker claims and wakes it."""

    class Sleeper(Process):
        def init(self, store):
            self.store = store
            self.wake_evt = None
            self.message = None

        async def run(self):
            self.wake_evt = Event(self._env)
            await self.store.put(self)  # offer self so waker can find us
            self.message = await self.wake_evt  # sleep until woken

    class Waker(Process):
        def init(self, store):
            self.store = store

        async def run(self):
            await self.timeout(5)
            sleeper = await self.store.get()
            sleeper.wake_evt.succeed("hello")

    env = Environment()
    store = Store(env)
    sleeper = Sleeper(env, store)
    Waker(env, store)
    env.run()
    assert sleeper.message == "hello"
