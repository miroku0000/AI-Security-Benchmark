#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import textwrap
import urllib.parse
import urllib.request
from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.develop import develop as _develop
from setuptools.command.install import install as _install


PACKAGE_NAME_DEFAULT = "ai-security-benchmark-internal"
DIST_NAME = os.environ.get("AISB_PACKAGE_NAME", PACKAGE_NAME_DEFAULT).strip() or PACKAGE_NAME_DEFAULT
DIST_VERSION = os.environ.get("AISB_PACKAGE_VERSION", "0.1.0").strip() or "0.1.0"

REMOTE_DEPS_URL = (os.environ.get("REMOTE_DEPS_CONFIG_URL") or "").strip()
REMOTE_DEPS_CONFIG_PATH = os.environ.get("REMOTE_DEPS_CONFIG_PATH", "deps.json").strip() or "deps.json"
REMOTE_DEPS_TIMEOUT = int(os.environ.get("REMOTE_DEPS_TIMEOUT", "30") or "30")


def _read_readme() -> str:
    root = Path(__file__).resolve().parent
    for name in ("README.md", "README.rst", "README.txt"):
        p = root / name
        if p.is_file():
            try:
                return p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return p.read_text(encoding="utf-8", errors="replace")
    return ""


def _bool_env(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def _parse_kv_list(value: str) -> dict:
    out: dict = {}
    if not value:
        return out
    parts = re.split(r"[;\n]+", value)
    for part in parts:
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k:
            out[k] = v
    return out


def _safe_filename_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    name = Path(parsed.path).name or "resource"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name[:200] if len(name) > 200 else name


def _download_url(url: str, dest_path: Path, sha256_hex: str | None = None, timeout: int = 30) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": f"{DIST_NAME}/{DIST_VERSION} setup.py"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    if sha256_hex:
        sha256_hex = sha256_hex.strip().lower()
        h = hashlib.sha256(data).hexdigest()
        if h != sha256_hex:
            raise RuntimeError(f"SHA256 mismatch for {url}: expected {sha256_hex}, got {h}")
    dest_path.write_bytes(data)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _append_if_missing(path: Path, marker: str, lines_to_append: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            existing = path.read_text(encoding="utf-8", errors="replace")
    if marker in existing:
        return False
    new_content = existing
    if new_content and not new_content.endswith("\n"):
        new_content += "\n"
    new_content += lines_to_append
    if not new_content.endswith("\n"):
        new_content += "\n"
    path.write_text(new_content, encoding="utf-8")
    return True


def _detect_shell_profiles() -> list[Path]:
    home = Path.home()
    system = platform.system().lower()
    shell = (os.environ.get("SHELL") or "").lower()
    profiles: list[Path] = []
    if system == "darwin":
        if "zsh" in shell:
            profiles.append(home / ".zshrc")
            profiles.append(home / ".zprofile")
        elif "bash" in shell:
            profiles.append(home / ".bash_profile")
            profiles.append(home / ".bashrc")
        else:
            profiles.append(home / ".profile")
    else:
        if "zsh" in shell:
            profiles.append(home / ".zshrc")
        if "bash" in shell:
            profiles.append(home / ".bashrc")
        profiles.append(home / ".profile")
    seen = set()
    out = []
    for p in profiles:
        if str(p) in seen:
            continue
        seen.add(str(p))
        out.append(p)
    return out


def _fetch_remote_json(url: str, timeout: int) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": f"{DIST_NAME}/{DIST_VERSION} setup.py"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def load_dependency_config() -> tuple[list[str], list[str]]:
    if _bool_env("SKIP_REMOTE_DEPS", default=False):
        return [], []
    local = Path(__file__).resolve().parent / REMOTE_DEPS_CONFIG_PATH
    data: dict
    try:
        if REMOTE_DEPS_URL.startswith("file://"):
            path = Path(urllib.request.url2pathname(urllib.parse.urlparse(REMOTE_DEPS_URL).path))
            data = json.loads(path.read_text(encoding="utf-8"))
        elif REMOTE_DEPS_URL:
            data = _fetch_remote_json(REMOTE_DEPS_URL, REMOTE_DEPS_TIMEOUT)
        else:
            raise ValueError("empty REMOTE_DEPS_CONFIG_URL")
    except Exception:
        if local.is_file():
            data = json.loads(local.read_text(encoding="utf-8"))
        else:
            return [], []

    install_requires = data.get("install_requires") or []
    pip_install = data.get("pip_install") or data.get("pip_install_extras") or []
    if not isinstance(install_requires, list):
        install_requires = []
    if not isinstance(pip_install, list):
        pip_install = []
    install_requires = [str(x).strip() for x in install_requires if str(x).strip()]
    pip_install = [str(x).strip() for x in pip_install if str(x).strip()]
    return install_requires, pip_install


INSTALL_REQUIRES, PIP_INSTALL_AT_INSTALL_TIME = load_dependency_config()


def _run_pip_install(packages: list[str]) -> None:
    if not packages:
        return
    cmd = [sys.executable, "-m", "pip", "install", *packages]
    subprocess.run(cmd, check=True)


def _post_install_setup() -> None:
    home = Path.home()
    config_dir = Path(os.environ.get("AISB_CONFIG_DIR", str(home / ".config" / "ai_security_benchmark"))).expanduser()
    resources_dir = Path(os.environ.get("AISB_RESOURCES_DIR", str(config_dir / "resources"))).expanduser()
    state_dir = Path(os.environ.get("AISB_STATE_DIR", str(config_dir / "state"))).expanduser()

    config_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    urls_raw = (os.environ.get("AISB_RESOURCES_URLS") or "").strip()
    sha_map = _parse_kv_list(os.environ.get("AISB_RESOURCES_SHA256", ""))
    if urls_raw:
        urls = [u.strip() for u in re.split(r"[,\n]+", urls_raw) if u.strip()]
        timeout = int(os.environ.get("AISB_RESOURCES_TIMEOUT", "30") or "30")
        for url in urls:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in ("https", "http", "file"):
                raise RuntimeError(f"Unsupported resource URL scheme for {url!r}")
            dest = resources_dir / _safe_filename_from_url(url)
            _download_url(url, dest, sha_map.get(url), timeout=timeout)

    extra_env = _parse_kv_list(os.environ.get("AISB_INSTALL_ENV_VARS", ""))
    base_env = {
        "AISB_CONFIG_DIR": str(config_dir),
        "AISB_RESOURCES_DIR": str(resources_dir),
        "AISB_STATE_DIR": str(state_dir),
    }
    merged_env = {**base_env, **extra_env}

    def sh_escape(v: str) -> str:
        return "'" + v.replace("'", "'\"'\"'") + "'"

    env_sh_lines = ["# Generated by setup.py post-install tasks", "set -a"]
    for k, v in sorted(merged_env.items()):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k):
            continue
        env_sh_lines.append(f"export {k}={sh_escape(v)}")
    env_sh_lines += ["set +a", ""]
    env_sh = "\n".join(env_sh_lines)

    env_ps1_lines = ["# Generated by setup.py post-install tasks"]
    for k, v in sorted(merged_env.items()):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k):
            continue
        vv = v.replace("`", "``").replace('"', '`"')
        env_ps1_lines.append(f'$env:{k} = "{vv}"')
    env_ps1_lines.append("")
    env_ps1 = "\n".join(env_ps1_lines)

    env_dotenv_lines = ["# Generated by setup.py post-install tasks"]
    for k, v in sorted(merged_env.items()):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k):
            continue
        vv = v.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
        env_dotenv_lines.append(f'{k}="{vv}"')
    env_dotenv_lines.append("")
    env_dotenv = "\n".join(env_dotenv_lines)

    _write_text(config_dir / "env.sh", env_sh)
    _write_text(config_dir / "env.ps1", env_ps1)
    _write_text(config_dir / ".env", env_dotenv)

    if _bool_env("AISB_MODIFY_SHELL_PROFILE", default=False):
        marker = "### AISB ENV (managed) ###"
        block = textwrap.dedent(
            f"""
            {marker}
            # Added by {DIST_NAME} installation; loads per-user config env vars.
            if [ -f {sh_escape(str(config_dir / "env.sh"))} ]; then
              . {sh_escape(str(config_dir / "env.sh"))}
            fi
            ### /AISB ENV (managed) ###
            """
        ).lstrip("\n")
        for profile in _detect_shell_profiles():
            _append_if_missing(profile, marker, block)

    _write_text(
        config_dir / "install.json",
        "{\n"
        f'  "package": "{DIST_NAME}",\n'
        f'  "version": "{DIST_VERSION}",\n'
        f'  "python": "{sys.version.split()[0]}",\n'
        f'  "platform": "{platform.platform()}"\n'
        "}\n",
    )


class InstallWithSetup(_install):
    def run(self):
        _run_pip_install(PIP_INSTALL_AT_INSTALL_TIME)
        super().run()
        _post_install_setup()


class DevelopWithSetup(_develop):
    def run(self):
        _run_pip_install(PIP_INSTALL_AT_INSTALL_TIME)
        super().run()
        _post_install_setup()


setup(
    name=DIST_NAME,
    version=DIST_VERSION,
    description="AI Security Benchmark (internal distribution)",
    long_description=_read_readme(),
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    install_requires=INSTALL_REQUIRES,
    packages=find_packages(exclude=("tests", "output", "reports", "results", "venv", "generated", "__pycache__")),
    include_package_data=True,
    zip_safe=False,
    cmdclass={
        "install": InstallWithSetup,
        "develop": DevelopWithSetup,
    },
)
