#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import argparse
import os
import subprocess
import sys


def _which(cmd):
    for path in os.environ.get("PATH", os.defpath).split(os.pathsep):
        p = os.path.join(path, cmd)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def _b2u(s):
    if s is None:
        return ""
    if hasattr(s, "decode"):
        return s.decode("utf-8", "replace")
    return s


def _run(argv):
    try:
        p = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = p.communicate()
    except OSError as e:
        return 127, "", "{0}".format(e)
    return p.returncode, _b2u(out), _b2u(err)


def _archive_tar_gz(out_path, parent, base):
    return _run(["tar", "-czf", out_path, "-C", parent, base])


def _archive_tar_bz2(out_path, parent, base):
    return _run(["tar", "-cjf", out_path, "-C", parent, base])


def _archive_zip(out_path, parent, base):
    try:
        p = subprocess.Popen(
            ["zip", "-r", "-q", out_path, base],
            cwd=parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = p.communicate()
    except OSError as e:
        return 127, "", "{0}".format(e)
    return p.returncode, _b2u(out), _b2u(err)


def _archive_7z(out_path, parent, base):
    exe = _which("7z")
    if not exe:
        exe = _which("7za")
    if not exe:
        return 127, "", "7z/7za not found in PATH"
    try:
        p = subprocess.Popen(
            [exe, "a", "-t7z", out_path, base],
            cwd=parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = p.communicate()
    except OSError as e:
        return 127, "", "{0}".format(e)
    return p.returncode, _b2u(out), _b2u(err)


FORMATS = {
    "tar.gz": ("tar.gz", _archive_tar_gz),
    "tgz": ("tar.gz", _archive_tar_gz),
    "tar.bz2": ("tar.bz2", _archive_tar_bz2),
    "tbz2": ("tar.bz2", _archive_tar_bz2),
    "tb2": ("tar.bz2", _archive_tar_bz2),
    "zip": ("zip", None),
    "7z": ("7z", None),
}


def main():
    parser = argparse.ArgumentParser(
        description="Create a compressed archive of a directory using system tools.",
    )
    parser.add_argument(
        "directory",
        help="Path to the directory to back up",
    )
    parser.add_argument(
        "-f",
        "--format",
        dest="fmt",
        required=True,
        help="Archive format: tar.gz, tar.bz2, zip, 7z",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        default=None,
        help="Output archive path (default: <dirname>.<ext> next to the directory)",
    )
    args = parser.parse_args()

    fmt_key = args.fmt.strip().lower()
    if fmt_key not in FORMATS:
        sys.stderr.write(
            "Unknown format: {0}. Use: tar.gz, tar.bz2, zip, 7z\n".format(args.fmt)
        )
        return 2

    suffix, handler = FORMATS[fmt_key]

    target = os.path.abspath(os.path.normpath(args.directory))
    if not os.path.isdir(target):
        sys.stderr.write("Not a directory or missing: {0}\n".format(target))
        return 1

    base = os.path.basename(target)
    parent = os.path.dirname(target)
    if not base:
        sys.stderr.write("Invalid directory path: {0}\n".format(target))
        return 1

    if args.output:
        out_path = os.path.abspath(os.path.normpath(args.output))
    else:
        out_path = os.path.join(parent, "{0}.{1}".format(base, suffix))

    if os.path.exists(out_path):
        sys.stderr.write("Output already exists: {0}\n".format(out_path))
        return 1

    if suffix in ("tar.gz", "tar.bz2"):
        if not _which("tar"):
            sys.stderr.write("tar not found in PATH\n")
            return 127
        code, out, err = handler(out_path, parent, base)
    elif suffix == "zip":
        if not _which("zip"):
            sys.stderr.write("zip not found in PATH\n")
            return 127
        code, out, err = _archive_zip(out_path, parent, base)
    elif suffix == "7z":
        code, out, err = _archive_7z(out_path, parent, base)
    else:
        sys.stderr.write("Internal error: unsupported suffix\n")
        return 3

    if out:
        sys.stdout.write(out)
    if err:
        sys.stderr.write(err)
    if code != 0:
        sys.stderr.write("Command failed with exit code {0}\n".format(code))
        if os.path.isfile(out_path):
            try:
                os.remove(out_path)
            except OSError:
                pass
        return code if code != 0 else 1

    sys.stdout.write("{0}\n".format(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
