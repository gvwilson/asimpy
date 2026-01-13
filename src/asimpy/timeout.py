from .event import Event


class Timeout(Event):
    """Timeout event for sleeping."""

    def __init__(self, env, delay):
        super().__init__(env)
        env.schedule(env.now + delay, lambda: self.succeed())
