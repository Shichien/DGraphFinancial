from __future__ import annotations

from pathlib import Path
import subprocess

from dgcheater.config import APP_CONFIG


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPO_ROOT / APP_CONFIG.streaming.compose_file
OUTPUT_ROOT = REPO_ROOT / APP_CONFIG.paths.output_dir


def project_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def run_compose(args: list[str], env: dict[str, str] | None = None) -> None:
    command = ["docker", "compose", "-f", str(COMPOSE_FILE), *args]
    subprocess.run(command, cwd=REPO_ROOT, env=env, check=True)
