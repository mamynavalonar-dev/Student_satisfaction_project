from __future__ import annotations

from django.test import SimpleTestCase

from student_satisfaction_project.i18n_residual_middleware import (
    translate_residual_text,
)


class LoginToastV14C220Tests(SimpleTestCase):
    def test_full_french_toast(self):
        self.assertEqual(
            translate_residual_text(
                "Connexion réussie. Bon retour, admindev."
            ),
            "Login successful. Welcome back, admindev.",
        )

    def test_partially_translated_toast(self):
        self.assertEqual(
            translate_residual_text(
                "Login successful. Bon retour, admindev."
            ),
            "Login successful. Welcome back, admindev.",
        )

    def test_usernames_are_preserved_exactly(self):
        usernames = (
            "admin",
            "admindev",
            "student26",
            "john_smith",
            "john-smith",
            "john.smith",
            "john+test",
            "john@example",
        )

        for username in usernames:
            with self.subTest(username=username):
                self.assertEqual(
                    translate_residual_text(
                        "Connexion réussie. "
                        f"Bon retour, {username}."
                    ),
                    (
                        "Login successful. Welcome back, "
                        f"{username}."
                    ),
                )

    def test_notification_title_alone(self):
        self.assertEqual(
            translate_residual_text("Connexion réussie"),
            "Login successful",
        )

    def test_notification_message_from_v14c216_still_works(self):
        self.assertEqual(
            translate_residual_text(
                "Bienvenue admindev. Votre session est active."
            ),
            "Welcome admindev. Your session is active.",
        )
