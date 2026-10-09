import os
import subprocess
import sys
import time
from datetime import datetime
from core.database import get_session
from core.models import TestRun, Script
from core.security import validate_script_path

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")


def execute_script(script_id: int) -> dict:
    db = get_session()
    try:
        script = db.query(Script).filter(Script.id == script_id).first()
        if not script:
            raise ValueError(f"Script {script_id} not found")

        script_path = script.script_path

        if not script_path or not os.path.exists(script_path):
            raise FileNotFoundError(f"Script file not found: {script_path}")

        if not validate_script_path(script_path):
            raise ValueError(f"Invalid script path (path traversal detected): {script_path}")

        run = TestRun(
            script_id=script_id,
            test_name=script.title,
            feature=script.feature,
            status="running",
            started_at=datetime.utcnow(),
            script_path=script_path,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        os.makedirs(REPORTS_DIR, exist_ok=True)
        screenshot_dir = os.path.join(REPORTS_DIR, "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)

        env = os.environ.copy()
        env["SCREENSHOT_DIR"] = screenshot_dir
        # Re-read HEADLESS_BROWSER from .env at execution time so live changes take effect
        from dotenv import dotenv_values
        live = dotenv_values(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
        if "HEADLESS_BROWSER" in live:
            env["HEADLESS_BROWSER"] = live["HEADLESS_BROWSER"]

        start_time = time.time()
        try:
            report_path = os.path.join(REPORTS_DIR, f"report_{run.id}.html")
            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest", script_path,
                    "-v", "--tb=short",
                    f"--html={report_path}",
                    "--self-contained-html",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )

            duration = time.time() - start_time
            output = result.stdout + result.stderr

            run.status = "passed" if result.returncode == 0 else "failed"
            if result.returncode != 0:
                run.error_message = result.stderr[:2000] if result.stderr else "Test failed"
            run.output = output[:5000]
            run.duration_seconds = round(duration, 2)
            run.completed_at = datetime.utcnow()

        except subprocess.TimeoutExpired:
            run.status = "error"
            run.error_message = "Test execution timed out after 120 seconds"
            run.duration_seconds = round(time.time() - start_time, 2)
            run.completed_at = datetime.utcnow()
        except Exception as e:
            run.status = "error"
            run.error_message = type(e).__name__
            run.duration_seconds = round(time.time() - start_time, 2)
            run.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(run)
        run_dict = _run_to_dict(run)

        # Persist JSON log asynchronously (best-effort)
        try:
            from test_execution_engine.result_collector import ResultCollector
            ResultCollector().save_json_log(run_dict)
        except Exception:
            pass

        return run_dict
    finally:
        db.close()


def get_all_runs() -> list:
    db = get_session()
    try:
        runs = db.query(TestRun).order_by(TestRun.started_at.desc()).all()
        return [_run_to_dict(r) for r in runs]
    finally:
        db.close()


def get_run_summary() -> dict:
    db = get_session()
    try:
        runs = db.query(TestRun).all()
        total = len(runs)
        passed = sum(1 for r in runs if r.status == "passed")
        failed = sum(1 for r in runs if r.status == "failed")
        error = sum(1 for r in runs if r.status == "error")
        pass_rate = round(passed / total * 100, 1) if total > 0 else 0.0
        return {"total": total, "passed": passed, "failed": failed, "error": error, "pass_rate": pass_rate}
    finally:
        db.close()


def get_run_by_id(run_id: int) -> dict | None:
    db = get_session()
    try:
        r = db.query(TestRun).filter(TestRun.id == run_id).first()
        return _run_to_dict(r) if r else None
    finally:
        db.close()


def _run_to_dict(r: TestRun) -> dict:
    return {
        "id": r.id,
        "script_id": r.script_id,
        "test_name": r.test_name,
        "feature": r.feature,
        "status": r.status,
        "output": r.output,
        "error_message": r.error_message,
        "duration_seconds": r.duration_seconds,
        "script_path": r.script_path,
        "started_at": r.started_at,
        "completed_at": r.completed_at,
    }
