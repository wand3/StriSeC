import socket
import sys
import threading
from typing import Callable, Tuple, Dict, Any

from src.exceptions import ServerError


def start_threaded_server(
    sock: socket.socket,
    handler: Callable[[socket.socket, tuple], None],
    logger
) -> None:
    """
    Accepts connections on 'sock' and dispatches each to 'handler' in a new thread.
    """
    logger.info("Server listening for connections...")
    while True:
        client_sock, addr = sock.accept()
        logger.debug(f"Accepted connection from {addr}")
        thread = threading.Thread(target=handler, args=(client_sock, addr), daemon=True)
        thread.start()


