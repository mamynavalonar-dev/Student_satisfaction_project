from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

ROOT = Path(settings.BASE_DIR)
PYPROJECT = ROOT / "pyproject.toml"
PYTHON_VERSION = ROOT / ".python-version"
VERCEL_BUILD = ROOT / "scripts" / "vercel_build.py"
CI = ROOT / ".github" / "workflows" / "ci.yml"


def clean_env():
    env = os.environ.copy()
    for name in (
        "DJANGO_ENV",
        "DJANGO_DEBUG",
        "DJANGO_SECRET_KEY",
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "DATABASE_URL",
        "DATABASE_URL_UNPOOLED",
        "DJANGO_DB_CONN_MAX_AGE",
        "PORTFOLIO_DEMO_ENABLED",
        "PORTFOLIO_DEMO_USERNAME",
        "PORTFOLIO_DEMO_EMAIL",
        "PORTFOLIO_DEMO_PASSWORD",
        "PORTFOLIO_MODEL_PATH",
        "VERCEL",
        "VERCEL_ENV",
        "VERCEL_URL",
        "VERCEL_BRANCH_URL",
        "VERCEL_PROJECT_PRODUCTION_URL",
        "VERCEL_BUILD_DRY_RUN",
    ):
        env.pop(name, None)
    env["DJANGO_SETTINGS_MODULE"] = "student_satisfaction_project.settings"
    return env


def settings_snapshot(env):
    code = (
        "import json\n"
        "from django.conf import settings\n"
        "print(json.dumps({"
        "'is_vercel': settings.IS_VERCEL,"
        "'hosts': settings.ALLOWED_HOSTS,"
        "'csrf': settings.CSRF_TRUSTED_ORIGINS,"
        "'middleware': settings.MIDDLEWARE,"
        "'static_backend': settings.STORAGES['staticfiles']['BACKEND'],"
        "'conn_max_age': settings.DATABASES['default'].get('CONN_MAX_AGE'),"
        "'proxy': settings.SECURE_PROXY_SSL_HEADER"
        "}))\n"
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )


class VercelNeonV174Tests(SimpleTestCase):
    def test_runtime_manifest_targets_python_312(self):
        project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        self.assertEqual(project["project"]["requires-python"], "~=3.12.0")
        self.assertEqual(
            project["tool"]["vercel"]["scripts"]["build"],
            "python scripts/vercel_build.py",
        )
        self.assertEqual(
            PYTHON_VERSION.read_text(encoding="utf-8").strip(),
            "3.12",
        )

    def test_runtime_dependencies_keep_ml_and_postgres(self):
        project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        dependencies = set(project["project"]["dependencies"])
        for dependency in (
            "Django==5.2.17",
            "pandas==3.0.5",
            "numpy==2.4.6",
            "scikit-learn==1.9.0",
            "joblib==1.5.3",
            "dj-database-url==3.1.2",
            "psycopg[binary]==3.3.4",
        ):
            with self.subTest(dependency=dependency):
                self.assertIn(dependency, dependencies)

    def test_vercel_system_hosts_and_csrf_are_derived_without_wildcard(self):
        env = clean_env()
        env.update(
            {
                "DJANGO_ENV": "production",
                "DJANGO_DEBUG": "0",
                "DJANGO_SECRET_KEY": "vercel-test-" + ("x7Q_" * 30),
                "DATABASE_URL": "postgresql://u:p@localhost:5432/db",
                "PORTFOLIO_DEMO_ENABLED": "0",
                "VERCEL": "1",
                "VERCEL_ENV": "preview",
                "VERCEL_URL": "preview-a.vercel.app",
                "VERCEL_BRANCH_URL": "branch-a.vercel.app",
                "VERCEL_PROJECT_PRODUCTION_URL": "prod-a.vercel.app",
            }
        )
        result = settings_snapshot(env)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout.strip())
        self.assertTrue(data["is_vercel"])
        self.assertIn("preview-a.vercel.app", data["hosts"])
        self.assertIn("prod-a.vercel.app", data["hosts"])
        self.assertNotIn("*", data["hosts"])
        self.assertIn("https://preview-a.vercel.app", data["csrf"])
        self.assertIn("https://prod-a.vercel.app", data["csrf"])

    def test_vercel_uses_cdn_static_path_and_short_db_connection(self):
        env = clean_env()
        env.update(
            {
                "DJANGO_ENV": "production",
                "DJANGO_DEBUG": "0",
                "DJANGO_SECRET_KEY": "vercel-static-" + ("A8m_" * 30),
                "DATABASE_URL": "postgresql://u:p@localhost:5432/db",
                "PORTFOLIO_DEMO_ENABLED": "0",
                "VERCEL": "1",
                "VERCEL_ENV": "production",
                "VERCEL_URL": "prod-a.vercel.app",
                "VERCEL_PROJECT_PRODUCTION_URL": "prod-a.vercel.app",
            }
        )
        result = settings_snapshot(env)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout.strip())
        self.assertNotIn(
            "whitenoise.middleware.WhiteNoiseMiddleware",
            data["middleware"],
        )
        self.assertEqual(
            data["static_backend"],
            "django.contrib.staticfiles.storage.StaticFilesStorage",
        )
        self.assertEqual(data["conn_max_age"], 30)
        self.assertEqual(
            data["proxy"],
            ["HTTP_X_FORWARDED_PROTO", "https"],
        )

    def test_generic_production_keeps_whitenoise(self):
        env = clean_env()
        env.update(
            {
                "DJANGO_ENV": "production",
                "DJANGO_DEBUG": "0",
                "DJANGO_SECRET_KEY": "generic-prod-" + ("Z6r_" * 30),
                "DJANGO_ALLOWED_HOSTS": "portfolio.example",
                "DJANGO_CSRF_TRUSTED_ORIGINS": "https://portfolio.example",
                "DATABASE_URL": "postgresql://u:p@localhost:5432/db",
                "PORTFOLIO_DEMO_ENABLED": "0",
            }
        )
        result = settings_snapshot(env)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout.strip())
        self.assertFalse(data["is_vercel"])
        self.assertIn(
            "whitenoise.middleware.WhiteNoiseMiddleware",
            data["middleware"],
        )
        self.assertEqual(
            data["static_backend"],
            "whitenoise.storage.CompressedManifestStaticFilesStorage",
        )
        self.assertEqual(data["conn_max_age"], 600)

    def test_vercel_build_dry_run_prefers_unpooled_database(self):
        env = clean_env()
        env.update(
            {
                "VERCEL": "1",
                "VERCEL_ENV": "preview",
                "VERCEL_BUILD_DRY_RUN": "1",
                "DATABASE_URL": "postgresql://pooled.invalid/db",
                "DATABASE_URL_UNPOOLED": "postgresql://direct.invalid/db",
                "PORTFOLIO_DEMO_ENABLED": "1",
            }
        )
        result = subprocess.run(
            [sys.executable, str(VERCEL_BUILD)],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("directe/non poolée pour migrations", result.stdout)
        self.assertIn("manage.py migrate --noinput", result.stdout)
        self.assertIn("manage.py setup_roles", result.stdout)
        self.assertIn("manage.py bootstrap_portfolio", result.stdout)
        self.assertIn("VERCEL_BUILD_DRY_RUN_OK", result.stdout)

    def test_ci_production_smoke_uses_python_312(self):
        source = CI.read_text(encoding="utf-8")
        production = source.split("production-smoke:", 1)[1]
        self.assertIn('python-version: "3.12"', production)
        self.assertIn("V17.4 Vercel runtime dry-run", production)

    def test_zero_config_has_no_legacy_wrapper(self):
        self.assertFalse((ROOT / "vercel.json").exists())
        self.assertFalse((ROOT / "api" / "index.py").exists())
