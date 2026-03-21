from __future__ import print_function
import os
import sys
import subprocess

def which_exe(names):
    path = os.environ.get("PATH", os.defpath)
    for d in path.split(os.pathsep):
        if not d:
            continue
        for name in names:
            p = os.path.join(d, name)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
    return None


FORMATS = {
    "tar.gz": ("tar", [".tar.gz"]),
    "tgz": ("tar", [".tar.gz"]),
    "tar.bz2": ("tar", [".tar.bz2"]),
    "tbz2": ("tar", [".tar.bz2"]),
    "tb2": ("tar", [".tar.bz2"]),
    "zip": ("zip", [".zip"]),
    "7z": ("7z", [".7z"]),
}


def usage():
    sys.stderr.write(
        "usage: %s <directory> <format>\n"
        "formats: tar.gz, tar.bz2, zip, 7z\n" % (sys.argv[0],)
    )


def main():
    if len(sys.argv) != 3:
        usage()
        sys.exit(2)

    dirpath = os.path.abspath(sys.argv[1])
    fmt = sys.argv[2].lower().strip()

    if fmt not in FORMATS:
        sys.stderr.write("error: unknown format %r\n" % (sys.argv[2],))
        usage()
        sys.exit(2)

    if not os.path.isdir(dirpath):
        sys.stderr.write("error: not a directory: %s\n" % dirpath)
        sys.exit(1)

    base = os.path.basename(dirpath.rstrip(os.sep)) or "backup"
    parent = os.path.dirname(dirpath)
    kind, suffixes = FORMATS[fmt]
    suffix = suffixes[0]
    archive_path = os.path.join(parent, base + suffix)

    if os.path.lexists(archive_path):
        sys.stderr.write("error: output already exists: %s\n" % archive_path)
        sys.exit(1)

    if kind == "tar":
        if suffix == ".tar.gz":
            cmd = ["tar", "-czf", archive_path, "-C", parent, base]
        else:
            cmd = ["tar", "-cjf", archive_path, "-C", parent, base]
        cwd = None
    elif kind == "zip":
        cmd = ["zip", "-r", archive_path, base]
        cwd = parent
    elif kind == "7z":
        seven = which_exe(("7z", "7za"))
        if not seven:
            sys.stderr.write("error: 7z or 7za not found in PATH\n")
            sys.exit(1)
        cmd = [seven, "a", archive_path, dirpath]
        cwd = None
    else:
        sys.stderr.write("error: internal format error\n")
        sys.exit(1)

    try:
        subprocess.check_call(cmd, cwd=cwd)
    except OSError as e:
        sys.stderr.write("error: failed to run %s: %s\n" % (cmd[0], e))
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        sys.stderr.write("error: command failed with exit %s\n" % e.returncode)
        if os.path.lexists(archive_path):
            try:
                os.remove(archive_path)
            except OSError:
                pass
        sys.exit(e.returncode)

    print(archive_path)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)