"""Events."""

class Sleep:
    """Wait for a specified simulated time."""

    def __init__(self, delay):
        self.delay = delay

    def __await__(self):
        yield self
        return None


class Acquire:
    """Acquire a resource."""

    def __init__(self, resource):
        self.resource = resource

    def __await__(self):
        yield self
        return None


class Release:
    """Release a resource."""

    def __init__(self, resource):
        self.resource = resource

    def __await__(self):
        yield self
        return None
