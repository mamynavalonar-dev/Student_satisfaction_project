from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.rbac import ROLE_ADMIN, ROLE_USER, assign_role


DEMO_USERNAME = "portfolio-demo-entry-test"
PASSWORD_SENTINEL = "Never-send-this-value-to-the-browser-2026"


@override_settings(
    PORTFOLIO_DEMO_ENABLED=True,
    PORTFOLIO_DEMO_USERNAME=DEMO_USERNAME,
)
class PortfolioDemoEntryV176Tests(TestCase):
    def make_demo(self, role=ROLE_USER):
        user = get_user_model().objects.create_user(
            username=DEMO_USERNAME,
            email="portfolio-demo-entry@example.invalid",
            password=PASSWORD_SENTINEL,
        )
        assign_role(user, role)
        return user

    def test_demo_query_renders_secure_post_handoff(self):
        self.make_demo()

        response = self.client.get(
            reverse("login_register") + "?demo=1"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-demo-autologin")
        self.assertContains(
            response,
            reverse("portfolio_demo_login"),
        )
        self.assertNotContains(response, PASSWORD_SENTINEL)
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_normal_login_page_does_not_autostart_demo(self):
        response = self.client.get(reverse("login_register"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "data-demo-autologin")

    def test_demo_entry_logs_in_prediction_only_user(self):
        demo = self.make_demo()

        response = self.client.post(
            reverse("portfolio_demo_login")
        )

        self.assertRedirects(
            response,
            reverse("home"),
            fetch_redirect_response=False,
        )
        self.assertEqual(
            self.client.session.get("_auth_user_id"),
            str(demo.pk),
        )

    def test_demo_entry_is_post_only(self):
        self.make_demo()

        response = self.client.get(
            reverse("portfolio_demo_login")
        )

        self.assertEqual(response.status_code, 405)

    def test_demo_entry_requires_csrf(self):
        self.make_demo()

        csrf_client = Client(enforce_csrf_checks=True)

        response = csrf_client.post(
            reverse("portfolio_demo_login")
        )

        self.assertEqual(response.status_code, 403)
        self.assertNotIn(
            "_auth_user_id",
            csrf_client.session,
        )

    @override_settings(PORTFOLIO_DEMO_ENABLED=False)
    def test_demo_entry_fails_closed_when_disabled(self):
        self.make_demo()

        response = self.client.post(
            reverse("portfolio_demo_login")
        )

        self.assertRedirects(
            response,
            reverse("login_register"),
            fetch_redirect_response=False,
        )
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_demo_entry_rejects_privileged_account_drift(self):
        self.make_demo(role=ROLE_ADMIN)

        response = self.client.post(
            reverse("portfolio_demo_login")
        )

        self.assertRedirects(
            response,
            reverse("login_register"),
            fetch_redirect_response=False,
        )
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_demo_entry_fails_closed_when_account_is_missing(self):
        response = self.client.post(
            reverse("portfolio_demo_login")
        )

        self.assertRedirects(
            response,
            reverse("login_register"),
            fetch_redirect_response=False,
        )
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )
