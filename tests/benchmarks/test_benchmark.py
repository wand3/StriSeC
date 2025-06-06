# tests/test_benchmark.py
import csv
import os
import sys
from src.logger import setup_logger
import pytest
from pathlib import Path

# search algorithms
from src.search.search_algorithms import (
    search_dynamic,
    search_regex,
    search_mmap,
    search_grep,
    search_linecache,
    load_lines,
)


# Constants
def get_project_root() -> Path:
    """Locate project root based on common markers with priority system."""
    current_path = Path(__file__).resolve()  # Get current file's absolute path
    markers = [
        ("requirements.txt", "Python dependencies"),
        ("tests/data", "Test data directory"),  # Directly target your data structure
        ("src", "Source code directory")
    ]

    # Search upward through directory tree
    for parent in current_path.parents:
        for marker, description in markers:
            if (parent / marker).exists():
                print(f"Found project root at {parent} via {marker} ({description})")
                return parent

    # Fallback to current file's grandparent if no markers found
    return current_path.parent.parent.parent


# Usage examples
PROJECT_ROOT = get_project_root()
TEST_FILE = PROJECT_ROOT / "tests" / "data" / "1m.txt"
TEST_QUERY = "2;0;0;5;8;4;5;3;"

logger = setup_logger("qserver", "DEBUG", "benchmark.log")

# List of (label, function, needs_cache)
SEARCH_FUNCS = [
    ("dynamic", search_dynamic, False),
    ("regex", search_regex, False),
    ("mmap", search_mmap, False),
    ("grep", search_grep, False),
    ("linecache", search_linecache, False),
]

CSV_FILE = "benchmark_results.csv"
CSV_HEADERS = ["name", "filename", "mean (ms)", "stddev (ms)", "min (ms)", "max (ms)", "median (ms)", "ops/sec"]

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)


@pytest.mark.parametrize("label,func,needs_cache", SEARCH_FUNCS)
def test_search_speed(benchmark, label, func, needs_cache):
    """
    Benchmark each search function against the same sample file and query.
    """
    if needs_cache:
        # preload into a set
        lines_cache = load_lines(str(TEST_FILE))
        # benchmark the lookup
        found = benchmark(func, lines_cache, TEST_QUERY)
    else:
        # benchmark by re-reading or other strategy
        found = benchmark(func, TEST_FILE, TEST_QUERY)
        logger.info(found)
        logger.info(TEST_FILE)

    # sanity check
    assert found is True

    # Save result to CSV
    # Convert timing stats to milliseconds
    stats = benchmark.stats
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            label,
            TEST_FILE.name,
            round(stats['mean'] * 1000, 3),
            round(stats['stddev'] * 1000, 3),
            round(stats['min'] * 1000, 3),
            round(stats['max'] * 1000, 3),
            round(stats['median'] * 1000, 3),
            round(stats['ops'], 3)
        ])
