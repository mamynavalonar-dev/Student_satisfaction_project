from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.rbac import ensure_roles_and_permissions


User = get_user_model()


class ResidualEnglishI18nV14C27Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_roles_and_permissions()

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="residual-i18n-root",
            email="residual-i18n-root@example.com",
            password="Residual!I18n-2026x",
        )
        self.client.force_login(self.user)
        self.client.post(
            reverse("set_language"),
            {"language": "en", "next": reverse("home")},
        )

    def test_residual_runtime_asset_is_loaded(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "ux/i18n_residuals.js")
        self.assertContains(response, "ux/i18n_residuals.css")

    def test_runtime_asset_contains_visible_residual_mappings(self):
        from django.conf import settings

        path = settings.BASE_DIR / "static" / "ux" / "i18n_residuals.js"
        content = path.read_text(encoding="utf-8")

        for source, target in (
            ("Données", "Data"),
            ("Présentiel", "In person"),
            ("Distanciel", "Online"),
            ("Hybride", "Hybrid"),
            ("Fichier joblib introuvable.", "Joblib file not found."),
            ("Taux satisfait prédit (%)", "Predicted satisfaction rate (%)"),
        ):
            self.assertIn(source, content)
            self.assertIn(target, content)

    def test_runtime_asset_handles_dynamic_charts_and_file_inputs(self):
        from django.conf import settings

        path = settings.BASE_DIR / "static" / "ux" / "i18n_residuals.js"
        content = path.read_text(encoding="utf-8")

        self.assertIn("Chart.instances", content)
        self.assertIn("enhanceFileInputs", content)
        self.assertIn("MutationObserver", content)

    def test_french_mode_keeps_server_language(self):
        self.client.post(
            reverse("set_language"),
            {"language": "fr", "next": reverse("home")},
        )
        response = self.client.get(reverse("home"))

        self.assertContains(response, 'lang="fr"')
        self.assertContains(response, "Satisfaction")
