"""Compare asimpy and simpy benchmark results side by side.

Imports benchmark() from benchmark.py (asimpy) and classic.py (simpy), runs
both, and produces a combined DataFrame with one row per feature.  Features
present in only one library show None for the other library's column and for
the ratio.  The ratio column is asimpy / simpy: values below 1 mean asimpy
used fewer instructions per execution than simpy for that feature.
"""

import argparse
import csv
import sys
import os

# Allow importing sibling modules (benchmark.py, classic.py) by name.
sys.path.insert(0, os.path.dirname(__file__))

import polars as pl
from prettytable import PrettyTable, TableStyle

from benchmark import benchmark as asimpy_benchmark
from classic import benchmark as simpy_benchmark


# Features that exist under different names in each library are mapped to a
# shared display name so they appear on the same row in the comparison table.
_ASIMPY_ALIASES = {
    "Barrier":            "Barrier / Barrier (via Event)",
    "FirstOf":            "FirstOf / AnyOf",
    "FirstOf (blocking)": "FirstOf / AnyOf (blocking)",
    "PriorityQueue":      "PriorityQueue / PriorityStore",
}

_SIMPY_ALIASES = {
    "Barrier (via Event)": "Barrier / Barrier (via Event)",
    "AnyOf":               "FirstOf / AnyOf",
    "AnyOf (blocking)":    "FirstOf / AnyOf (blocking)",
    "PriorityStore":       "PriorityQueue / PriorityStore",
}


def _apply_aliases(df, aliases):
    """Return df with Feature values renamed according to aliases."""
    return df.with_columns(
        pl.col("Feature").replace(
            old=list(aliases.keys()),
            new=list(aliases.values()),
        )
    )


def benchmark():
    """Run both benchmark suites and return a combined comparison DataFrame.

    Columns:
      Feature       - benchmark name
      asimpy        - asimpy instructions per execution (null if not measured)
      simpy         - simpy instructions per execution (null if not measured)
      asimpy/simpy  - ratio of asimpy to simpy cost (null if either is missing)
    """
    asimpy_df = _apply_aliases(
        asimpy_benchmark().select(
            pl.col("Feature"),
            pl.col("Instr/Execution").alias("asimpy"),
        ),
        _ASIMPY_ALIASES,
    )
    simpy_df = _apply_aliases(
        simpy_benchmark().select(
            pl.col("Feature"),
            pl.col("Instr/Execution").alias("simpy"),
        ),
        _SIMPY_ALIASES,
    )

    df = asimpy_df.join(simpy_df, on="Feature", how="full", coalesce=True)
    df = df.with_columns(
        (pl.col("asimpy") / pl.col("simpy")).alias("asimpy/simpy")
    )
    return df.sort("Feature")


def _fmt_float(val):
    """Format a float to one decimal place, or 'N/A' for None."""
    return "N/A" if val is None else f"{val:.1f}"


def _fmt_ratio(val):
    """Format a ratio to three decimal places, or 'N/A' for None."""
    return "N/A" if val is None else f"{val:.3f}"


def parse_args():
    parser = argparse.ArgumentParser(description="Compare asimpy and simpy benchmark results.")
    parser.add_argument(
        "--format",
        metavar="NAME",
        choices=["csv", "markdown"],
        default="markdown",
        help="output format: csv or markdown (default: markdown)",
    )
    parser.add_argument(
        "--output",
        metavar="FILENAME",
        help="write results to this file (default: stdout)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    df = benchmark()

    newline = "" if args.format == "csv" else None
    out = open(args.output, "w", newline=newline) if args.output else sys.stdout
    try:
        if args.format == "csv":
            writer = csv.writer(out)
            writer.writerow(["Feature", "asimpy", "simpy", "asimpy/simpy"])
            for feature, asimpy, simpy, ratio in df.iter_rows():
                writer.writerow([feature, _fmt_float(asimpy), _fmt_float(simpy), _fmt_ratio(ratio)])
        else:
            table = PrettyTable()
            table.set_style(TableStyle.MARKDOWN)
            table.field_names = ["Feature", "asimpy", "simpy", "asimpy/simpy"]
            table.align["Feature"] = "l"
            table.align["asimpy"] = "r"
            table.align["simpy"] = "r"
            table.align["asimpy/simpy"] = "r"
            for feature, asimpy, simpy, ratio in df.iter_rows():
                table.add_row([feature, _fmt_float(asimpy), _fmt_float(simpy), _fmt_ratio(ratio)])
            print(table, file=out)
    finally:
        if args.output:
            out.close()


if __name__ == "__main__":
    main()
