# StriSeC — String Search Core

**StriSeC** is a high-performance, secure, multithreaded string search server written in Python.  
It implements a secure, multithreaded string-search TCP server with optional SSL/TLS encryption and configurable payload limits, Automated robust testing for benchmarking algorithms, daemon processes for MacOS and LINUX, client-server communication for use in automated data validation, scanning, or secure query environments.

## 🚀 Features

- 🔒 **SSL/TLS support** with client certificate validation
- ⚡ **Multithreaded TCP server** for high-concurrency query handling
- 🧠 **Pluggable search algorithms** (`dynamic`, `regex`, `mmap`, `linecache`, `grep`, etc.)
- 🧪 **Full test suite** with `pytest`, including malformed queries, stress test, disconnects, and cert validation
- 📂 **Configurable via INI file** — runtime paths, SSL settings, logging, and behavior
- 🧰 Designed for **Linux/ MacOS environments**, works in containers and headless systems


## Prerequisites

- Python 3.8+

- A Python virtual environment (recommended)

- OpenSSL (for generating certificates)

## Steps
1. Create and activate a virtual environment:
    ``` bash
    python3 -m venv venv
    source venv/bin/activate
    ```
2. Install dependencies:
    ``` bash
    pip install -r requirements.txt
    ```
   
3. SSL configuration:
    ###### Create CA key + self-signed cert
    ``` bash
   openssl genrsa -out certs/ca.key 4096
   ```

   ``` bash
   openssl req -x509 -new -nodes   -key certs/ca.key   -sha256 -days 3650   -out certs/ca.crt   -subj "/C=US/ST=State/L=City/O=MyOrg/OU=IT/CN=LocalTestCA"
   ```
   
   ###### Sign the client CSR with your CA to get client.crt valid for 1 year
   ``` bash
   openssl genrsa -out certs/server.key 2048
   ```
   ``` bash
   openssl req -new -key certs/server.key   -out certs/server.csr   -subj "/C=US/ST=State/L=City/O=MyOrg/OU=IT/CN=localhost"
   ```
   ``` bash
   openssl x509 -req   -in certs/server.csr   -CA certs/ca.crt   -CAkey certs/ca.key   -CAcreateserial   -out certs/server.crt   -days 365   -sha256
   ```
   
   ###### Create client key + self-signed cert
   ``` bash
   openssl genrsa -out certs/client.key 2048
   ```
   ###### Create a Certificate Signing Request (CSR) for the client
   ``` bash
   openssl req -new   -key certs/client.key   -out certs/client.csr   -subj "/C=US/ST=State/L=City/O=MyOrg/OU=Clients/CN=my-client"
   ```
   ###### Sign the client CSR with your CA to get client.crt
   ``` bash
   openssl x509 -req   -in certs/client.csr   -CA certs/ca.crt   -CAkey certs/ca.key   -CAcreateserial   -out certs/client.crt   -days 365   -sha256
   ```
   ###### Testing the mutual-TLS handshake
   ``` bash
   openssl s_client   -connect localhost:12345  -cert certs/client.crt   -key certs/client.key   -CAfile certs/ca.crt
   ```
   ``` bash
   openssl s_client -connect 127.0.0.1:12345
   ```
   
4. Configuration
Edit config/server_config.ini or config/client_config.ini parameters: 
#### Note: You can enable TLS by setting ssl_on = True

### Running the Server
 ```python3 -m src.server  -c config/server_config.ini ```

#### Testing Connectivity
Plain TCP (SSL_ON=False):
    ```
        echo "4;0;1;28;0;7;5;0;" | nc 127.0.0.1 12345
    ```
    or with client

```    
    python3 -m client  -c config/client_config.ini  "4;0;1;28;0;7;5;0;"
```


SSL/TLS (SSL_ON = True):
    ```
        echo "4;0;1;28;0;7;5;0;" | openssl s_client -quiet -connect 127.0.0.1:12345 -cert certs/client.crt   -key certs/client.key -CAfile certs/ca.crt 
    ```

You should receive either STRING EXISTS or STRING NOT FOUND.


## Steps (To run Server as a Linux Daemon)

1. Create a Systemd Service File
    ``` bash
   sudo cp daemon/search-server.service /etc/systemd/system/search-server.service
   ```
2. Reload systemd
    ``` bash
    sudo systemctl daemon-reload
   ```
3. Start/Enable Service
    ``` bash
    sudo systemctl start search-server
    sudo systemctl enable search-server 
    ```
4. Check Status / view logs
    ```
   sudo systemctl status search-server
   journalctl -u search-server -f
   ```

