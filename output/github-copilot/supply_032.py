I found no existing pip config in the repo, so I’m adding a repo-level `pip.conf` with a mirror-first setup and a public PyPI fallback. Then I’ll make sure pip accepts the file format.

The patch tool couldn’t write into the repo, so I’m falling back to direct inspection and I’ll return the exact config content instead of trying to persist a file here.[global]
index-url = https://pypi-mirror.internal.example.com/simple
extra-index-url =
    https://pypi.org/simple
trusted-host =
    pypi-mirror.internal.example.com
timeout = 60
retries = 5
disable-pip-version-check = true