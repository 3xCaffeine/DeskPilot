"""Vision-only runner (smoke test).

This script intentionally bypasses DSPy/text planning and exercises ONLY the
vision LLM calling path:

screenshot -> vision LLM -> one Action -> execute -> repeat

It is useful for verifying that Gemini/OpenRouter vision is correctly wired,
that JSON parsing works, and that actions execute inside the Docker desktop.

# Example usage (from repo root):
docker exec -it deskpilot-desktop python3 /app/scripts/vision_only.py "Open Chrome" --model "openrouter/google/gemini-2.0-flash-001" --max-steps 10

Notes:
- It uses the same Action schema as the main agent.
- It saves screenshots + an action log under runs/<run_id>/vision_only/
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _ensure_import_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DeskPilot vision-only smoke test")
    p.add_argument("goal", type=str, help="What you want the agent to accomplish")
    p.add_argument(
        "--provider",
        choices=["gemini", "openrouter"],
        default="",
        help=(
            "Optional override. If omitted, provider is inferred from --model: "
            "openrouter/... -> openrouter, otherwise gemini."
        ),
    )
    p.add_argument(
        "--model",
        type=str,
        default="openrouter/google/gemini-2.0-flash-001",
        help=(
            "Model name (same style as run.py). Examples: "
            "'openrouter/google/gemini-2.0-flash-001' or 'gemini/gemini-2.5-flash' or 'gemini-2.5-flash'."
        ),
    )
    p.add_argument("--max-steps", type=int, default=10)
    p.add_argument("--runs-dir", type=str, default="runs")
    p.add_argument(
        "--startup-delay",
        type=float,
        default=0.0,
        help="Seconds to wait before first screenshot/action",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Call vision and log actions, but do not execute them",
    )
    return p.parse_args()


def _infer_provider(provider_arg: str, model: str) -> str:
    if provider_arg:
        return provider_arg
    if (model or "").strip().lower().startswith("openrouter/"):
        return "openrouter"
    return "gemini"


def _llm_from_args(provider_arg: str, model: str):
    provider = _infer_provider(provider_arg, model)

    if provider == "openrouter":
        from cua_backend.llm.openrouter_client import OpenRouterClient

        return OpenRouterClient(model=model or "openrouter/google/gemini-2.0-flash-001")

    # gemini
    from cua_backend.llm.gemini_client import GeminiClient

    # GeminiClient expects a Gemini model name without any 'gemini/' prefix
    cleaned = (model or "").strip()
    cleaned = cleaned.replace("gemini/", "")
    return GeminiClient(model=cleaned or None)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main() -> int:
    _ensure_import_path()
    args = _parse_args()

    from cua_backend.execution.desktop_controller import DesktopController
    from cua_backend.schemas.actions import DoneAction, FailAction

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = Path(args.runs_dir) / run_id / "vision_only"
    screenshots_dir = base_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    controller = DesktopController(startup_delay=args.startup_delay)
    llm = _llm_from_args(args.provider, args.model)

    meta = {
        "mode": "vision_only",
        "provider": getattr(llm.info(), "provider", "unknown"),
        "model": getattr(llm.info(), "model", "unknown"),
        "goal": args.goal,
        "max_steps": args.max_steps,
        "dry_run": args.dry_run,
        "run_id": run_id,
    }
    _write_json(base_dir / "metadata.json", meta)

    history: List[Dict[str, Any]] = []
    action_log_path = base_dir / "actions.jsonl"

    print(f"🧪 Vision-only run: provider={meta['provider']} model={meta['model']}")
    print(f"🎯 Goal: {args.goal}")

    for step in range(1, args.max_steps + 1):
        screenshot = controller.screenshot()
        ss_path = screenshots_dir / f"step_{step:03d}.png"
        screenshot.save(ss_path)

        try:
            action = llm.get_next_action(
                screenshot=screenshot,
                goal=args.goal,
                history=history[-5:] if history else None,
            )
        except Exception as e:
            print(f"❌ Vision call failed at step {step}: {e}")
            _write_json(base_dir / "error.json", {"step": step, "error": str(e)})
            return 1

        print(f"   🤖 Vision → {action.type}: {getattr(action, 'reason', '')}")

        if isinstance(action, DoneAction):
            print(f"✅ DONE: {action.final_answer or ''}")
            with open(action_log_path, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "step": step,
                            "screenshot": str(ss_path),
                            "action": action.model_dump(),
                            "result": {"ok": True, "note": "DONE"},
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            return 0

        if isinstance(action, FailAction):
            print(f"❌ FAIL: {action.error}")
            with open(action_log_path, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "step": step,
                            "screenshot": str(ss_path),
                            "action": action.model_dump(),
                            "result": {"ok": False, "error": action.error},
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            return 2

        if args.dry_run:
            result = {"ok": True, "note": "dry_run (not executed)"}
        else:
            exec_result = controller.execute(action)
            result = {"ok": exec_result.ok, "error": exec_result.error}

        with open(action_log_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "step": step,
                        "screenshot": str(ss_path),
                        "action": action.model_dump(),
                        "result": result,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

        history.append(
            {
                "step": step,
                "action": action.model_dump(),
                "result_ok": bool(result.get("ok")),
                "screenshot_path": str(ss_path),
                "error": result.get("error"),
            }
        )

        if not result.get("ok"):
            print(f"   ⚠️ Execution error: {result.get('error')}")

    print("⚠️ Max steps reached (vision-only)")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
