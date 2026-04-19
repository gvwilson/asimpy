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
    """Return df with feature values renamed according to aliases."""
    return df.with_columns(
        pl.col("feature").replace(
            old=list(aliases.keys()),
            new=list(aliases.values()),
        )
    )


def benchmark():
    """Run both benchmark suites and return a combined comparison DataFrame.

    Columns:
      feature       - benchmark name
      asimpy_instr  - asimpy instructions per execution (null if not measured)
      simpy_instr   - simpy instructions per execution (null if not measured)
      instr_ratio   - asimpy_instr / simpy_instr (null if either is missing)
      asimpy_sec    - asimpy seconds per execution (null if not measured)
      simpy_sec     - simpy seconds per execution (null if not measured)
      time_ratio    - asimpy_sec / simpy_sec (null if either is missing)
    """
    asimpy_df = _apply_aliases(
        asimpy_benchmark().select(
            pl.col("feature"),
            pl.col("instr_per_execution").alias("asimpy_instr"),
            pl.col("usec_per_execution").alias("asimpy_usec"),
        ),
        _ASIMPY_ALIASES,
    )
    simpy_df = _apply_aliases(
        simpy_benchmark().select(
            pl.col("feature"),
            pl.col("instr_per_execution").alias("simpy_instr"),
            pl.col("usec_per_execution").alias("simpy_usec"),
        ),
        _SIMPY_ALIASES,
    )

    df = asimpy_df.join(simpy_df, on="feature", how="full", coalesce=True)
    df = df.with_columns(
        (pl.col("asimpy_instr") / pl.col("simpy_instr")).alias("instr_ratio"),
        (pl.col("asimpy_usec") / pl.col("simpy_usec")).alias("time_ratio"),
    )
    return df.select(
        "feature", "asimpy_instr", "simpy_instr", "instr_ratio",
        "asimpy_usec", "simpy_usec", "time_ratio",
    ).sort("feature")


def _fmt_float(val):
    """Format a float to one decimal place, or 'N/A' for None."""
    return "N/A" if val is None else f"{val:.1f}"


def _fmt_usec(val):
    """Format a microseconds value to three decimal places, or 'N/A' for None."""
    return "N/A" if val is None else f"{val:.3f}"


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
            writer.writerow(["feature", "asimpy_instr", "simpy_instr", "instr_ratio", "asimpy_usec", "simpy_usec", "time_ratio"])
            for feature, asimpy_instr, simpy_instr, instr_ratio, asimpy_usec, simpy_usec, time_ratio in df.iter_rows():
                writer.writerow([
                    feature,
                    _fmt_float(asimpy_instr), _fmt_float(simpy_instr), _fmt_ratio(instr_ratio),
                    _fmt_usec(asimpy_usec), _fmt_usec(simpy_usec), _fmt_ratio(time_ratio),
                ])
        else:
            table = PrettyTable()
            table.set_style(TableStyle.MARKDOWN)
            table.field_names = ["feature", "asimpy_instr", "simpy_instr", "instr_ratio", "asimpy_usec", "simpy_usec", "time_ratio"]
            table.align["feature"] = "l"
            table.align["asimpy_instr"] = "r"
            table.align["simpy_instr"] = "r"
            table.align["instr_ratio"] = "r"
            table.align["asimpy_usec"] = "r"
            table.align["simpy_usec"] = "r"
            table.align["time_ratio"] = "r"
            for feature, asimpy_instr, simpy_instr, instr_ratio, asimpy_usec, simpy_usec, time_ratio in df.iter_rows():
                table.add_row([
                    feature,
                    _fmt_float(asimpy_instr), _fmt_float(simpy_instr), _fmt_ratio(instr_ratio),
                    _fmt_usec(asimpy_usec), _fmt_usec(simpy_usec), _fmt_ratio(time_ratio),
                ])
            print(table, file=out)
    finally:
        if args.output:
            out.close()


if __name__ == "__main__":
    main()
