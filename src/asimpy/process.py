"""Base class for processes."""


class Process:
    def __init__(self, env, *args):
        self.env = env
        self.init(*args)
        self.proc = self.env.process(self.run())
