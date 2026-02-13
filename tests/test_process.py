"""Test asimpy process."""

import pytest
from asimpy import Environment, Event, Interrupt, Process


def test_process_basic_execution():
    """Test basic process execution."""

    class SimpleProcess(Process):
        def init(self):
            self.executed = False

        async def run(self):
            self.executed = True

    env = Environment()
    proc = SimpleProcess(env)
    env.run()
    assert proc.executed


def test_process_with_timeout():
    """Test process with timeout."""
    class WaitingProcess(Process):
        async def run(self):
            await self.timeout(5)
            self.done_time = self.now

    env = Environment()
    proc = WaitingProcess(env)
    env.run()
    assert proc.done_time == 5


def test_process_init_with_args():
    """Test process initialization with arguments."""
    class ProcessWithArgs(Process):
        def init(self, value, name=None):
            self.value = value
            self.name = name

        async def run(self):
            pass

    env = Environment()
    proc = ProcessWithArgs(env, 42, name="test")
    env.run()
    assert proc.value == 42
    assert proc.name == "test"


def test_process_now_property():
    """Test process now property."""
    class TimeCheckProcess(Process):
        async def run(self):
            self.start_time = self.now
            await self.timeout(10)
            self.end_time = self.now

    env = Environment()
    proc = TimeCheckProcess(env)
    env.run()
    assert proc.start_time == 0
    assert proc.end_time == 10


def test_process_interrupt():
    """Test process interruption."""
    class InterruptibleProcess(Process):
        def init(self):
            self.interrupted = False
            self.cause = None

        async def run(self):
            try:
                await self.timeout(100)
            except Interrupt as e:
                self.interrupted = True
                self.cause = e.cause

    env = Environment()
    proc = InterruptibleProcess(env)
    env.schedule(5, lambda: proc.interrupt("stop"))
    env.run()
    assert proc.interrupted
    assert proc.cause == "stop"


def test_process_multiple_interrupts():
    """Test multiple interrupts."""
    class MultiInterruptProcess(Process):
        def init(self):
            self.interrupt_count = 0

        async def run(self):
            try:
                await self.timeout(100)
            except Interrupt:
                self.interrupt_count += 1
                try:
                    await self.timeout(100)
                except Interrupt:
                    self.interrupt_count += 1

    env = Environment()
    proc = MultiInterruptProcess(env)
    env.schedule(5, lambda: proc.interrupt("first"))
    env.schedule(10, lambda: proc.interrupt("second"))
    env.run()
    assert proc.interrupt_count == 2


def test_process_interrupt_already_done():
    """Test interrupting already completed process."""
    class QuickProcess(Process):
        async def run(self):
            self.completed = True

    env = Environment()
    proc = QuickProcess(env)
    env.run()
    proc.interrupt("late")
    assert proc.completed


def test_process_exception_handling():
    """Test process exception handling."""
    class FailingProcess(Process):
        async def run(self):
            raise ValueError("test error")

    env = Environment()
    with pytest.raises(ValueError, match="test error"):
        FailingProcess(env)
        env.run()


def test_process_done_flag():
    """Test process done flag."""
    class TestProcess(Process):
        async def run(self):
            await self.timeout(5)

    env = Environment()
    proc = TestProcess(env)
    assert not proc._done
    env.run()
    assert proc._done


def test_process_loop_called_after_done():
    """Test that _loop returns early when process is already done."""
    class Worker(Process):
        def init(self, evt):
            self.finished = False
            self.evt = evt

        async def run(self):
            try:
                await self.evt
            except Interrupt:
                self.finished = True

    env = Environment()
    evt = Event(env)
    worker = Worker(env, evt)

    class Driver(Process):
        def init(self, worker, evt):
            self.worker = worker
            self.evt = evt

        async def run(self):
            await self.timeout(1)
            # Both calls schedule worker._loop before either runs
            self.evt.succeed()
            self.worker.interrupt("done")

    Driver(env, worker, evt)
    env.run()
    assert worker.finished
