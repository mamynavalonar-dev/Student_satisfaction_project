from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


User = get_user_model()


class AccountProfileV14BTests(TestCase):
    def setUp(self):
        self.password = "Ancien!MotDePasse2026x"
        self.user = User.objects.create_user(
            username="profil-v14b",
            email="profil-v14b@example.com",
            password=self.password,
            first_name="Jean",
            last_name="Test",
        )

    def test_profile_requires_authentication(self):
        response = self.client.get(reverse("accounts:profile"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login_register"), response["Location"])

    def test_profile_page_displays_identity_and_security_actions(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("accounts:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.username)
        self.assertContains(response, self.user.email)
        self.assertContains(response, reverse("accounts:profile_edit"))
        self.assertContains(response, reverse("accounts:password_change"))

    def test_profile_updates_first_and_last_name(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:profile_edit"),
            {
                "first_name": "Jeanne",
                "last_name": "Validation",
                "email": self.user.email,
                "current_password": "",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Jeanne")
        self.assertEqual(self.user.last_name, "Validation")

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(
            username="autre-v14b",
            email="duplicate@example.com",
            password="Autre!MotDePasse2026x",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:profile_edit"),
            {
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
                "email": "DUPLICATE@example.com",
                "current_password": self.password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Cette adresse e-mail est déjà utilisée",
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "profil-v14b@example.com")

    def test_email_change_requires_current_password(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:profile_edit"),
            {
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
                "email": "nouveau@example.com",
                "current_password": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Saisissez votre mot de passe actuel",
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "profil-v14b@example.com")

    def test_email_change_with_correct_password_succeeds(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:profile_edit"),
            {
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
                "email": "nouveau@example.com",
                "current_password": self.password,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "nouveau@example.com")

    def test_password_change_works_and_keeps_current_session(self):
        self.client.force_login(self.user)
        new_password = "Nouveau!MotDePasse2026x"

        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": self.password,
                "new_password1": new_password,
                "new_password2": new_password,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

        profile_response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(profile_response.status_code, 200)

    def test_password_change_rejects_wrong_current_password(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "Incorrect!2026x",
                "new_password1": "Nouveau!MotDePasse2026x",
                "new_password2": "Nouveau!MotDePasse2026x",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "incorrect")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.password))

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    )
    def test_password_reset_known_email_sends_one_message(self):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": self.user.email},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Réinitialisation", mail.outbox[0].subject)
        self.assertIn("/account/password/reset/", mail.outbox[0].body)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    )
    def test_password_reset_unknown_email_is_generic_and_sends_nothing(self):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": "inconnu@example.com"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Si un compte actif correspond")
        self.assertEqual(len(mail.outbox), 0)

    def test_login_page_links_to_password_reset(self):
        response = self.client.get(reverse("login_register"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("accounts:password_reset"))
        self.assertContains(response, "Mot de passe oublié")
