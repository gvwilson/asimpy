"""Using Environment.immediate and Environment.schedule directly."""

from asimpy import Environment

env = Environment()
env.schedule(10, lambda: print("delayed (scheduled at 10)"))
env.schedule(5, lambda: print("middle (scheduled at 5)"))
env.immediate(lambda: print("immediate (scheduled at current time)"))
env.run()
