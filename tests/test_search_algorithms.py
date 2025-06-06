from pathlib import Path

import pytest
import tempfile
import os
from tests.data.data_generator import create_dummy_file


from src.exceptions import ServerError, FileSystemError
from src.search.search_algorithms import (
    load_lines, search_cached, search_dynamic, search_regex,
    search_mmap, search_grep, search_linecache
)

QUERY_PRESENT = "2;0;0;5;8;4;5;3;"
QUERY_ABSENT = "no;match;here"
test_files = ["10k.txt", "250k.txt", "500k.txt", "750k.txt", "1m.txt"]

# List of all search functions to parametrize tests
SEARCH_FUNCTIONS = [
    search_dynamic,
    search_regex,
    search_mmap,
    search_grep,
    search_linecache
]

def get_test_files(name: str) -> bool:
    """Checks if a test file exists and is not empty; otherwise, creates a dummy file."""
    search_file_path = os.path.join("tests/data", name)

    # Ensure absolute path
    if not os.path.isabs(search_file_path):
        project_root = os.path.dirname(os.path.dirname(__file__))  # Move up from src/
        search_file_path = os.path.abspath(os.path.join(project_root, search_file_path))

    # Check if file exists and is not empty
    if os.path.isfile(search_file_path) and os.path.getsize(search_file_path) > 0:
        return True
    else:
        # Filesystem error
        raise FileSystemError(
            operation="read",
            path=search_file_path,
            reason="File not found"
        )
        create_dummy_file(filename="10k.txt", num_lines=10000, pattern_length=8)
        return False


@pytest.fixture
def validate_test_files():
    ctest_files = test_files
    """Loops through a list of test files and checks if all satisfy the get_test_files function."""
    return all(get_test_files(name) for name in ctest_files)


def test_files_satisfy_load_lines():
    """Loops through each filename, checks if it exists in the tests/data directory,
    and asserts True if it satisfies the load_lines function."""
    for file_name in test_files:
        project_root = Path(__file__).resolve().parent.parent
        # Build the config path relative to that root
        config_path = project_root / "tests" / "data" / f"{file_name}"

        # Resolve to an absolute path, to be extra safe
        file_path = config_path.resolve()

        if not file_path.is_file():
            assert f"Search file not found: {file_path}"
            raise FileSystemError(
                operation="read",
                path=file_path,
                reason="File not found"
            )
        assert load_lines(str(file_path))


def test_search_cached():
    """Test case for search_cached function."""
    # Test data
    for file in test_files:
        project_root = Path(__file__).resolve().parent.parent
        # Build the config path relative to that root
        config_path = project_root / "tests" / "data" / f"{file}"

        # Resolve to an absolute path, to be extra safe
        file_path = config_path.resolve()

        # Test cases
        assert search_cached(set(str(file_path)), 'apple') == False, "Test Case 1 Failed"
        assert search_cached(set(str(file_path)), '2;0;0;') == False, "Test Case 2 Failed"
        assert search_cached(set(str(file_path)), 'grape') == False, "Test Case 3 Failed"
        assert search_cached(set(str(file_path)), '') == False, "Test Case 4 Failed"
        print("All test cases for search_cached passed!")


@pytest.mark.parametrize("func", SEARCH_FUNCTIONS)
def test_positive_match(func, files=test_files):
    """Test pattern found in files."""
    for file in files:
        project_root = Path(__file__).resolve().parent.parent
        # Build the config path relative to that root
        config_path = project_root / "tests" / "data" / f"{file}"

        # Resolve to an absolute path, to be extra safe
        file_path = config_path.resolve()
        assert func(str(file_path), QUERY_PRESENT) is True


@pytest.mark.parametrize("func", SEARCH_FUNCTIONS)
def test_negative_match(func, files=test_files):
    """Test pattern not found in files."""
    for file in files:
        project_root = Path(__file__).resolve().parent.parent
        # Build the config path relative to that root
        config_path = project_root / "tests" / "data" / f"{file}"

        # Resolve to an absolute path, to be extra safe
        file_path = config_path.resolve()
        assert func(str(file_path), QUERY_ABSENT) is False