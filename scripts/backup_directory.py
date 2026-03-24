#!/usr/bin/env python3
"""
Create compressed backups of directories using system commands.

Supported formats:
  - tar.gz
  - tar.bz2
  - zip
  - 7z
"""

from __future__ import print_function

import argparse
import datetime
import os
import subprocess
import sys


FORMAT_CONFIG = {
    "tar.gz": {"ext": ".tar.gz", "command": "tar"},
    "tar.bz2": {"ext": ".tar.bz2", "command": "tar"},
    "zip": {"ext": ".zip", "command": "zip"},
    "7z": {"ext": ".7z", "command": "7z"},
}


def error_exit(message, code=1):
    print("Error: {0}".format(message), file=sys.stderr)
    sys.exit(code)


def build_default_output_path(source_dir, fmt):
    source_name = os.path.basename(os.path.normpath(source_dir))
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = FORMAT_CONFIG[fmt]["ext"]
    filename = "{0}_{1}{2}".format(source_name, timestamp, ext)
    return os.path.abspath(filename)


def ensure_parent_exists(path):
    parent = os.path.dirname(path)
    if not parent:
        return
    if not os.path.isdir(parent):
        error_exit("Output directory does not exist: {0}".format(parent))


def command_exists(command_name):
    path_value = os.environ.get("PATH", "")
    for directory in path_value.split(os.pathsep):
        candidate = os.path.join(directory, command_name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return True
    return False


def ensure_command_available(command_name):
    if not command_exists(command_name):
        error_exit(
            "Required command '{0}' was not found in PATH.".format(command_name)
        )


def run_backup(source_dir, fmt, output_path):
    parent_dir = os.path.dirname(source_dir)
    source_name = os.path.basename(source_dir)

    if fmt == "tar.gz":
        cmd = ["tar", "-czf", output_path, source_name]
    elif fmt == "tar.bz2":
        cmd = ["tar", "-cjf", output_path, source_name]
    elif fmt == "zip":
        cmd = ["zip", "-r", output_path, source_name]
    elif fmt == "7z":
        cmd = ["7z", "a", "-t7z", output_path, source_name]
    else:
        error_exit("Unsupported format: {0}".format(fmt))

    try:
        subprocess.check_call(cmd, cwd=parent_dir)
    except subprocess.CalledProcessError as exc:
        error_exit(
            "Backup command failed with exit code {0}.".format(exc.returncode),
            code=exc.returncode,
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create compressed archives from directories using system tools."
    )
    parser.add_argument(
        "directory",
        help="Path to directory to back up.",
    )
    parser.add_argument(
        "format",
        choices=sorted(FORMAT_CONFIG.keys()),
        help="Archive format: tar.gz, tar.bz2, zip, or 7z.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output archive path. If omitted, a timestamped file is created in the current directory.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    source_dir = os.path.abspath(args.directory)
    if not os.path.isdir(source_dir):
        error_exit("Directory does not exist: {0}".format(source_dir))

    output_path = (
        os.path.abspath(args.output)
        if args.output
        else build_default_output_path(source_dir, args.format)
    )
    ensure_parent_exists(output_path)

    required_command = FORMAT_CONFIG[args.format]["command"]
    ensure_command_available(required_command)

    run_backup(source_dir, args.format, output_path)
    print("Backup created: {0}".format(output_path))


if __name__ == "__main__":
    main()
