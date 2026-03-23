#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import argparse
import os
import subprocess
import sys


def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


def run(cmd, cwd=None):
    try:
        p = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = p.communicate()
    except OSError as e:
        fail("Failed to run %s: %s" % (" ".join(cmd), e))

    if p.returncode != 0:
        err = err.decode("utf-8", "replace") if err else ""
        fail("Command failed (%s): %s" % (p.returncode, err.strip() or "(no stderr)"))


def main():
    ap = argparse.ArgumentParser(description="Create a compressed archive of a directory.")
    ap.add_argument("directory", help="Path to the directory to archive")
    ap.add_argument(
        "-f",
        "--format",
        required=True,
        choices=("tar.gz", "tar.bz2", "zip", "7z"),
        help="Archive format",
    )
    ap.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output archive path (default: <dirname>.<ext> in current directory)",
    )
    args = ap.parse_args()

    src = os.path.abspath(args.directory)
    if not os.path.isdir(src):
        fail("Not a directory or missing: %s" % src)

    base = os.path.basename(src.rstrip(os.sep))
    parent = os.path.dirname(src)

    ext = {"tar.gz": ".tar.gz", "tar.bz2": ".tar.bz2", "zip": ".zip", "7z": ".7z"}[args.format]

    if args.output:
        out = os.path.abspath(args.output)
    else:
        out = os.path.join(os.getcwd(), base + ext)

    out_dir = os.path.dirname(out)
    if out_dir and not os.path.isdir(out_dir):
        fail("Output directory does not exist: %s" % out_dir)

    fmt = args.format
    if fmt == "tar.gz":
        run(["tar", "-czf", out, "-C", parent, base])
    elif fmt == "tar.bz2":
        run(["tar", "-cjf", out, "-C", parent, base])
    elif fmt == "zip":
        run(["zip", "-r", "-q", out, base], cwd=parent)
    elif fmt == "7z":
        run(["7z", "a", "-t7z", "-y", out, base], cwd=parent)
    else:
        fail("Unsupported format: %s" % fmt)

    print(out)


if __name__ == "__main__":
    main()
