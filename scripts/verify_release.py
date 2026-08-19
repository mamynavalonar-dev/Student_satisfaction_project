from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# When executed as "python scripts/verify_release.py", Python puts
# the scripts/ directory, not the repository root, in sys.path.
# Add the project root explicitly before importing Django.
ROOT_STRING = str(ROOT)
if ROOT_STRING not in sys.path:
    sys.path.insert(0, ROOT_STRING)

MODEL_DIR = ROOT / "deployment" / "model"
MODEL_PATH = MODEL_DIR / "portfolio_model.joblib"
HASH_PATH = MODEL_DIR / "portfolio_model.sha256"
ENV_EXAMPLE = ROOT / ".env.example"
PROCFILE = ROOT / "Procfile"

REQUIRED = (
    ROOT / "manage.py",
    ROOT / "requirements.txt",
    ROOT / "student_satisfaction_project" / "settings.py",
    ROOT / "accounts" / "management" / "commands" / "bootstrap_portfolio.py",
    MODEL_PATH,
    HASH_PATH,
    ENV_EXAMPLE,
    PROCFILE,
)


def fail(message: str) -> None:
    print(f"RELEASE_CHECK_ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def expected_model_hash() -> str:
    line = HASH_PATH.read_text(encoding="utf-8").strip()

    if not line:
        fail("deployment/model/portfolio_model.sha256 est vide.")

    expected = line.split()[0].strip().lower()

    if len(expected) != 64 or any(
        character not in "0123456789abcdef"
        for character in expected
    ):
        fail("Le manifeste SHA-256 du modèle est invalide.")

    return expected


def check_env_example() -> None:
    source = ENV_EXAMPLE.read_text(encoding="utf-8")

    live_password_lines = [
        line
        for line in source.splitlines()
        if line.startswith("PORTFOLIO_DEMO_PASSWORD=")
    ]

    if live_password_lines != ["PORTFOLIO_DEMO_PASSWORD="]:
        fail(
            ".env.example doit contenir exactement une variable "
            "PORTFOLIO_DEMO_PASSWORD vide."
        )

    if "DJANGO_SECRET_KEY=<" in source:
        # Commented example placeholder is explicitly allowed.
        pass

    forbidden = (
        "CI-Portfolio-Only-2026-Quartz",
        "postgres-ci-password",
        "ci-production-simulation-only",
    )

    for value in forbidden:
        if value in source:
            fail(
                f"Une valeur réservée à la CI a fui dans .env.example : {value}"
            )


def check_git_secret_hygiene() -> None:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        fail("git ls-files a échoué.")

    tracked = {
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if line.strip()
    }

    forbidden_tracked = {
        ".env",
        ".env.local",
        ".env.production",
        "db.sqlite3",
    }

    leaked = sorted(
        tracked & forbidden_tracked
    )

    if leaked:
        fail(
            "Fichier runtime/secret versionné : "
            + ", ".join(leaked)
        )


def check_model_loadable() -> None:
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "student_satisfaction_project.settings",
    )
    os.environ.setdefault(
        "DJANGO_ENV",
        "test",
    )
    os.environ.setdefault(
        "DJANGO_DEBUG",
        "0",
    )
    os.environ.setdefault(
        "DJANGO_SECRET_KEY",
        "release-verification-only-not-production-secret",
    )
    os.environ.setdefault(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1,testserver",
    )
    os.environ.setdefault(
        "PORTFOLIO_DEMO_ENABLED",
        "0",
    )

    import django

    django.setup()

    from predictor.neural_network_model import load_model_artifact

    model_data, resolved = load_model_artifact(
        str(MODEL_PATH)
    )

    if resolved.resolve() != MODEL_PATH.resolve():
        fail("Le chemin résolu du modèle packagé est inattendu.")

    if model_data.get("schema_version") != 3:
        fail(
            "Le modèle packagé n'utilise pas le schema_version 3."
        )

    if "pipeline" not in model_data:
        fail("Le modèle packagé ne contient pas de pipeline.")


def main() -> int:
    missing = [
        str(path.relative_to(ROOT))
        for path in REQUIRED
        if not path.is_file()
    ]

    if missing:
        fail(
            "Fichiers release manquants : "
            + ", ".join(missing)
        )

    expected = expected_model_hash()
    actual = sha256(MODEL_PATH)

    if actual != expected:
        fail(
            "SHA-256 du modèle incorrect : "
            f"attendu {expected}, obtenu {actual}."
        )

    check_env_example()
    check_git_secret_hygiene()
    check_model_loadable()

    print("RELEASE_CHECK_OK")
    print(
        "MODEL_SHA256",
        actual,
    )
    print(
        "MODEL_SIZE",
        MODEL_PATH.stat().st_size,
    )
    print(
        "MODEL_SCHEMA",
        3,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
