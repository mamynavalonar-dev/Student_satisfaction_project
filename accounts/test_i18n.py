from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .rbac import (
    ROLE_ANALYST,
    ROLE_USER,
    assign_role,
    ensure_roles_and_permissions,
)


User = get_user_model()


class InternationalizationV14C1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_roles_and_permissions()

    def setUp(self):
        self.root = User.objects.create_superuser(
            username="i18n-root",
            email="i18n-root@example.com",
            password="I18n!Root-2026x",
        )
        self.user = User.objects.create_user(
            username="i18n-user",
            email="i18n-user@example.com",
            password="I18n!User-2026x",
        )
        assign_role(self.user, ROLE_USER)

    def switch_language(self, code, next_url="/dashboard/"):
        return self.client.post(
            reverse("set_language"),
            {"language": code, "next": next_url},
        )

    def test_default_language_is_french(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse("accounts:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mon profil")
        self.assertContains(response, 'value="fr"')
        self.assertContains(response, 'value="en"')

    def test_language_switch_to_english_persists(self):
        self.client.force_login(self.root)
        response = self.switch_language("en", reverse("accounts:profile"))

        self.assertEqual(response.status_code, 302)

        profile = self.client.get(reverse("accounts:profile"))
        self.assertContains(profile, "My profile")
        self.assertContains(profile, "Personal information")
        self.assertContains(profile, 'lang="en"')

        dashboard = self.client.get(reverse("home"))
        self.assertContains(dashboard, ">Home<")
        self.assertContains(dashboard, ">Prediction<")

    def test_can_switch_back_to_french(self):
        self.client.force_login(self.root)
        self.switch_language("en")
        self.switch_language("fr")

        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, "Mon profil")
        self.assertContains(response, 'lang="fr"')

    def test_super_admin_role_badge_is_translated(self):
        self.client.force_login(self.root)
        self.switch_language("en")

        response = self.client.get(reverse("home"))
        self.assertContains(response, "Super Administrator")

    def test_user_management_translates_roles_and_actions(self):
        self.client.force_login(self.root)
        self.switch_language("en")

        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User management")
        self.assertContains(response, "New account")
        self.assertContains(response, "Administrator")
        self.assertContains(response, "ML Manager")
        self.assertContains(response, "Analyst")
        self.assertContains(response, ">User<")

    def test_password_change_page_is_translated(self):
        self.client.force_login(self.root)
        self.switch_language("en")

        response = self.client.get(reverse("accounts:password_change"))
        self.assertContains(response, "Change password")
        self.assertContains(response, "Back to profile")

    def test_language_control_is_accessible(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse("home"))

        self.assertContains(response, 'class="app-locale-switch"')
        self.assertContains(response, 'aria-label="Langue"')
        self.assertContains(response, 'aria-pressed="true"')

    def test_theme_script_uses_server_i18n_dictionary(self):
        from django.conf import settings

        path = (
            settings.BASE_DIR
            / "static"
            / "ux"
            / "theme_accessibility.js"
        )
        content = path.read_text(encoding="utf-8")

        self.assertIn("window.APP_I18N", content)
        self.assertIn("ui.themeAuto", content)
        self.assertIn("changeTheme", content)
