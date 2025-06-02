import configparser
from pathlib import Path
from typing import Any, Dict
from .exceptions import ConfigError, ClientConfigError


def load_config(path: str) -> Dict[str, Any]:
    """
    Reads and validates server_config.ini.
    Returns a nested dict of sections and values.
    Raises ConfigError on missing or invalid fields.
    """
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    parser = configparser.ConfigParser()
    parser.read(path)

    try:
        server = parser["server"]
        network = parser["network"]
        ssl = parser["ssl"]
        logging_cfg = parser["logging"]
    except KeyError as e:
        raise ConfigError(f"Missing section in config: {e}")

    # Basic validation
    cfg = {
        "LINUXPATH": server.get("LINUXPATH"),
        "REREAD_ON_QUERY": server.getboolean("REREAD_ON_QUERY", fallback=False),
        "HOST": network.get("HOST", "0.0.0.0"),
        "PORT": network.getint("PORT", fallback=9000),
        "MAX_PAYLOAD_SIZE": network.getint("MAX_PAYLOAD_SIZE", fallback=1024),
        "SSL_ON": ssl.getboolean("SSL_ON", fallback=False),
        "SSL_MODE": ssl.get("SSL_MODE", "cert"),
        "CERTFILE": ssl.get("CERTFILE", ""),
        "CAFILE": ssl.get("CAFILE", ""),
        "KEYFILE": ssl.get("KEYFILE", ""),
        "SSL_VERIFY_CLIENT": ssl.getboolean("SSL_VERIFY_CLIENT", fallback=False),
        "LOG_LEVEL": logging_cfg.get("LOG_LEVEL", "INFO"),
        "LOG_FILE": logging_cfg.get("LOG_FILE", "server.log"),
    }

    # More validation can be added here (e.g. file paths exist)
    return cfg


def load_client_config(path: str) -> Dict[str, Any]:
    """
    Load and validate client configuration from an INI file.

    Expects a file at `path` with at least:

    [client]
      host               = <server hostname or IP>
      port               = <server TCP port>
      ssl_on             = true|false
      certfile           = <(optional) path to client TLS cert>
      keyfile            = <(optional) path to client TLS key>
      cafile             = <(optional) path to CA bundle for server validation>
      max_payload_size   = <(optional) max bytes to recv/send; defaults to 1024>

    Optionally you can include a [loadtest] section for driving a harness:
    [loadtest]
      concurrency         = <number of parallel clients; default 1>
      requests_per_client = <queries per client; default 1>
      request_interval_ms = <delay between queries in ms; default 0>
      sample_query        = <string to send repeatedly; default “”>

    Raises:
        ServerError on missing file, missing sections, or invalid values.

    Returns:
        cfg: Dict[str, Any] mapping each setting to its Python-typed value.
    """
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    parser = configparser.ConfigParser()

    # Attempt to read the file; parser.read() returns list of successfully-read names
    read_files = parser.read(path)
    if not read_files:
        raise ClientConfigError(f"Could not read config file: {path}")

    # Ensure the mandatory [client] section is present
    if "client" not in parser:
        raise ClientConfigError("Missing [client] section in config file")

    section = parser["client"]
    cfg: Dict[str, Any] = {}

    # Parse and validate each client setting
    try:
        # Required fields
        cfg["host"] = section.get("host")
        if not cfg["host"]:
            raise ValueError("host must be set")

        cfg["port"] = section.getint("port")
        # Optional flags
        cfg["ssl_on"] = section.getboolean("ssl_on", fallback=False)
        # Optional file paths (may be None or empty if no TLS)
        cfg["certfile"] = section.get("certfile", fallback=None) or None
        cfg["keyfile"] = section.get("keyfile", fallback=None)  or None
        cfg["cafile"] = section.get("cafile", fallback=None)   or None
        cfg["log_level"] = section.get("log_level", "INFO"),
        cfg["log_file"] = section.get("log_file", "server.log"),
        # Payload size for recv()
        cfg["max_payload_size"] = section.getint("max_payload_size", fallback=1024)

    except ValueError as e:
        # Catches missing/empty host, non-integer port, etc.
        raise ClientConfigError(f"Invalid value in [client] section: {e}")

    # If TLS is enabled, ensure we have at least a CA file or skip verification explicitly
    if cfg["ssl_on"] and not (cfg["cafile"] or (cfg["certfile"] and cfg["keyfile"])):
        # You can choose to require certfile+keyfile, or allow cafile-only server validation.
        # Here we just warn if no trust anchor or client cert is set.
        raise ClientConfigError(
            "ssl_on=True but cafile or certfile+keyfile not configured in [client] section"
        )

    # Load optional loadtest parameters
    if "loadtest" in parser:
        lt = parser["loadtest"]
        try:
            cfg["concurrency"] = lt.getint("concurrency", fallback=1)
            cfg["requests_per_client"] = lt.getint("requests_per_client", fallback=1)
            cfg["request_interval_ms"] = lt.getint("request_interval_ms", fallback=0)
        except ValueError as e:
            raise ClientConfigError(f"Invalid value in [loadtest] section: {e}")
        # Any string (even empty) is fine for the sample query
        # cfg["sample_query"] = lt.get("sample_query", fallback="")

    return cfg
