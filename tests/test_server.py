import datetime
import os
import subprocess
import sys
import socket
import ssl
import threading
import time
import configparser
import multiprocessing

import psutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.exceptions import FileSystemError
from src.search.search_algorithms import search_regex
from src.server import main, handle_client, ServerError
from src.logger import setup_logger
from src.ssl_utils import create_ssl_context

logger = setup_logger("qserver", "DEBUG", "server.log")
test_files = ["test_server_config.ini"]


required_pattern = "4;0;1;28;0;7;5;0;"


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    conn.recv.return_value = b"test query\n"
    return conn


@pytest.fixture
def mock_logger():
    return MagicMock()


"""Checks if a test file exists and is not empty; otherwise, creates a dummy file."""
# def tmp_path(pathname: str):
name = "test_server_config.ini"
temp_path = os.path.join("tests")
project_root = os.path.dirname(os.path.dirname(__file__))  # Move up from src/
tmp_path = os.path.abspath(os.path.join(project_root, temp_path))
logger.info(tmp_path)


# Helper function to get a free port
def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


# Helper to wait for server to start
def wait_for_server(port, host='localhost', timeout=5.0):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.1):
                return True
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.1)
    return False


# Base config fixture
@pytest.fixture
def base_config():
    for file_name in range(len(test_files)):
        project_root = Path(__file__).resolve().parent.parent
        # Build the config path relative to that root
        config_path = project_root / "tests" / f"{file_name}"

        # Resolve to an absolute path, to be extra safe
        file_path = config_path.resolve()

        if not file_path.is_file():
            assert f"Search file not found: {file_path}"
            # raise FileSystemError(
            #     operation="read",
            #     path=file_path,
            #     reason="File not found"
            # )
        if test_files[file_name]:
            free_port = get_free_port()

            return {
                "HOST": "127.0.0.1",
                "PORT": f"{free_port}",
                "LINUXPATH": "tests/data/500k.txt",
                "REREAD_ON_QUERY": "False",
                "MAX_PAYLOAD_SIZE": "1024",
                "SSL_ON": "False",
                "SSL_MODE": "none",
                "SSL_VERIFY_CLIENT": "none",
                "CERTFILE": "certs/server.crt",
                "KEYFILE": "certs/server.key",
                "LOG_LEVEL": "DEBUG",
                "CAFILE": "certs/ca.crt",
                "LOG_FILE": "test_server.log"
            }


# Fixture to create config file
@pytest.fixture
def config_file(path, base_config):
    path = tmp_path
    config_path = path

    config = configparser.ConfigParser()
    config["server"] = base_config

    with open(config_path, 'w') as f:
        config.write(f)

    return config_path


def test_handle_client_found(mock_conn, base_config, mock_logger):
    lines_cache = {"test query"}
    handle_client(mock_conn, (base_config["HOST"], base_config["PORT"]), base_config, mock_logger, lines_cache)

    mock_conn.sendall.assert_called_once_with(b"STRING EXISTS\n")
    mock_logger.debug.assert_called()


def test_handle_client_not_found(mock_conn, base_config, mock_logger):
    lines_cache = set()
    handle_client(mock_conn, (base_config["HOST"], base_config["PORT"]), base_config, mock_logger, lines_cache)

    mock_conn.sendall.assert_called_once_with(b"STRING NOT FOUND\n")
    mock_logger.debug.assert_called()


def test_handle_client_empty_data(mock_conn, base_config, mock_logger):
    mock_conn.recv.return_value = b""
    handle_client(mock_conn, (base_config["HOST"], base_config["PORT"]), base_config, mock_logger)

    mock_conn.sendall.assert_not_called()
    mock_conn.close.assert_called_once()


def test_handle_client_error(mock_conn, base_config, mock_logger):
    mock_conn.recv.side_effect = Exception("Test error")
    handle_client(mock_conn, (base_config["HOST"], base_config["PORT"]), base_config, mock_logger)

    mock_logger.error.assert_called_once()
    mock_conn.close.assert_called_once()


# def test_search_returns_true_on_match(mock_conn, base_config):
#     assert search_regex(str(base_config["LINUXPATH"]), "2;0;0;5;8;4;5;3;") is True
#
#
# def test_search_returns_false_on_miss(base_config):
#     assert search_regex(base_config['LINUXPATH'], "no;such;sequence;") is False


# ── Helper: poll until the server is listening on localhost:<port> ─────────────
SERVER_STARTUP_TIMEOUT = 10.0
SERVER_POLL_INTERVAL = 0.1


# ── The pytest fixture itself ───────────────────────────────────────────────────
@ pytest.fixture
def server_process(base_config: dict, tmp_path: Path):
    """
    1) Calls get_free_port() and injects that into base_config["PORT"].
    2) Writes a config.ini (using configparser) under [server] with that dynamic port.
    3) Launches the server via subprocess.Popen, capturing stdout/stderr.
    4) Waits up to SERVER_STARTUP_TIMEOUT for the new port to be open.
       If the process dies early or the port never opens, we fail with stderr+stdout.
    5) Yields the Popen object.
    6) On teardown, sends SIGTERM → wait → SIGKILL if necessary.
    """

    # ──  pick a free port and override base_config["PORT"] ───────────────
    free_port = get_free_port()
    project_root = Path(__file__).resolve().parent.parent
    # Build the config path relative to that root
    config_path = project_root / "tests" / name

    # Resolve to an absolute path, to be extra safe
    file_path = config_path.resolve()

    # config_path = tmp_path / "test_server_config.ini"
    with open(file_path, "w") as cfg_file:
        for key, value in base_config.items():
            cfg_file.write(f"{key}={value}\n")

        logger.info(f"config file updated {config_path}")
    # ── launch the server process ───────────────────────────────────────
    # Replace "yourapp.server" + "--config" with whatever your actual entrypoint is
    python_executable = "python3"
    cmd = [
        python_executable,
        "-m",
        "src.server.main",            # <– your real module or script
        "--config",
        str(config_path),
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # ── wait until either (a) port is open or (b) process exits ────────
    deadline = time.time() + SERVER_STARTUP_TIMEOUT
    while time.time() < deadline:
        # If the child already died, grab its stderr/stdout and fail immediately:
        if proc.poll() is not None:
            stderr_output = proc.stderr.read()
            stdout_output = proc.stdout.read()
            logger.error("Server process exited prematurely")
            # pytest.fail(
            #     f"Server process exited prematurely "
            #     f"(exit code={proc.returncode}).\n\n"
            #     f"Stdout:\n{stdout_output}\n\nStderr:\n{stderr_output}"
            # )

        if wait_for_server(free_port, timeout=0.2):
            # We successfully opened a socket → server is “up.”

            break

        # Otherwise, loop until the deadline
        time.sleep(0.05)
    else:
        # If we get here, we never saw the port open within the timeout window
        stderr_output = proc.stderr.read()
        stdout_output = proc.stdout.read()
        proc.terminate()
        logger.error(f"Server failed to start listening on port {free_port}")

        # pytest.fail(
        #     f"Server failed to start listening on port {free_port} "
        #     f"after {SERVER_STARTUP_TIMEOUT:.1f}s.\n\n"
        #     f"Stdout:\n{stdout_output}\n\nStderr:\n{stderr_output}"
        # )

    # ── yield the Popen so tests can make HTTP calls ────────────────────
    yield proc

    # ── teardown/cleanup ────────────────────────────────────────────────
    if proc.poll() is None:
        proc.terminate()  # send SIGTERM
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()   # send SIGKILL if it didn’t die in time


@pytest.fixture
def server_ssl_process(ssl_config: dict, tmp_path: Path):
    """
    1) Calls get_free_port() and injects that into base_config["PORT"].
    2) Writes a config.ini (using configparser) under [server] with that dynamic port.
    3) Launches the server via subprocess.Popen, capturing stdout/stderr.
    4) Waits up to SERVER_STARTUP_TIMEOUT for the new port to be open.
       If the process dies early or the port never opens, we fail with stderr+stdout.
    5) Yields the Popen object.
    6) On teardown, sends SIGTERM → wait → SIGKILL if necessary.
    """

    # ── Step 1: pick a free port and override base_config["PORT"] ───────────────
    free_port = get_free_port()
    project_root = Path(__file__).resolve().parent.parent
    # Build the config path relative to that root
    config_path = project_root / "tests" / name

    # Resolve to an absolute path, to be extra safe
    file_path = config_path.resolve()

    # config_path = tmp_path / "test_server_config.ini"
    with open(file_path, "w") as cfg_file:
        for key, value in ssl_config.items():
            cfg_file.write(f"{key}={value}\n")

        logger.info(f"config file updated {config_path}")
        # config.write(cfg_file)

    # ── launch the server process ───────────────────────────────────────
    # Replace "yourapp.server" + "--config" with whatever your actual entrypoint is
    # Start server process
    proc = subprocess.Popen(
        ["python3", "-m", "src.server.main", "--config", str(config_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for server to start
    deadline = time.time() + SERVER_STARTUP_TIMEOUT
    stdout_output = ""
    stderr_output = ""
    server_started = False

    while time.time() < deadline:
        # Check if process exited
        if proc.poll() is not None:
            # Read output before pipes close
            stdout_output, stderr_output = proc.communicate()
            break

        # Check if port is open
        if wait_for_server(free_port, timeout=0.1):
            server_started = True
            break

        time.sleep(0.05)

    # Handle startup failures
    if not server_started:
        if proc.poll() is None:
            # Process still running but port not open
            stdout_output, stderr_output = proc.communicate(timeout=1)
            proc.terminate()
            logger.error(
                f"Server failed to start on port {free_port}\n"
                f"STDOUT:\n{stdout_output}\nSTDERR:\n{stderr_output}"
            )
        else:
            # Process exited prematurely
            logger.error(
                f"Server exited prematurely (code={proc.returncode})\n"
                f"STDOUT:\n{stdout_output}\nSTDERR:\n{stderr_output}"
            )

    yield proc

    # Cleanup
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()

    # client code
    # Build the OpenSSL client command
    # openssl_cmd = [
    #     "openssl", "s_client",
    #     "-quiet",
    #     "-connect", f"{ssl_config['HOST']}:{ssl_config['PORT']}",
    #     "-cert", ssl_config["CERTFILE"],
    #     "-key", ssl_config["KEYFILE"],
    #     "-CAfile", ssl_config["CAFILE"]
    # ]

    # Execute the command
    # proc = subprocess.Popen(
    #     openssl_cmd,
    #     stdin=subprocess.PIPE,
    #     stdout=subprocess.PIPE,
    #     stderr=subprocess.PIPE
    # )
    # Create the input data
    # required_pattern = "4;0;1;28;0;7;5;0;"
    # input_data = f"{required_pattern}\n".encode()
    #
    # # Send query and get response
    # stdout, stderr = proc.communicate(input=input_data)
    #
    # # Verify response
    # assert stdout in stdout

    # ── wait until either (a) port is open or (b) process exits ────────
    # deadline = time.time() + SERVER_STARTUP_TIMEOUT
    # while time.time() < deadline:
    #     # If the child already died, grab its stderr/stdout and fail immediately:
    #     if proc.poll() is not None:
    #         stderr_output = proc.stderr.read()
    #         stdout_output = proc.stdout.read()
    #         logger.error(f"{stdout_output} Server process exited prematurely")
    #         # pytest.fail(
    #         #     f"Server process exited prematurely "
    #         #     f"(exit code={proc.returncode}).\n\n"
    #         #     f"Stdout:\n{stdout_output}\n\nStderr:\n{stderr_output}"
    #         # )
    #
    #     if wait_for_server(ssl_config['PORT'], timeout=0.2):
    #         # We successfully opened a socket → server is “up.”
    #         break
    #
    #     # Otherwise, loop until the deadline
    #     time.sleep(0.05)
    # else:
    #     # If we get here, we never saw the port open within the timeout window
    #     stderr_output = proc.stderr.read()
    #     stdout_output = proc.stdout.read()
    #     proc.terminate()
    #     logger.error(f"Server failed to start listening on port {free_port}")
    #
    # # ── yield the Popen so tests can make HTTP calls ────────────────────
    # yield proc
    #
    # # ── teardown/cleanup ────────────────────────────────────────────────
    # if proc.poll() is None:
    #     proc.terminate()  # send SIGTERM
    #     try:
    #         proc.wait(timeout=2.0)
    #     except subprocess.TimeoutExpired:
    #         proc.kill()   # send SIGKILL if it didn’t die in time


# =========================================
# Test Cases (Parameterized by test_file)
# =========================================
# Update the test to check process status correctly
def test_server_start_stop(server_process, base_config):
    """Verify server starts and stops correctly with each test file."""
    # Check if process is running using psutil
    try:
        parent = psutil.Process(server_process.pid)
        children = parent.children(recursive=True)
        assert any(p.is_running() for p in [parent] + children)
    except psutil.NoSuchProcess:
        logger.error("Server process not running")

    # Test connection to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((base_config["HOST"], int(base_config["PORT"])))
        sock.listen()


# SSL/ certs context setup
@pytest.fixture()
def ssl_config():
    for file_name in range(len(test_files)):
        project_root = Path(__file__).resolve().parent.parent
        # Build the config path relative to that root
        config_path = project_root / "tests" / f"{file_name}"

        # Resolve to an absolute path, to be extra safe
        file_path = config_path.resolve()

        if not file_path.is_file():
            assert f"Search file not found: {file_path}"
            # raise FileSystemError(
            #     operation="read",
            #     path=file_path,
            #     reason="File not found"
            # )
        if test_files[file_name]:
            free_port = get_free_port()
            # Build the config path relative to that root
            config_path = project_root / "certs"

            return {
                "HOST": "127.0.0.1",
                "PORT": f"{free_port}",
                "LINUXPATH": "tests/data/500k.txt",
                "REREAD_ON_QUERY": "False",
                "MAX_PAYLOAD_SIZE": "1024",
                "SSL_ON": "True",
                "SSL_MODE": "cert",
                "SSL_VERIFY_CLIENT": "True",
                "CERTFILE": f"{config_path}/server.crt",
                "KEYFILE": f"{config_path}/server.key",
                "LOG_LEVEL": "DEBUG",
                "CAFILE": f"{config_path}/ca.crt",
                "LOG_FILE": "test_server.log"
            }


def run_ssl_query(query: str, port: int, timeout: float = 2.0) -> str:
    project_root = Path(__file__).resolve().parent.parent
    # Build the config path relative to that root
    config_path = project_root / "certs"
    openssl_cmd = [
        "openssl", "s_client",
        "-quiet",
        "-connect", f"127.0.0.1:{port}",
        "-cert", str(config_path / "client.crt"),
        "-key", str(config_path / "client.key"),
        "-CAfile", str(config_path / "ca.crt")
    ]

    result = subprocess.run(
        openssl_cmd,
        input=f"{query}\n",
        text=True,
        capture_output=True,
        timeout=timeout
    )
    return result.stdout.strip()


def test_ssl_start_stop(server_ssl_process, ssl_config, mock_logger, mock_conn):
    """Verify server starts and stops correctly with each test file."""
    # Check if process is running using psutil
    try:
        parent = psutil.Process(server_ssl_process.pid)
        children = parent.children(recursive=True)
        assert any(p.is_running() for p in [parent] + children)
    except psutil.NoSuchProcess:
        logger.error("Server process not running")

    # Test connection to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ssl_config["HOST"], int(ssl_config["PORT"])))
        sock.listen()

        # SSL context based on SSL_ON and SSL_MODE
        if ssl_config['SSL_ON']:
            ssl_ctx = create_ssl_context(
                ssl_config['CERTFILE'], ssl_config['KEYFILE'], ssl_config['SSL_VERIFY_CLIENT'], ssl_config['CAFILE'])
            if ssl_ctx is None:
                raise ServerError("Invalid SSL configuration")
            sock = ssl_ctx.wrap_socket(sock, server_side=True)
            logger.info("SSL/TLS enabled")
            print(f"Connected to {ssl_config['HOST']}:{ssl_config['PORT']} (SSL={'on' if ssl_config['SSL_ON'] else 'off'})")

        # Create the input data
        # required_pattern = "4;0;1;28;0;7;5;0;"
        # lines_cache = {required_pattern}
        #
        # input_data = f"{required_pattern}\n".encode()
        # #
        # handle_client(mock_conn, (ssl_config["HOST"], int(ssl_config["PORT"])), ssl_config, mock_logger, lines_cache=input_data)
        # response = run_ssl_query(required_pattern, ssl_config["PORT"])
        # assert "STRING EXISTS" in response