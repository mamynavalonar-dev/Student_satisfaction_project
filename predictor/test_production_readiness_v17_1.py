from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


ROOT = Path(settings.BASE_DIR)


def _clean_env():
    env = os.environ.copy()

    for name in (
        "DJANGO_ENV",
        "DJANGO_DEBUG",
        "DJANGO_SECRET_KEY",
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "DATABASE_URL",
        "DJANGO_SECURE_SSL_REDIRECT",
        "DJANGO_TRUST_X_FORWARDED_PROTO",
        "DJANGO_HSTS_SECONDS",
        "DJANGO_HSTS_INCLUDE_SUBDOMAINS",
        "DJANGO_HSTS_PRELOAD",
    ):
        env.pop(name, None)

    env["DJANGO_SETTINGS_MODULE"] = (
        "student_satisfaction_project.settings"
    )
    return env


def _settings_snapshot(env):
    code = (
        "import json\n"
        "from django.conf import settings\n"
        "print(json.dumps({"
        "'production': settings.IS_PRODUCTION,"
        "'debug': settings.DEBUG,"
        "'engine': settings.DATABASES['default']['ENGINE'],"
        "'middleware': settings.MIDDLEWARE,"
        "'static_backend': settings.STORAGES['staticfiles']['BACKEND'],"
        "'ssl_redirect': settings.SECURE_SSL_REDIRECT,"
        "'session_secure': settings.SESSION_COOKIE_SECURE,"
        "'csrf_secure': settings.CSRF_COOKIE_SECURE"
        "}))\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    return result


class ProductionReadinessV1711Tests(SimpleTestCase):
    def test_test_runner_environment_is_not_used_to_infer_dev_debug(self):
        # Django's test runner forces DEBUG=False. The actual development
        # default is therefore verified in a clean subprocess below.
        self.assertFalse(settings.IS_PRODUCTION)

    def test_clean_process_keeps_local_development_defaults(self):
        result = _settings_snapshot(_clean_env())

        self.assertEqual(
            result.returncode,
            0,
            msg=result.stderr,
        )

        payload = json.loads(result.stdout.strip())

        self.assertFalse(payload["production"])
        self.assertTrue(payload["debug"])
        self.assertEqual(
            payload["engine"],
            "django.db.backends.sqlite3",
        )
        self.assertEqual(
            payload["static_backend"],
            "django.contrib.staticfiles.storage.StaticFilesStorage",
        )
        self.assertNotIn(
            "whitenoise.middleware.WhiteNoiseMiddleware",
            payload["middleware"],
        )

    def test_required_production_dependencies_are_pinned(self):
        requirements = (ROOT / "requirements.txt").read_text(
            encoding="utf-8"
        )

        for dependency in (
            "gunicorn==26.1.0",
            "whitenoise==6.12.0",
            "dj-database-url==3.1.2",
            "psycopg[binary]==3.3.4",
        ):
            with self.subTest(dependency=dependency):
                self.assertIn(
                    dependency,
                    requirements,
                )

    def test_env_example_contains_no_local_secret_fallback(self):
        source = (ROOT / ".env.example").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "DJANGO_ENV=development",
            source,
        )
        self.assertIn(
            "DATABASE_URL=",
            source,
        )
        self.assertNotIn(
            "django-insecure-local-development-only-change-me",
            source,
        )

    def test_production_configuration_is_fail_closed_and_postgresql(self):
        env = _clean_env()
        env.update(
            {
                "DJANGO_ENV": "production",
                "DJANGO_DEBUG": "0",
                "DJANGO_SECRET_KEY": "prod-test-" + ("x7A_" * 30),
                "DJANGO_ALLOWED_HOSTS": "portfolio.example",
                "DJANGO_CSRF_TRUSTED_ORIGINS":
                    "https://portfolio.example",
                "DATABASE_URL":
                    "postgresql://student:password@localhost:5432/studentdb",
                "DJANGO_SECURE_SSL_REDIRECT": "1",
                "DJANGO_HSTS_SECONDS": "3600",
            }
        )

        result = _settings_snapshot(env)

        self.assertEqual(
            result.returncode,
            0,
            msg=result.stderr,
        )

        payload = json.loads(result.stdout.strip())

        self.assertTrue(payload["production"])
        self.assertFalse(payload["debug"])
        self.assertEqual(
            payload["engine"],
            "django.db.backends.postgresql",
        )
        self.assertTrue(payload["ssl_redirect"])
        self.assertTrue(payload["session_secure"])
        self.assertTrue(payload["csrf_secure"])
        self.assertEqual(
            payload["static_backend"],
            "whitenoise.storage.CompressedManifestStaticFilesStorage",
        )

        middleware = payload["middleware"]
        security_index = middleware.index(
            "django.middleware.security.SecurityMiddleware"
        )
        self.assertEqual(
            middleware[security_index + 1],
            "whitenoise.middleware.WhiteNoiseMiddleware",
        )

    def test_production_without_secret_refuses_to_start(self):
        env = _clean_env()
        env.update(
            {
                "DJANGO_ENV": "production",
                "DJANGO_DEBUG": "0",
            }
        )

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import student_satisfaction_project.settings",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(
            result.returncode,
            0,
        )
        self.assertIn(
            "DJANGO_SECRET_KEY",
            result.stderr + result.stdout,
        )


class HealthEndpointV1711Tests(TestCase):
    def test_health_returns_ok_when_database_is_ready(self):
        response = self.client.get(
            reverse("health")
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertJSONEqual(
            response.content,
            {"status": "ok"},
        )
        self.assertEqual(
            response["Cache-Control"],
            "no-store",
        )

    @patch(
        "student_satisfaction_project.health._database_ready",
        return_value=False,
    )
    def test_health_returns_503_without_leaking_details(
        self,
        mocked_ready,
    ):
        response = self.client.get(
            reverse("health")
        )

        self.assertEqual(
            response.status_code,
            503,
        )
        self.assertJSONEqual(
            response.content,
            {"status": "unavailable"},
        )
        mocked_ready.assert_called_once_with()
