import ssl
from typing import Optional


def create_ssl_context(certfile: str, keyfile: str, verify_client: bool, cafile) -> Optional[ssl.SSLContext]:
    """
    Returns an SSLContext configured with server cert/key.
    If certfile or keyfile is missing, returns None.
    """
    if not certfile or not keyfile:
        return None

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH, cafile=cafile)
    context.load_cert_chain(certfile, keyfile)
    context.load_verify_locations(certfile)
    if verify_client:
        context.verify_mode = ssl.CERT_REQUIRED
    else:
        context.verify_mode = ssl.CERT_NONE
    return context
