#!/usr/bin/env python3
import json
import os
import shlex
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from setuptools import Command, find_packages, setup
from setuptools._distutils.errors import DistutilsSetupError
from setuptools.command.develop import develop
from setuptools.command.install import install

PACKAGE_NAME = "ai-security-benchmark"
PACKAGE_DIR_NAME = "ai_security_benchmark"
PROJECT_ROOT = Path(__file__).resolve().parent
README_PATH = PROJECT_ROOT / "README.md"
CONFIG_SOURCE_FILE = PROJECT_ROOT / "benchmark_config.yaml"
PROMPTS_SOURCE_DIR = PROJECT_ROOT / "prompts"

ENV_PREFIX = "AI_SECURITY_BENCHMARK"
CONFIG_DIR_ENV = f"{ENV_PREFIX}_CONFIG_DIR"
DATA_DIR_ENV = f"{ENV_PREFIX}_HOME"
CACHE_DIR_ENV = f"{ENV_PREFIX}_CACHE_DIR"
RESOURCE_DIR_ENV = f"{ENV_PREFIX}_RESOURCE_DIR"
RESOURCE_URLS_ENV = f"{ENV_PREFIX}_RESOURCE_URLS"
INSTALL_ENV_ENV = f"{ENV_PREFIX}_INSTALL_ENV"
OVERWRITE_ENV = f"{ENV_PREFIX}_OVERWRITE_RESOURCES"
CONFIG_FILE_ENV = f"{ENV_PREFIX}_CONFIG_FILE"
PROMPTS_FILE_ENV = f"{ENV_PREFIX}_PROMPTS_FILE"

TOP_LEVEL_MODULES = [
    "auto_benchmark",
    "cache_manager",
    "code_generator",
    "runner",
    "status",
]

BASE_REQUIREMENTS = [
    "PyYAML>=6.0",
    "jsonschema>=4.0",
    "requests>=2.31.0",
]

PROVIDER_REQUIREMENTS = [
    "openai>=1.0.0",
    "anthropic>=0.34.0",
    "google-genai>=1.0.0",
    "ollama>=0.4.0",
]

ANALYSIS_REQUIREMENTS = [
    "numpy>=1.24.0",
]

DEV_REQUIREMENTS = [
    "pytest>=7.0.0",
]


def _read_long_description():
    if README_PATH.exists():
        return README_PATH.read_text(encoding="utf-8")
    return "Internal distribution for the AI Security Benchmark toolchain."


def _truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _split_entries(raw_value):
    if not raw_value:
        return []
    if "\n" in raw_value:
        entries = raw_value.splitlines()
    else:
        entries = raw_value.split(",")
    return [entry.strip() for entry in entries if entry.strip()]


def _parse_install_env(raw_value):
    env_map = {}
    for entry in _split_entries(raw_value):
        if "=" not in entry:
            raise DistutilsSetupError(
                f"Invalid {INSTALL_ENV_ENV} entry '{entry}'. Expected KEY=VALUE."
            )
        key, value = entry.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise DistutilsSetupError(
                f"Invalid {INSTALL_ENV_ENV} entry '{entry}'. Environment variable name is empty."
            )
        env_map[key] = value
    return env_map


def _safe_resource_name(url, index):
    parsed = urlparse(url)
    candidate = Path(unquote(parsed.path)).name
    if candidate:
        return candidate
    return f"resource_{index}.bin"


def _parse_resource_specs(raw_value):
    resource_specs = []
    for index, entry in enumerate(_split_entries(raw_value), start=1):
        if "=" in entry and "://" not in entry.split("=", 1)[0]:
            name, url = entry.split("=", 1)
            name = name.strip()
            url = url.strip()
        else:
            url = entry.strip()
            name = _safe_resource_name(url, index)
        if not url or not name:
            raise DistutilsSetupError(
                f"Invalid {RESOURCE_URLS_ENV} entry '{entry}'. Expected NAME=URL or URL."
            )
        resource_specs.append({"name": name, "url": url})
    return resource_specs


def _default_paths():
    config_dir = Path(os.environ.get(CONFIG_DIR_ENV, Path.home() / ".config" / PACKAGE_NAME)).expanduser()
    data_dir = Path(os.environ.get(DATA_DIR_ENV, Path.home() / ".local" / "share" / PACKAGE_NAME)).expanduser()
    cache_dir = Path(os.environ.get(CACHE_DIR_ENV, Path.home() / ".cache" / PACKAGE_NAME)).expanduser()
    resource_dir = Path(os.environ.get(RESOURCE_DIR_ENV, data_dir / "resources")).expanduser()
    prompts_dir = resource_dir / "prompts"
    config_file = Path(os.environ.get(CONFIG_FILE_ENV, config_dir / CONFIG_SOURCE_FILE.name)).expanduser()
    prompts_file = Path(os.environ.get(PROMPTS_FILE_ENV, prompts_dir / "prompts.yaml")).expanduser()
    return {
        "config_dir": config_dir,
        "data_dir": data_dir,
        "cache_dir": cache_dir,
        "resource_dir": resource_dir,
        "prompts_dir": prompts_dir,
        "config_file": config_file,
        "prompts_file": prompts_file,
    }


def _ensure_directories(paths):
    for key in ("config_dir", "data_dir", "cache_dir", "resource_dir", "prompts_dir"):
        paths[key].mkdir(parents=True, exist_ok=True)


def _should_overwrite():
    return _truthy(os.environ.get(OVERWRITE_ENV, "0"))


def _copy_resource(source_path, destination_path, overwrite):
    if not source_path.exists():
        return None
    if destination_path.exists() and not overwrite:
        return None
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)
    return str(destination_path)


def _copy_local_resources(paths):
    copied = []
    overwrite = _should_overwrite()

    copied_config = _copy_resource(CONFIG_SOURCE_FILE, paths["config_file"], overwrite)
    if copied_config:
        copied.append(copied_config)

    if PROMPTS_SOURCE_DIR.exists():
        for source_file in sorted(PROMPTS_SOURCE_DIR.glob("*.yaml")):
            destination = paths["prompts_dir"] / source_file.name
            copied_file = _copy_resource(source_file, destination, overwrite)
            if copied_file:
                copied.append(copied_file)

    return copied


def _download_resources(paths):
    downloaded = []
    resource_specs = _parse_resource_specs(os.environ.get(RESOURCE_URLS_ENV, ""))
    for spec in resource_specs:
        target_path = paths["resource_dir"] / spec["name"]
        target_path.parent.mkdir(parents=True, exist_ok=True)
        request = Request(
            spec["url"],
            headers={"User-Agent": f"{PACKAGE_NAME}-installer/1.0"},
        )
        try:
            with urlopen(request, timeout=60) as response, target_path.open("wb") as output_file:
                shutil.copyfileobj(response, output_file)
        except Exception as exc:
            raise DistutilsSetupError(
                f"Failed to download installer resource '{spec['url']}' to '{target_path}': {exc}"
            ) from exc
        downloaded.append(str(target_path))
    return downloaded


def _write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _format_env_lines(env_map):
    return [f"{key}={value}" for key, value in sorted(env_map.items())]


def _format_shell_exports(env_map):
    lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
    for key, value in sorted(env_map.items()):
        lines.append(f"export {key}={shlex.quote(value)}")
    lines.append("")
    return "\n".join(lines)


def _format_powershell_exports(env_map):
    lines = []
    for key, value in sorted(env_map.items()):
        escaped_value = value.replace('"', '`"')
        lines.append(f'$env:{key} = "{escaped_value}"')
    lines.append("")
    return "\n".join(lines)


def _write_environment_files(paths, env_map, copied_resources, downloaded_resources):
    metadata = {
        "package": PACKAGE_NAME,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "directories": {
            "config_dir": str(paths["config_dir"]),
            "data_dir": str(paths["data_dir"]),
            "cache_dir": str(paths["cache_dir"]),
            "resource_dir": str(paths["resource_dir"]),
            "prompts_dir": str(paths["prompts_dir"]),
        },
        "resources": {
            "copied": copied_resources,
            "downloaded": downloaded_resources,
        },
        "environment": env_map,
    }

    env_file = paths["config_dir"] / ".env"
    shell_file = paths["config_dir"] / "activate.sh"
    powershell_file = paths["config_dir"] / "activate.ps1"
    metadata_file = paths["config_dir"] / "install_state.json"

    _write_text(env_file, "\n".join(_format_env_lines(env_map)) + "\n")
    _write_text(shell_file, _format_shell_exports(env_map))
    _write_text(powershell_file, _format_powershell_exports(env_map))
    _write_text(metadata_file, json.dumps(metadata, indent=2, sort_keys=True) + "\n")

    shell_file.chmod(0o700)


def _bootstrap_environment():
    paths = _default_paths()
    _ensure_directories(paths)

    copied_resources = _copy_local_resources(paths)
    downloaded_resources = _download_resources(paths)

    env_map = {
        DATA_DIR_ENV: str(paths["data_dir"]),
        CONFIG_DIR_ENV: str(paths["config_dir"]),
        CACHE_DIR_ENV: str(paths["cache_dir"]),
        RESOURCE_DIR_ENV: str(paths["resource_dir"]),
        CONFIG_FILE_ENV: str(paths["config_file"]),
        PROMPTS_FILE_ENV: str(paths["prompts_file"]),
    }
    env_map.update(_parse_install_env(os.environ.get(INSTALL_ENV_ENV, "")))

    os.environ.update(env_map)
    _write_environment_files(paths, env_map, copied_resources, downloaded_resources)

    print(f"[setup.py] Bootstrapped configuration in {paths['config_dir']}")
    return paths


def _build_data_files():
    data_files = []

    if CONFIG_SOURCE_FILE.exists():
        data_files.append((f"share/{PACKAGE_DIR_NAME}", [str(CONFIG_SOURCE_FILE)]))

    if PROMPTS_SOURCE_DIR.exists():
        prompt_files = [str(path) for path in sorted(PROMPTS_SOURCE_DIR.glob("*.yaml"))]
        if prompt_files:
            data_files.append((f"share/{PACKAGE_DIR_NAME}/prompts", prompt_files))

    return data_files


class BootstrapCommand(Command):
    description = "Download resources and create user-scoped configuration files"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        _bootstrap_environment()


class InstallWithBootstrap(install):
    def run(self):
        super().run()
        self.run_command("bootstrap")


class DevelopWithBootstrap(develop):
    def run(self):
        super().run()
        self.run_command("bootstrap")


extras_require = {
    "providers": PROVIDER_REQUIREMENTS,
    "analysis": ANALYSIS_REQUIREMENTS,
    "dev": DEV_REQUIREMENTS,
}
extras_require["all"] = sorted(
    {requirement for values in extras_require.values() for requirement in values}
)

setup(
    name=PACKAGE_NAME,
    version="0.1.0",
    description="Internal distribution for the AI Security Benchmark toolchain",
    long_description=_read_long_description(),
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    packages=find_packages(
        exclude=(
            "output",
            "output.*",
            "reports",
            "reports.*",
            "archives",
            "archives.*",
            "backups",
            "backups.*",
            "deprecated",
            "deprecated.*",
            "venv",
            "venv.*",
            "charts",
            "charts.*",
        )
    ),
    py_modules=TOP_LEVEL_MODULES,
    include_package_data=True,
    data_files=_build_data_files(),
    install_requires=BASE_REQUIREMENTS,
    extras_require=extras_require,
    entry_points={
        "console_scripts": [
            "ai-security-benchmark=auto_benchmark:main",
            "ai-security-generate=code_generator:main",
            "ai-security-run=runner:main",
        ]
    },
    cmdclass={
        "bootstrap": BootstrapCommand,
        "install": InstallWithBootstrap,
        "develop": DevelopWithBootstrap,
    },
    zip_safe=False,
)