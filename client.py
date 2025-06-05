# client.py
import socket
import ssl
import argparse
from typing import Optional

from src.config_loader import load_client_config


def query_server(
        host: str,
        port: int,
        query: str,
        use_ssl: bool = False,
        ca_cert: Optional[str] = None,
        client_cert: Optional[str] = None,
        client_key: Optional[str] = None
) -> str:
    """
    Send a query to the server and return the response.

    Args:
        host: Server IP/hostname
        port: Server port
        query: Query string to send
        use_ssl: Enable SSL/TLS
        ca_cert: Path to CA certificate
        client_cert: Path to client certificate
        client_key: Path to client private key

    Returns:
        Server response as a string
    """
    # Create base TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Wrap with SSL if needed
        if use_ssl:
            context = ssl.create_default_context(
                ssl.Purpose.SERVER_AUTH,
                cafile=ca_cert
            )

            if client_cert and client_key:
                context.load_cert_chain(
                    certfile=client_cert,
                    keyfile=client_key
                )

            sock = context.wrap_socket(sock, server_hostname=host)

        # Connect and send query
        sock.connect((host, port))
        sock.sendall(query.encode('utf-8') + b'\n')  # Add terminating newline

        # Receive response (up to 1KB)
        response = sock.recv(1024).decode('utf-8').strip()
        return response

    finally:
        sock.close()


def main():
    parser = argparse.ArgumentParser(description="Query the string server")
    parser.add_argument(
        "-c", "--config", default="config/client_config.ini",
        help="config/client_config.ini"
    )
    # parser.add_argument("host", help="Server hostname/IP")
    # parser.add_argument("port", type=int, help="Server port")
    parser.add_argument("query", help="Query string to send")
    # parser.add_argument("--ssl", action="store_true", help="Enable SSL/TLS")
    # parser.add_argument("--ca-cert", help="CA certificate file")
    # parser.add_argument("--client-cert", help="Client certificate file")
    # parser.add_argument("--client-key", help="Client private key file")

    args = parser.parse_args()
    cfg = load_client_config(args.config)

    try:
        response = query_server(
            host=cfg["host"],
            port=cfg["port"],
            query=args.query,
            use_ssl=cfg['ssl_on'],
            ca_cert=cfg['cafile'],
            client_cert=cfg['certfile'],
            client_key=cfg['keyfile']
        )
        print(f"{response}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
