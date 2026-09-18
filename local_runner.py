#!/usr/bin/env python3
"""Local entrypoint that adds the documented deploy.sh application contract."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


PRODUCTION_RUNNER_PATH = Path("/opt/arcbench/run_submission.py")


def load_production_runner():
    spec = importlib.util.spec_from_file_location("arcbench_production_runner", PRODUCTION_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load the production runner: {PRODUCTION_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def wait_for_deployed_application(runner, process: subprocess.Popen, timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    runner.append_debug_log(
        f"Waiting for custom deploy.sh application at {runner.WEB_APP_BASE_URL} "
        f"with timeout={timeout_seconds}s"
    )
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"deploy.sh exited before the application became ready (code={process.returncode})"
            )
        try:
            with urlopen(runner.WEB_APP_BASE_URL, timeout=2) as response:
                if response.status < 500:
                    runner.append_debug_log(
                        f"Custom deploy.sh application became ready with status={response.status}"
                    )
                    return
        except (URLError, TimeoutError):
            time.sleep(1)
    raise TimeoutError(
        f"deploy.sh did not make the application reachable at "
        f"{runner.WEB_APP_BASE_URL} within {timeout_seconds} seconds"
    )


def install_deploy_script_contract(runner) -> None:
    default_run_web_template = runner.run_web_template

    def run_web_template(stdout_file, stderr_file) -> dict:
        deploy_script = runner.PROJECT_DIR / "deploy.sh"
        if not deploy_script.is_file():
            return default_run_web_template(stdout_file, stderr_file)

        application_env = {
            **os.environ,
            "HOST": "0.0.0.0",
            "PORT": str(runner.WEB_APP_PORT),
            "ARCBENCH_WEB_BASE_URL": runner.WEB_APP_BASE_URL,
        }
        runner.append_runner_event("run_tests", "Starting generated application with deploy.sh")
        process, stdout_thread, stderr_thread = runner.start_background_process(
            ["bash", str(deploy_script)],
            cwd=runner.PROJECT_DIR,
            stdout_file=stdout_file,
            stderr_file=stderr_file,
            label="template-deploy-script",
            env=application_env,
        )
        runner.append_runner_event(
            "run_tests",
            f"deploy.sh started (pid={process.pid})",
            status="success",
        )
        wait_for_deployed_application(runner, process)
        runner.append_runner_event(
            "run_tests",
            f"Template application is reachable on {runner.WEB_APP_BASE_URL}",
            status="success",
        )
        return {
            "app_process": process,
            "app_stdout_thread": stdout_thread,
            "app_stderr_thread": stderr_thread,
            "base_url": runner.WEB_APP_BASE_URL,
        }

    runner.run_web_template = run_web_template


def main() -> int:
    runner = load_production_runner()
    install_deploy_script_contract(runner)
    return int(runner.main())


if __name__ == "__main__":
    raise SystemExit(main())

