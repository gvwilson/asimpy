"""Example utilities."""

import random
import sys
from prettytable import PrettyTable, TableStyle


DEFAULT_SEED = 7493418
TABLE = {
    "time": "r",
    "name": "l",
    "event": "l",
}


def example(func):
    """Run example function."""
    seed = DEFAULT_SEED if len(sys.argv) == 1 else int(sys.argv[1])
    random.seed(seed)
    env = func()
    show_log(env)


def show_log(env):
    """Show example log."""
    table = PrettyTable(list(TABLE.keys()))
    for name, align in TABLE.items():
        table.align[name] = align
    for row in env.get_log():
        table.add_row(row)
    table.set_style(TableStyle.MARKDOWN)
    print(table)
