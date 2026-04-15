[global]
index-url = https://pypi.example.internal/simple
trusted-host =
    pypi.example.internal
cert = /etc/ssl/certs/pypi-example-internal-ca.pem
require-virtualenv = true
disable-pip-version-check = true
timeout = 15
retries = 3
no-input = true

[install]
trusted-host =
    pypi.example.internal