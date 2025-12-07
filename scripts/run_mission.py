"""CLI entry point to run an AERUM mission loop."""

from __future__ import annotations

import argparse
import time

from aerum.core.controller import AERUMController


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an AERUM mission")
    parser.add_argument("--mission", required=True, help="Mission JSON filename")
    parser.add_argument(
        "--tick-mode",
        choices=["loop", "step"],
        default="loop",
        help="Run continuously or wait for Enter between steps",
    )
    parser.add_argument("--sleep", type=float, default=0.5, help="Sleep between ticks in loop mode")
    args = parser.parse_args()

    controller = AERUMController()
    ok, error = controller.start_mission(args.mission)
    if not ok:
        raise SystemExit(f"Unable to start mission: {error}")

    print(f"Mission {args.mission} launched. Mode={args.tick_mode}")
    try:
        while True:
            status = controller.get_mission_status()
            print(status)
            if status.get("status") in {"ABORTED", "COMPLETED", "FAILED"}:
                break
            if args.tick_mode == "step":
                input("Press Enter to advance...")
            else:
                time.sleep(args.sleep)
    except KeyboardInterrupt:
        controller.abort_mission("Keyboard interrupt")
        print("Abort requested. Exiting.")


if __name__ == "__main__":
    main()
