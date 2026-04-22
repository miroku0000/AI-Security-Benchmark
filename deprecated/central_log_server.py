#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse, urljoin


class LogConfig:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()

    def append_line(self, line: str) -> None:
        with self._lock:
            parent = os.path.dirname(os.path.abspath(self.path))
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line)
                if not line.endswith("\n"):
                    fh.write("\n")


def make_handler(log_cfg: LogConfig):
    class CentralLogHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:
            pass

        def _send(self, code: int, body: bytes, content_type: str = "text/plain; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/health"):
                self._send(200, b"ok\n")
                return
            self._send(404, b"not found\n")

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path not in ("/log", "/logs"):
                self._send(404, b"not found\n")
                return

            length_hdr = self.headers.get("Content-Length")
            try:
                length = int(length_hdr) if length_hdr else 0
            except ValueError:
                self._send(400, b"bad Content-Length\n")
                return

            raw = self.rfile.read(length) if length else b""
            ct = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()

            payload: dict = {}
            if ct == "application/json":
                try:
                    payload = json.loads(raw.decode("utf-8") or "{}")
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._send(400, b"invalid JSON\n")
                    return
            elif ct in ("application/x-www-form-urlencoded", "text/plain"):
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    self._send(400, b"invalid encoding\n")
                    return
                if ct == "application/x-www-form-urlencoded":
                    qs = parse_qs(text, keep_blank_values=True)
                    payload = {k: (v[0] if len(v) == 1 else v) for k, v in qs.items()}
                else:
                    payload = {"message": text}
            else:
                self._send(415, b"unsupported Content-Type\n")
                return

            if not isinstance(payload, dict):
                self._send(400, b"JSON body must be an object\n")
                return

            ts = payload.get("timestamp")
            if ts is None:
                ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            level = str(payload.get("level", "INFO")).upper()
            service = str(payload.get("service", payload.get("source", "unknown")))
            msg = payload.get("message")
            if msg is None:
                msg = payload.get("msg", "")
            trace = payload.get("trace_id", payload.get("request_id", ""))
            extra = payload.get("extra")
            if extra is not None and not isinstance(extra, (dict, list, str, int, float, bool)):
                extra = str(extra)

            line = "{ts} [{level}] service={service!s} trace={trace!s} message={message!s}".format(
                ts=ts,
                level=level,
                service=service,
                trace=trace if trace is not None else "",
                message=msg if msg is not None else "",
            )
            if extra is not None:
                try:
                    extra_s = json.dumps(extra, separators=(",", ":"), ensure_ascii=False)
                except TypeError:
                    extra_s = str(extra)
                line = "{base} extra={extra}".format(base=line, extra=extra_s)

            log_cfg.append_line(line)
            self._send(204, b"")

    return CentralLogHandler


class CentralHTTPLogHandler(logging.Handler):
    def __init__(
        self,
        base_url: str,
        service: str = "",
        timeout: float = 5.0,
        path: str = "/log",
    ) -> None:
        super().__init__()
        self.endpoint = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
        self.service = service
        self.timeout = timeout

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
                "level": record.levelname,
                "service": self.service or record.name,
                "message": self.format(record),
            }
            if getattr(record, "trace_id", None):
                payload["trace_id"] = record.trace_id
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint,
                data=data,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=self.timeout)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError):
            self.handleError(record)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default=os.environ.get("LOG_HTTP_HOST", "0.0.0.0"))
    p.add_argument("--port", type=int, default=int(os.environ.get("LOG_HTTP_PORT", "8080")))
    p.add_argument("--file", dest="logfile", default=os.environ.get("LOG_HTTP_FILE", "./central.log"))
    args = p.parse_args(argv)

    cfg = LogConfig(args.logfile)
    handler_cls = make_handler(cfg)
    server = HTTPServer((args.host, args.port), handler_cls)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
