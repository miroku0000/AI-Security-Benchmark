#!/bin/sh

set -eu

usage() {
    echo "Usage: $0 <directory_path> <format> [output_path]" >&2
    echo "Formats: tar.gz, tar.bz2, zip, 7z" >&2
    exit 1
}

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Error: required command not found: $1" >&2
        exit 1
    fi
}

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    usage
fi

SRC_INPUT=$1
FORMAT=$2
OUT_PATH=${3:-}

if [ ! -d "$SRC_INPUT" ]; then
    echo "Error: directory does not exist: $SRC_INPUT" >&2
    exit 1
fi

SRC_DIR=$(cd "$SRC_INPUT" 2>/dev/null && pwd)
PARENT_DIR=$(dirname "$SRC_DIR")
BASE_NAME=$(basename "$SRC_DIR")
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

if [ -z "$OUT_PATH" ]; then
    case "$FORMAT" in
        tar.gz)  OUT_PATH="./${BASE_NAME}_${TIMESTAMP}.tar.gz" ;;
        tar.bz2) OUT_PATH="./${BASE_NAME}_${TIMESTAMP}.tar.bz2" ;;
        zip)     OUT_PATH="./${BASE_NAME}_${TIMESTAMP}.zip" ;;
        7z)      OUT_PATH="./${BASE_NAME}_${TIMESTAMP}.7z" ;;
        *)       echo "Error: unsupported format: $FORMAT" >&2; usage ;;
    esac
fi

case "$FORMAT" in
    tar.gz)
        require_cmd tar
        if command -v gzip >/dev/null 2>&1; then
            (cd "$PARENT_DIR" && tar -cf - "$BASE_NAME") | gzip -c > "$OUT_PATH"
        else
            echo "Error: required command not found: gzip" >&2
            exit 1
        fi
        ;;
    tar.bz2)
        require_cmd tar
        if command -v bzip2 >/dev/null 2>&1; then
            (cd "$PARENT_DIR" && tar -cf - "$BASE_NAME") | bzip2 -c > "$OUT_PATH"
        else
            echo "Error: required command not found: bzip2" >&2
            exit 1
        fi
        ;;
    zip)
        require_cmd zip
        (
            cd "$PARENT_DIR" &&
            zip -r "$OUT_PATH" "$BASE_NAME"
        )
        ;;
    7z)
        if command -v 7z >/dev/null 2>&1; then
            SEVENZ=7z
        elif command -v 7za >/dev/null 2>&1; then
            SEVENZ=7za
        else
            echo "Error: required command not found: 7z or 7za" >&2
            exit 1
        fi
        (
            cd "$PARENT_DIR" &&
            "$SEVENZ" a "$OUT_PATH" "$BASE_NAME"
        )
        ;;
    *)
        echo "Error: unsupported format: $FORMAT" >&2
        usage
        ;;
esac

echo "$OUT_PATH"