"""Combination conditions."""

class AllOf:
    def __init__(self, env, **kwargs):
        self.env = env
        self.children = {obj: key for key, obj in kwargs}
        self.results = {}

    def notify(self, child, value):
        assert child in self.children
        assert child not in self.results
        self.results[self.children[child]] = value
        if len(self.results) == len(self.children):
            print("complete")
