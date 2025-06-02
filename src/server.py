import os
import socket
import ssl
import argparse
from .config_loader import load_config
from .ssl_utils import create_ssl_context
from .threads import start_threaded_server
from .logger import setup_logger
from .exceptions import ServerError
import time
from typing import Dict, Any, Tuple
from .search.search_algorithms import load_lines, search_cached, search_linecache


def handle_client(
    conn: socket.socket,
    addr: Tuple[str, int],
    cfg: Dict[str, Any],
    logger,
    lines_cache: set = None
) -> None:
    """
    Handle a single client connection:

    Steps:
    1. Receive raw data up to `max_payload_size` bytes.
    2. Strip terminal nulls (\x00) and whitespace/newline characters.
    3. Decode bytes to UTF-8 string (ignore invalid bytes).
    4. Measure start time for performance logging.
    5. Perform exact-line search:
       - If `REREAD_ON_QUERY` is True: stream the file on each query (search_dynamic).
       - Otherwise: lookup in preloaded `lines_cache` set (search_cached).
    6. Calculate elapsed time in milliseconds.
    7. Formulate response:
       - "STRING EXISTS\n" if found, else "STRING NOT FOUND\n".
    8. Send response back to client.
    9. Log a detailed DEBUG message:
       - Query string (e.g. "4;0;1;28;0;7;5;0;")
       - Client IP address
       - Execution time
       - Whether the string was found
    10. Clean up and close the connection.

    Example Input:
        raw data: b"4;0;1;28;0;7;5;0;\n"
        query: "4;0;1;28;0;7;5;0;"

    """
    try:
        # 1. Receive raw bytes from the client
        raw = conn.recv(cfg["MAX_PAYLOAD_SIZE"])
        if not raw:
            # No data received; close connection
            return

        # 2-3. Strip nulls/newlines and decode
        #    e.g. raw = b"4;0;1;28;0;7;5;0;\n" -> query = "4;0;1;28;0;7;5;0;"
        query = raw.rstrip(b"\x00\r\n").decode("utf-8", errors="ignore")
        logger.debug(f"Decoded query from {addr[0]}: '{query}'")
        logger.info(f"'{query}'")

        # 4. Start timing
        t0 = time.perf_counter()

        # 5. Exact match search
        # if cfg.get("REREAD_ON_QUERY", False):
        #
        #     # Read file on each query to catch updates
        #     # found = search_dynamic(cfg["LINUXPATH"], query)
        #     # found = search_regex(cfg["LINUXPATH"], query)
        #     # found = search_mmap(cfg["LINUXPATH"], query)
        #     # found = search_grep(cfg["LINUXPATH"], query)
        #     # found = search_linecache(cfg["LINUXPATH"], query)
        #     found = search_linecache(cfg["LINUXPATH"], query)
        # else:
        #     # Use preloaded set for O(1) lookup
        #     found = search_cached(lines_cache, query)

        # 4. Determine search mode
        reread_flag = cfg.get("REREAD_ON_QUERY", False)
        # Normalize boolean-like strings
        if isinstance(reread_flag, str):
            reread_flag = reread_flag.lower() in ("1", "true", "yes", "on")

        if reread_flag:
            # Dynamic: read file on each query
            found = search_linecache(cfg["LINUXPATH"], query)
        else:
            # Static: ensure lines_cache is loaded
            if lines_cache is None:
                try:
                    lines_cache = load_lines(cfg["LINUXPATH"])
                    logger.info(f"Lazily preloaded {len(lines_cache)} lines for caching.")
                except Exception as ex:
                    logger.error(f"Failed to preload cache: {ex}")
                    raise
            found = search_cached(lines_cache, query)

        # 6. Compute elapsed time
        elapsed_ms = (time.perf_counter() - t0) * 1000

        # 7. Prepare the response bytes
        if found:
            response = b"STRING EXISTS\n"
        else:
            response = b"STRING NOT FOUND\n"

        # 8. Send the response back to the client
        conn.sendall(response)

        # 9. Detailed debug log
        logger.debug(
            f"Query=\"{query}\" | IP={addr[0]} | Time={elapsed_ms:.2f}ms | Found={found}"
        )
        print(response)

    except Exception as e:
        # On any error, log with ERROR level
        logger.error(f"Error handling client {addr}: {e}")
        # Optionally, could send an error message to client here
    finally:
        # Attempt proper TLS close_notify exchange
        ssl_conn = isinstance(conn, ssl.SSLSocket)
        if ssl_conn:
            try:
                # send close_notify and wait for peer's close_notify
                conn.unwrap()
            except Exception as e:
                logger.debug(f"Error during TLS unwrap for {addr}: {e}")
        try:
            conn.close()
        except Exception:
            pass


def main():
    # Load configuration
    parser = argparse.ArgumentParser(description="String-search TCP server")
    parser.add_argument(
        "-c", "--config", default="config/server_config.ini",
        help="config/server_config.ini"
    )
    args = parser.parse_args()

    cfg = load_config(args.config)

    # Validate essential config
    required = ["HOST", "PORT", "LINUXPATH", "REREAD_ON_QUERY", "MAX_PAYLOAD_SIZE", "SSL_ON", "SSL_MODE", "SSL_VERIFY_CLIENT", "CERTFILE", "KEYFILE",
                "LOG_LEVEL", "CAFILE", "LOG_FILE"]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ServerError(f"Missing required config keys: {', '.join(missing)}")

    # Ensure LINUXPATH exists and is absolute
    search_file_path = cfg["LINUXPATH"]
    if not os.path.isabs(search_file_path):
        # If relative path, make it relative to project root
        project_root = os.path.dirname(os.path.dirname(__file__))  # Move up from src/
        search_file_path = os.path.abspath(os.path.join(project_root, search_file_path))

    if not os.path.isfile(search_file_path):
        raise ServerError(f"Search file not found at {search_file_path}")

    cfg["LINUXPATH"] = search_file_path  # Update config with correct absolute path
    logger = setup_logger("qserver", cfg["LOG_LEVEL"], cfg["LOG_FILE"])

    # Preload lines if static mode for faster queries
    lines_cache = None
    if not cfg.get("REREAD_ON_QUERY", False):
        try:
            lines_cache = load_lines(cfg["LINUXPATH"])
            logger.info(f"Preloaded {len(lines_cache)} lines for caching.")
        except Exception as e:
            logger.error(f"Failed to load search file: {e}")
            raise ServerError("Could not preload search file")

    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((cfg["HOST"], cfg["PORT"]))
    sock.listen()

    # SSL context based on SSL_ON and SSL_MODE
    if cfg['SSL_ON']:
        ssl_ctx = create_ssl_context(
            cfg['CERTFILE'], cfg['KEYFILE'], cfg['SSL_VERIFY_CLIENT'], cfg['CAFILE'])
        if ssl_ctx is None:
            raise ServerError("Invalid SSL configuration")
        sock = ssl_ctx.wrap_socket(sock, server_side=True)
        logger.info("SSL/TLS enabled")
        print(f"Connected to {cfg['HOST']}:{cfg['PORT']} (SSL={'on' if cfg['SSL_ON'] else 'off'})")

    # Start handling clients
    start_threaded_server(sock, lambda c,a: handle_client(c, a, cfg, logger), logger)


if __name__ == "__main__":
    main()
