"""Example utilities."""

import random
import sys


DEFAULT_SEED = 7493418


def example(func):
    seed = DEFAULT_SEED if len(sys.argv) == 1 else int(sys.argv[1])
    random.seed(seed)
    func()
