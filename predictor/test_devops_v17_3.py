from __future__ import annotations

import hashlib
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


ROOT = Path(settings.BASE_DIR)
CI = ROOT / ".github" / "workflows" / "ci.yml"
DEPLOYMENT = ROOT / "DEPLOYMENT.md"
CHANGELOG = ROOT / "CHANGELOG.md"
VERIFY = ROOT / "scripts" / "verify_release.py"
MODEL = ROOT / "deployment" / "model" / "portfolio_model.joblib"
HASH_FILE = ROOT / "deployment" / "model" / "portfolio_model.sha256"

EXPECTED_MODEL_HASH = (
    "b3e4668f4f02f2f765440cf539fb56376654df4a596503ac60a2ead0d01697d7"
)


class DevOpsV173Tests(SimpleTestCase):
    def test_release_verifier_adds_repository_root_to_python_path(self):
        source = VERIFY.read_text(encoding="utf-8")

        self.assertIn(
            "ROOT = Path(__file__).resolve().parents[1]",
            source,
        )
        self.assertIn(
            "sys.path.insert(0, ROOT_STRING)",
            source,
        )

    def test_required_devops_files_exist(self):
        for path in (
            CI,
            DEPLOYMENT,
            CHANGELOG,
            VERIFY,
            HASH_FILE,
        ):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_model_manifest_matches_packaged_binary(self):
        actual = hashlib.sha256(
            MODEL.read_bytes()
        ).hexdigest()

        manifest = (
            HASH_FILE.read_text(encoding="utf-8")
            .strip()
            .split()[0]
            .lower()
        )

        self.assertEqual(actual, EXPECTED_MODEL_HASH)
        self.assertEqual(manifest, EXPECTED_MODEL_HASH)

    def test_ci_uses_full_sha_pins_for_external_actions(self):
        source = CI.read_text(encoding="utf-8")

        uses = re.findall(
            r"^\s*uses:\s*([^\s#]+)",
            source,
            flags=re.MULTILINE,
        )

        self.assertTrue(uses)

        for action in uses:
            with self.subTest(action=action):
                self.assertRegex(
                    action,
                    r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$",
                )

        self.assertIn(
            "actions/checkout@"
            "3d3c42e5aac5ba805825da76410c181273ba90b1",
            source,
        )
        self.assertIn(
            "actions/setup-python@"
            "5fda3b95a4ea91299a34e894583c3862153e4b97",
            source,
        )

    def test_ci_runs_full_suite_and_release_checks(self):
        source = CI.read_text(encoding="utf-8")

        for token in (
            "python scripts/verify_release.py",
            "python manage.py check",
            "python manage.py makemigrations --check --dry-run",
            "python manage.py test",
            "python manage.py collectstatic --noinput --clear",
            "python manage.py check --deploy --fail-level ERROR",
        ):
            with self.subTest(token=token):
                self.assertIn(token, source)

    def test_ci_has_real_postgresql_production_smoke(self):
        source = CI.read_text(encoding="utf-8")

        for token in (
            "production-smoke:",
            "image: postgres:16",
            "DATABASE_URL:",
            "DJANGO_ENV: production",
            "python manage.py migrate --noinput",
            "python manage.py setup_roles",
            "python manage.py bootstrap_portfolio",
            "CI_ML_SMOKE_OK",
            "CI_HEALTH_OK",
        ):
            with self.subTest(token=token):
                self.assertIn(token, source)

    def test_ci_permissions_are_read_only(self):
        source = CI.read_text(encoding="utf-8")

        self.assertIn(
            "permissions:\n  contents: read",
            source,
        )

    def test_deployment_docs_cover_required_release_sequence(self):
        source = DEPLOYMENT.read_text(encoding="utf-8")

        for token in (
            "DATABASE_URL",
            "DJANGO_SECRET_KEY",
            "PORTFOLIO_DEMO_PASSWORD",
            "python manage.py migrate --noinput",
            "python manage.py setup_roles",
            "python manage.py bootstrap_portfolio",
            "gunicorn student_satisfaction_project.wsgi:application",
            "/health/",
            "python manage.py check",
            "python manage.py test",
        ):
            with self.subTest(token=token):
                self.assertIn(token, source)

    def test_documentation_never_contains_current_private_credentials(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                DEPLOYMENT,
                CHANGELOG,
                ROOT / "README.md",
                ROOT / ".env.example",
            )
        )

        for forbidden in (
            "postgres-ci-password",
            "CI-Portfolio-Only-2026-Quartz",
            "ci-production-simulation-only-9Zp7Kx4Wm2Qr8Nv6",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden,
                    combined,
                )
