from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import json
import urllib.request
import webbrowser
from pathlib import Path

import typer

from .dgraph_prior import DGraphAccountPrior


app = typer.Typer(no_args_is_help=False)


@app.callback(invoke_without_command=True)
def main(
    event_count: int = 200_000,
    interval_ms: int = 80,
    api_port: int = 8060,
    infra_only: bool = False,
    feature_backend: str = typer.Option("flink", help="Feature backend: flink or python."),
    open_dashboard: bool = typer.Option(True, help="Open dashboard URL after startup."),
) -> None:
    """Start local realtime anti-fraud infrastructure and workers."""
    if feature_backend not in {"flink", "python"}:
        raise typer.BadParameter("feature_backend 只能是 flink 或 python。")
    repo_root = Path(__file__).resolve().parents[3]
    compose_file = repo_root / "infra" / "realtime" / "docker-compose.yml"
    if not compose_file.exists():
        raise SystemExit(f"缺少 Docker Compose 文件：{compose_file}")
    docker_runner = _resolve_docker_runner(repo_root)
    keepalive = docker_runner.start_keepalive()
    docker_runner.run_compose(["up", "-d"])

    env = os.environ.copy()
    env.setdefault("DG_BOOTSTRAP_SERVERS", "localhost:9094")
    env.setdefault("DG_DATABASE_URL", "postgresql://dgcheater:dgcheater@localhost:55432/dgcheater")
    env.setdefault("DG_REDIS_URL", "redis://localhost:6379/0")
    env.setdefault("DG_NEO4J_URI", "bolt://localhost:7687")
    env.setdefault("DG_NEO4J_USER", "neo4j")
    env.setdefault("DG_NEO4J_PASSWORD", "dgcheater")
    if infra_only:
        print("基础服务已启动。")
        if keepalive is not None:
            print("WSL Docker 保活进程已启动，关闭当前终端不会立即停止基础服务。")
        _print_urls()
        return

    processes: list[subprocess.Popen[str]] = []
    service_processes: list[subprocess.Popen[str]] = []
    try:
        if keepalive is not None:
            processes.append(keepalive)
        uv = _find_executable("uv")
        _ensure_dgraph_prior(repo_root)
        _ensure_frontend_dist(repo_root)
        service_processes.append(
            _start(
                repo_root,
                env,
                [
                    uv,
                    "run",
                    "uvicorn",
                    "dgcheater.realtime.dashboard_api:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(api_port),
                ],
            )
        )
        if feature_backend == "flink":
            docker_runner.run_compose(["--profile", "flink-job", "up", "-d", "flink-submit-realtime-features"])
            _wait_for_flink_job()
            print("特征后端：Flink。不会启动 Python feature-worker。")
        else:
            service_processes.append(_start(repo_root, env, [uv, "run", "dgcheater-realtime", "feature-worker"]))
            print("特征后端：Python feature-worker。")
        service_processes.append(_start(repo_root, env, [uv, "run", "dgcheater-realtime", "scoring-worker"]))
        processes.extend(service_processes)
        time.sleep(2)
        processes.append(
            _start(
                repo_root,
                env,
                [
                    uv,
                    "run",
                    "dgcheater-realtime",
                    "produce",
                    "--event-count",
                    str(event_count),
                    "--interval-ms",
                    str(interval_ms),
                ],
            )
        )
        print("实时反诈系统已启动。按 Ctrl+C 停止本地实时进程。")
        _print_urls(api_port)
        if open_dashboard:
            webbrowser.open(f"http://127.0.0.1:{api_port}")
        sys.stdout.flush()
        while all(process.poll() is None for process in service_processes):
            time.sleep(1)
    except KeyboardInterrupt:
        print("正在停止本地实时进程。")
    finally:
        _stop_all(processes)


def _start(repo_root: Path, env: dict[str, str], args: list[str]) -> subprocess.Popen[str]:
    print("启动：" + " ".join(args))
    return subprocess.Popen(args, cwd=repo_root, env=env, text=True)


def _ensure_frontend_dist(repo_root: Path) -> None:
    frontend_dir = repo_root / "frontend" / "graph-stream"
    dist_index = frontend_dir / "dist" / "index.html"
    package_json = frontend_dir / "package.json"
    if not package_json.exists():
        return
    source_paths = [
        package_json,
        frontend_dir / "package-lock.json",
        frontend_dir / "index.html",
        *list((frontend_dir / "src").rglob("*")),
    ]
    newest_source = max((path.stat().st_mtime for path in source_paths if path.is_file()), default=0.0)
    if dist_index.exists() and dist_index.stat().st_mtime >= newest_source:
        return
    npm = _find_executable("npm")
    print("构建 Vue 实时大屏。")
    subprocess.run([npm, "install"], cwd=frontend_dir, check=True)
    subprocess.run([npm, "run", "build"], cwd=frontend_dir, check=True)


def _ensure_dgraph_prior(repo_root: Path) -> None:
    print("加载 DGraph 账户风险先验。")
    prior = DGraphAccountPrior.load(repo_root=repo_root)
    print(f"DGraph 先验已就绪：{prior.metadata.node_count} 个节点，AUC {prior.metadata.valid_auc:.6f}。")


def _wait_for_flink_job(timeout_sec: int = 120) -> None:
    deadline = time.monotonic() + timeout_sec
    last_state = "unknown"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8081/jobs/overview", timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            for job in payload.get("jobs", []):
                if job.get("name") == "dgcheater-realtime-features":
                    last_state = str(job.get("state", "unknown"))
                    tasks = job.get("tasks", {})
                    if last_state == "RUNNING" and int(tasks.get("running", 0)) == int(tasks.get("total", 0)):
                        return
        except Exception:
            last_state = "unavailable"
        time.sleep(2)
    raise SystemExit(f"Flink 实时特征作业未在 {timeout_sec} 秒内就绪，最后状态：{last_state}")


class DockerRunner:
    def __init__(self, repo_root: Path, docker: str | None, wsl: str | None) -> None:
        self.repo_root = repo_root
        self.docker = docker
        self.wsl = wsl
        self.compose_file = repo_root / "infra" / "realtime" / "docker-compose.yml"
        self.wsl_repo_root: str | None = None

    @property
    def uses_wsl(self) -> bool:
        return self.docker is None

    def run_compose(self, args: list[str]) -> None:
        if self.docker is not None:
            subprocess.run(
                [self.docker, "compose", "-f", str(self.compose_file), *args],
                check=True,
                cwd=self.repo_root,
            )
            return
        if self.wsl is None:
            raise SystemExit("找不到 docker，也找不到 wsl。请安装 Docker 或在 WSL 中安装 Docker。")
        command = "cd " + _shell_quote(self._wsl_repo_root()) + " && docker compose -f infra/realtime/docker-compose.yml " + " ".join(
            _shell_quote(item) for item in args
        )
        subprocess.run([self.wsl, "--", "bash", "-lc", command], check=True, cwd=self.repo_root)

    def start_keepalive(self) -> subprocess.Popen[str] | None:
        if not self.uses_wsl or self.wsl is None:
            return None
        return subprocess.Popen(
            [self.wsl, "--", "bash", "-lc", "while sleep 3600; do :; done"],
            cwd=self.repo_root,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _wsl_repo_root(self) -> str:
        if self.wsl_repo_root is None:
            windows_path = str(self.repo_root).replace("\\", "/")
            result = subprocess.run(
                [self.wsl or "wsl", "--", "wslpath", "-a", windows_path],
                check=True,
                cwd=self.repo_root,
                text=True,
                capture_output=True,
            )
            self.wsl_repo_root = result.stdout.strip()
        return self.wsl_repo_root


def _resolve_docker_runner(repo_root: Path) -> DockerRunner:
    docker = _which_optional("docker")
    if docker is not None:
        return DockerRunner(repo_root, docker=docker, wsl=None)
    wsl = _which_optional("wsl")
    if wsl is None:
        raise SystemExit("找不到 docker，也找不到 wsl。请安装 Docker 或在 WSL 中安装 Docker。")
    probe = subprocess.run(
        [wsl, "--", "bash", "-lc", "command -v docker >/dev/null 2>&1 && docker version >/dev/null 2>&1"],
        cwd=repo_root,
        text=True,
    )
    if probe.returncode != 0:
        raise SystemExit("Windows 侧找不到 docker，WSL 中的 docker 也不可用。请先启动 WSL Docker。")
    return DockerRunner(repo_root, docker=None, wsl=wsl)


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def _stop_all(processes: list[subprocess.Popen[str]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 8
    for process in processes:
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.2)
        if process.poll() is None:
            process.kill()


def _find_executable(name: str) -> str:
    resolved = _which_optional(name)
    if resolved is None:
        raise SystemExit(f"找不到命令：{name}。请确认它已经安装并加入 PATH。")
    return resolved


def _which_optional(name: str) -> str | None:
    resolved = shutil.which(name)
    if resolved is None and os.name == "nt":
        resolved = shutil.which(f"{name}.exe")
    return resolved


def _print_urls(api_port: int = 8060) -> None:
    print(f"实时 API: http://127.0.0.1:{api_port}")
    print("Kafka UI: http://127.0.0.1:8088")
    print("Flink UI: http://127.0.0.1:8081")
    print("Neo4j: http://127.0.0.1:7474")


if __name__ == "__main__":
    app()
