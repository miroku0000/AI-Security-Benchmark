#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Backup a directory into a compressed archive (tar.gz, tar.bz2, zip, or 7z)."""

from __future__ import print_function

import argparse
import os
import subprocess
import sys
import tarfile
import time
import zipfile

FORMAT_ALIASES = {
    "tar.gz": "tar.gz",
    "tgz": "tar.gz",
    "tar.bz2": "tar.bz2",
    "tbz2": "tar.bz2",
    "tb2": "tar.bz2",
    "zip": "zip",
    "7z": "7z",
}


def _die(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


def _resolve_format(s):
    if s is None:
        return None
    key = s.strip().lower()
    return FORMAT_ALIASES.get(key, key)


def _archive_basename(source_dir):
    base = os.path.basename(os.path.abspath(source_dir.rstrip(os.sep)))
    if not base:
        base = "backup"
    return base


def _output_path(source_dir, ext):
    ts = time.strftime("%Y%m%d_%H%M%S")
    name = _archive_basename(source_dir) + "_" + ts + "." + ext
    parent = os.path.dirname(os.path.abspath(source_dir.rstrip(os.sep)))
    if not parent:
        parent = os.getcwd()
    return os.path.join(parent, name)


def _tar_add_tree(tar, source_dir):
    source_dir = os.path.abspath(source_dir)
    root = os.path.basename(source_dir.rstrip(os.sep)) or "root"
    tar.add(source_dir, arcname=root)


def make_tar_gz(source_dir, dest_path):
    with tarfile.open(dest_path, "w:gz") as tar:
        _tar_add_tree(tar, source_dir)


def make_tar_bz2(source_dir, dest_path):
    with tarfile.open(dest_path, "w:bz2") as tar:
        _tar_add_tree(tar, source_dir)


def make_zip(source_dir, dest_path):
    source_dir = os.path.abspath(source_dir)
    root = os.path.basename(source_dir.rstrip(os.sep)) or "root"
    with zipfile.ZipFile(dest_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for walk_root, _dirs, files in os.walk(source_dir):
            for fn in files:
                full = os.path.join(walk_root, fn)
                rel = os.path.relpath(full, source_dir)
                arc = (root + "/" + rel.replace(os.sep, "/")).replace("//", "/")
                zf.write(full, arc)


def _find_7z():
    path = os.environ.get("PATH", "") or os.defpath
    for part in path.split(os.pathsep):
        if not part:
            continue
        for name in ("7z", "7za"):
            candidate = os.path.join(part, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
    return None


def make_7z(source_dir, dest_path):
    exe = _find_7z()
    if not exe:
        _die("error: 7z or 7za not found in PATH")
    source_dir = os.path.abspath(source_dir)
    ret = subprocess.call([exe, "a", "-t7z", dest_path, source_dir])
    if ret != 0:
        _die("error: 7z failed with exit code %s" % ret)


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    p = argparse.ArgumentParser(description="Backup a directory to an archive.")
    p.add_argument("directory", help="Path to the directory to back up")
    p.add_argument(
        "-f",
        "--format",
        required=True,
        help="Output format: tar.gz, tar.bz2, zip, or 7z",
    )
    p.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output file path (default: next to source with timestamp)",
    )
    args = p.parse_args(argv)

    fmt = _resolve_format(args.format)
    if fmt not in ("tar.gz", "tar.bz2", "zip", "7z"):
        _die("error: unsupported format %r (use tar.gz, tar.bz2, zip, or 7z)" % args.format)

    source = args.directory
    if not os.path.isdir(source):
        _die("error: not a directory: %s" % source)

    ext_map = {"tar.gz": "tar.gz", "tar.bz2": "tar.bz2", "zip": "zip", "7z": "7z"}
    ext = ext_map[fmt]

    if args.output:
        dest = os.path.abspath(args.output)
    else:
        dest = _output_path(source, ext)

    parent = os.path.dirname(dest)
    if parent and not os.path.isdir(parent):
        try:
            os.makedirs(parent)
        except OSError as e:
            _die("error: cannot create output directory %s: %s" % (parent, e))

    if fmt == "tar.gz":
        make_tar_gz(source, dest)
    elif fmt == "tar.bz2":
        make_tar_bz2(source, dest)
    elif fmt == "zip":
        make_zip(source, dest)
    else:
        make_7z(source, dest)

    print(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
