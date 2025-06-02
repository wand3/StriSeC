import mmap
import os
import re
import subprocess
import linecache
from pathlib import Path
from typing import Set


def load_lines(path: str) -> Set[str]:
    """
    Reads the entire file at `path` once and returns a set of stripped lines.
    Use this when REREAD_ON_QUERY is False for O(1) lookups.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Search file not found: {path}")

    with p.open('r', encoding='utf-8', errors='ignore') as f:
        return {line.rstrip('\n') for line in f}


def search_cached(lines: Set[str], query: str) -> bool:
    """
    Checks if `query` exactly matches any line in the preloaded `lines` set.
    Returns True if found; False otherwise.
    """
    # exact match: query must equal a full line
    return query in lines


def search_dynamic(path: str, query: str) -> bool:
    """
    Streams through the file at `path`, checking each line for an exact match to `query`.
    Use this when REREAD_ON_QUERY is True, so the file is reloaded on every query.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Search file not found: {path}")

    with p.open('r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # strip newline and compare exact equality
            if line.rstrip('\n') == query:
                return True
    return False


def search_regex(path: str, query: str) -> bool:
    """
    Search for an exact match of the query string in a file using regex.

    Replicates server's matching logic:
    1. Reads lines while stripping newline characters
    2. Performs exact match comparison using regex
    3. Handles special characters in query safely

    Args:
        path: Path to search file
        query: Exact string to search for

    Returns:
        True if exact match found, False otherwise
    """
    # Create safe regex pattern for exact match
    pattern = re.compile(f'^{re.escape(query)}$')

    try:
        with open(path, 'r', encoding='utf-8') as file:
            for line in file:
                # Mirror server's line processing
                stripped_line = line.rstrip('\n')

                # Check for exact match using regex
                if pattern.match(stripped_line):
                    return True
        return False

    except FileNotFoundError:
        raise ValueError(f"Search file not found at {path}")
    except UnicodeDecodeError:
        raise ValueError("File contains invalid UTF-8 characters")


def search_mmap(path: str, query: str) -> bool:
    """
    Search for exact string match in a file using memory-mapped I/O.

    Features:
    - O(1) disk access via mmap
    - Efficient whole-file search

    Args:
        path: Path to text file
        query: Exact string to search for

    Returns:
        True if exact match found as a complete line, False otherwise
    """
    query_bytes = query.encode('utf-8')
    line_break = len(os.linesep.encode('utf-8'))  # Handle \n vs \r\n

    try:
        with open(path, 'rb') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                pos = mm.find(query_bytes)
                if pos != -1:
                    return True
                return False

    except FileNotFoundError:
        raise ValueError(f"Search file not found: {path}")
    except Exception as e:
        raise RuntimeError(f"MMap search failed: {e}")


def search_grep(path: str, query: str) -> bool:
    """
    Search for exact string match in a file using grep.

    Features:
    - Uses grep's optimized search algorithms
    - Proper file existence checking

    Args:
        path: Path to text file
        query: Exact string to search for

    Returns:
        True if exact match found, False otherwise

    Raises:
        ValueError: If file doesn't exist
        RuntimeError: If grep execution fails
    """
    if not os.path.exists(path):
        raise ValueError(f"Search file not found: {path}")

    try:
        try:
            subprocess.check_output(['grep', query, path])
            return True
        except subprocess.CalledProcessError:
            return False
    except FileNotFoundError:
        raise RuntimeError("grep command not found - requires grep installation")
    except Exception as e:
        raise RuntimeError(f"Search failed: {str(e)}")


def search_linecache(path: str, query: str) -> bool:
    """
    Efficient exact line search in large files using linecache.

    Features:
    - Memory-efficient sequential access
    - Automatic line ending handling
    - Exact match validation
    - Optimized for large files (500k+ lines)

    Args:
        path: Path to text file
        query: Exact string to find (e.g. "7;0;1;26;0;8;3;0;")

    Returns:
        True if exact match found, False otherwise

    Raises:
        ValueError: If file doesn't exist
    """
    if not os.path.exists(path):
        raise ValueError(f"File not found: {path}")

    line_number = 1
    query = query.rstrip('\r\n')  # Normalize query

    while True:
        # Get line while preserving linecache's internal caching
        raw_line = linecache.getline(str(path), line_number)
        # Strip line endings using server's matching logic
        line = raw_line.rstrip('\r\n')

        # Empty line indicates EOF (linecache returns '' past last line)
        if not raw_line:
            break

        if line == query:
            return True

        line_number += 1

    return False


# def search_willow(path: str, query: str, index_dir="exact_index") -> bool:
#     """
#     Searches for an exact query as a whole line within a large text file
#     using Whoosh with a KEYWORD field for exact matching.
#
#     Args:
#         path: The path to the .txt file (used for initial indexing if the index doesn't exist).
#         query: The exact string to search for.
#         index_dir: The directory where the Whoosh index will be stored.
#
#     Returns:
#         True if the query is found as an exact whole line in the file, False otherwise.
#     """
#     schema = Schema(line=KEYWORD(stored=True, unique=True))  # Use KEYWORD for exact matching
#
#     if not os.path.exists(index_dir):
#         os.makedirs(index_dir)
#
#     if not exists_in(index_dir):
#         print(f"Creating exact match index in: {index_dir}")
#         ix = create_in(index_dir, schema)
#         writer = ix.writer()
#         try:
#             with open(path, 'r') as f:
#                 for line in f:
#                     writer.add_document(line=line.strip())
#             writer.commit()
#         except FileNotFoundError:
#             print(f"Error: File not found at path: {path}")
#             return False
#     else:
#         print(f"Opening existing exact match index in: {index_dir}")
#         ix = open_dir(index_dir)
#
#     try:
#         searcher = ix.searcher()
#         parser = QueryParser("line", schema)
#         # We can search directly for the keyword without quotes for exact match
#         q = parser.parse(query)
#         results = searcher.search(q)
#         return len(results) > 0
#     finally:
#         if 'searcher' in locals():
#             searcher.close()
#         ix.close()
