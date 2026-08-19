from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANAGE = ROOT / "manage.py"
VERIFY_RELEASE = ROOT / "scripts" / "verify_release.py"


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def run(command: list[str], env: dict[str, str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def main() -> int:
    target = os.environ.get("VERCEL_ENV", "").strip().lower()

    if target not in {"preview", "production"}:
        print(
            "VERCEL_BUILD_SKIP: environnement Vercel "
            f"{target or 'absent'} ; aucun bootstrap distant."
        )
        return 0

    if not os.environ.get("DATABASE_URL", "").strip():
        raise RuntimeError(
            f"DATABASE_URL est obligatoire pour un build Vercel {target}."
        )

    command_env = os.environ.copy()
    unpooled = os.environ.get("DATABASE_URL_UNPOOLED", "").strip()

    if unpooled:
        command_env["DATABASE_URL"] = unpooled
        db_mode = "directe/non poolée pour migrations"
    else:
        db_mode = "DATABASE_URL disponible"

    commands = [
        [sys.executable, str(VERIFY_RELEASE)],
        [sys.executable, str(MANAGE), "migrate", "--noinput"],
        [sys.executable, str(MANAGE), "setup_roles"],
    ]

    if env_bool("PORTFOLIO_DEMO_ENABLED"):
        commands.append(
            [sys.executable, str(MANAGE), "bootstrap_portfolio"]
        )

    print("VERCEL_BUILD_TARGET:", target, "| DB:", db_mode)

    if env_bool("VERCEL_BUILD_DRY_RUN"):
        for command in commands:
            print("DRY_RUN:", " ".join(command))
        print("VERCEL_BUILD_DRY_RUN_OK")
        return 0

    for command in commands:
        run(command, command_env)

    print("VERCEL_BUILD_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
