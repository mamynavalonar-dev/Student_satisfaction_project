from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import StudentFeedback


class DataManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="mot-de-passe-test")
        self.feedback_satisfied = StudentFeedback.objects.create(
            qualite_enseignement=6,
            charge_travail=4,
            interactivite=6,
            type_cours="présentiel",
            niveau_etudiant="L1",
            predicted_satisfaction=True,
            probability_satisfied=88.0,
        )
        self.feedback_unsatisfied = StudentFeedback.objects.create(
            qualite_enseignement=2,
            charge_travail=7,
            interactivite=2,
            type_cours="distanciel",
            niveau_etudiant="L2",
            predicted_satisfaction=False,
            probability_satisfied=12.0,
        )

    def test_data_management_requires_authentication(self):
        response = self.client.get(reverse("data_management"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login_register"), response.url)

    def test_server_side_status_filter(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("data_management"), {"status": "satisfied"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result_count"], 1)

        displayed_ids = [
            feedback.id
            for feedback in response.context["feedbacks"]
        ]
        self.assertIn(self.feedback_satisfied.id, displayed_ids)
        self.assertNotIn(self.feedback_unsatisfied.id, displayed_ids)

        # Vérifie aussi que l'indicateur animé est positionné sur "Données".
        self.assertContains(response, 'animated-nav page-data')

    def test_server_side_search_by_id(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("data_management"),
            {"q": f"#{self.feedback_unsatisfied.id}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result_count"], 1)
        self.assertContains(response, f"#{self.feedback_unsatisfied.id}")

    def test_feedback_detail_returns_real_values_including_zero_probability(self):
        self.feedback_unsatisfied.probability_satisfied = 0.0
        self.feedback_unsatisfied.save(update_fields=["probability_satisfied"])

        self.client.force_login(self.user)
        response = self.client.get(
            reverse("feedback_detail", args=[self.feedback_unsatisfied.id])
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], self.feedback_unsatisfied.id)
        self.assertEqual(payload["qualite_enseignement"], 2)
        self.assertEqual(payload["probability_satisfied"], 0.0)
        self.assertEqual(payload["prediction_label"], "Non satisfait")

    @patch("predictor.views.predict_satisfaction")
    @patch("predictor.views.load_current_model")
    def test_feedback_update_recalculates_prediction(
        self,
        mocked_load_current_model,
        mocked_predict_satisfaction,
    ):
        mocked_load_current_model.return_value = {"schema_version": 2}
        mocked_predict_satisfaction.return_value = {
            "prediction": 1,
            "probability_satisfied": 91.5,
        }

        self.client.force_login(self.user)
        response = self.client.post(
            reverse("feedback_update", args=[self.feedback_unsatisfied.id]),
            {
                "qualite_enseignement": "7",
                "charge_travail": "3",
                "interactivite": "7",
                "type_cours": "hybride",
                "niveau_etudiant": "L3",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.feedback_unsatisfied.refresh_from_db()
        self.assertEqual(self.feedback_unsatisfied.qualite_enseignement, 7)
        self.assertEqual(self.feedback_unsatisfied.type_cours, "hybride")
        self.assertTrue(self.feedback_unsatisfied.predicted_satisfaction)
        self.assertEqual(self.feedback_unsatisfied.probability_satisfied, 91.5)

    def test_feedback_delete_accepts_post_and_removes_row(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("feedback_delete", args=[self.feedback_unsatisfied.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            StudentFeedback.objects.filter(pk=self.feedback_unsatisfied.id).exists()
        )

    def test_feedback_delete_rejects_get(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("feedback_delete", args=[self.feedback_satisfied.id])
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(
            StudentFeedback.objects.filter(pk=self.feedback_satisfied.id).exists()
        )

    def test_export_respects_current_filters(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("export_data"), {"status": "satisfied"})

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8-sig")
        self.assertIn(str(self.feedback_satisfied.id), content)
        self.assertNotIn(f"{self.feedback_unsatisfied.id},", content)

class StatisticsDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="stats-tester", password="mot-de-passe-test")
        rows = [
            (1, 7, 1, "distanciel", "L1", False, 10.0),
            (1, 6, 2, "distanciel", "L1", False, 20.0),
            (7, 2, 7, "présentiel", "L3", True, 90.0),
            (7, 3, 6, "hybride", "L3", True, 80.0),
        ]
        for quality, workload, interactivity, course_type, level, prediction, probability in rows:
            StudentFeedback.objects.create(
                qualite_enseignement=quality,
                charge_travail=workload,
                interactivite=interactivity,
                type_cours=course_type,
                niveau_etudiant=level,
                predicted_satisfaction=prediction,
                probability_satisfied=probability,
            )

    @patch("predictor.views.load_current_model")
    def test_statistics_are_computed_from_database(self, mocked_load_current_model):
        mocked_load_current_model.return_value = None
        self.client.force_login(self.user)
        response = self.client.get(reverse("statistics"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stats"]["total"], 4)
        self.assertEqual(response.context["stats"]["satisfied"], 2)
        self.assertEqual(response.context["stats"]["unsatisfied"], 2)
        self.assertEqual(response.context["stats"]["satisfaction_rate"], 50.0)
        self.assertAlmostEqual(response.context["stats"]["average_probability"], 50.0)

    @patch("predictor.views.load_current_model")
    def test_associations_are_dynamic_not_static_examples(self, mocked_load_current_model):
        mocked_load_current_model.return_value = None
        self.client.force_login(self.user)
        response = self.client.get(reverse("statistics"))

        factors = {item["key"]: item for item in response.context["association_factors"]}
        self.assertEqual(factors["quality"]["spread"], 100.0)
        self.assertNotContains(response, "Facteurs d'Impact (Exemple)")
        self.assertContains(response, "Associations observées")
        self.assertContains(response, 'id="charts-data"')

    @patch("predictor.views.load_current_model")
    def test_home_uses_same_statistics_and_model_metrics(self, mocked_load_current_model):
        mocked_load_current_model.return_value = {
            "schema_version": 2,
            "metrics": {
                "accuracy": 0.91,
                "precision": 0.90,
                "recall": 0.89,
                "f1": 0.88,
                "dataset_size": 100,
                "train_size": 80,
                "test_size": 20,
            },
        }
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_feedbacks"], 4)
        self.assertEqual(response.context["satisfied_count"], 2)
        self.assertEqual(response.context["unsatisfied_count"], 2)
        self.assertEqual(response.context["satisfaction_rate"], 50.0)
        self.assertEqual(response.context["active_model"]["accuracy"], 91.0)
        self.assertEqual(response.context["active_model"]["f1"], 88.0)

    @patch("predictor.views.load_current_model")
    def test_navigation_is_responsive_and_not_hardcoded_to_590px(self, mocked_load_current_model):
        mocked_load_current_model.return_value = None
        self.client.force_login(self.user)
        response = self.client.get(reverse("statistics"))

        self.assertContains(response, "data-animated-nav")
        self.assertContains(response, "grid-template-columns")
        self.assertNotContains(response, "width: 590px")
        self.assertContains(response, "animated-nav page-stats")



class AuthenticationTests(TestCase):
    def setUp(self):
        self.login_url = reverse("login_register")
        self.valid_password = "ProjetIA-2026!Solide"

    def test_auth_page_is_responsive_and_has_no_legacy_jquery_dependencies(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-auth-card')
        self.assertContains(response, 'auth/st-inscr.css')
        self.assertContains(response, 'auth/app.js')
        self.assertNotContains(response, 'jquery-3.7.1.min.js')
        self.assertNotContains(response, 'auth/css/animate.min.css')

    def test_registration_rejects_weak_password(self):
        response = self.client.post(
            self.login_url,
            {
                "form_type": "register",
                "register-username": "faible",
                "register-email": "faible@example.com",
                "register-password1": "123",
                "register-password2": "123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="faible").exists())
        self.assertTrue(response.context["register_form"].errors)
        self.assertEqual(response.context["active_panel"], "register")

    def test_registration_rejects_password_mismatch(self):
        response = self.client.post(
            self.login_url,
            {
                "form_type": "register",
                "register-username": "mismatch",
                "register-email": "mismatch@example.com",
                "register-password1": self.valid_password,
                "register-password2": self.valid_password + "X",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="mismatch").exists())
        self.assertTrue(response.context["register_form"].errors)

    def test_registration_creates_user_and_logs_in(self):
        response = self.client.post(
            self.login_url,
            {
                "form_type": "register",
                "register-username": "nouveau",
                "register-email": "nouveau@example.com",
                "register-password1": self.valid_password,
                "register-password2": self.valid_password,
            },
        )
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(username="nouveau").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(
            username="existant",
            email="test@example.com",
            password=self.valid_password,
        )
        response = self.client.post(
            self.login_url,
            {
                "form_type": "register",
                "register-username": "autre",
                "register-email": "TEST@example.com",
                "register-password1": self.valid_password,
                "register-password2": self.valid_password,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="autre").exists())
        self.assertIn("email", response.context["register_form"].errors)

    def test_login_then_logout_requires_post(self):
        User.objects.create_user(
            username="connexion",
            email="connexion@example.com",
            password=self.valid_password,
        )
        response = self.client.post(
            self.login_url,
            {
                "form_type": "login",
                "login-username": "connexion",
                "login-password": self.valid_password,
            },
        )
        self.assertRedirects(response, reverse("home"))
        self.assertIn("_auth_user_id", self.client.session)

        get_response = self.client.get(reverse("logout"))
        self.assertEqual(get_response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

        post_response = self.client.post(reverse("logout"))
        self.assertRedirects(post_response, reverse("login_register"))
        self.assertNotIn("_auth_user_id", self.client.session)

class PredictionTrainingUxTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.user = get_user_model().objects.create_user(
            username="ux-validator",
            email="ux-validator@example.com",
            password="UxValidation123!",
        )
        self.client.force_login(self.user)

    def test_prediction_keeps_submitted_values_and_valid_css_width(self):
        from unittest.mock import patch
        from django.urls import reverse

        payload = {
            "qualite_enseignement": "7",
            "charge_travail": "4",
            "interactivite": "7",
            "type_cours": "présentiel",
            "niveau_etudiant": "L3",
        }

        result = {
            "prediction": 1,
            "satisfaction_text": "Satisfait",
            "prediction_probability": 85.8,
            "probability_satisfied": 85.8,
            "probability_unsatisfied": 14.2,
        }

        with (
            patch(
                "predictor.views.load_current_model",
                return_value={"schema_version": 2},
            ),
            patch(
                "predictor.views.predict_satisfaction",
                return_value=result,
            ),
        ):
            response = self.client.post(reverse("predict"), payload)

        self.assertEqual(response.status_code, 200)

        form = response.context["form"]
        self.assertTrue(form.is_bound)
        self.assertEqual(str(form["qualite_enseignement"].value()), "7")
        self.assertEqual(str(form["charge_travail"].value()), "4")
        self.assertEqual(str(form["interactivite"].value()), "7")
        self.assertEqual(form["type_cours"].value(), "présentiel")
        self.assertEqual(form["niveau_etudiant"].value(), "L3")

        html = response.content.decode("utf-8")

        self.assertIn("Confiance", html)

        # widthratio arrondit 85.8 vers un entier CSS sûr.
        self.assertIn('style="width: 86%;"', html)
        self.assertNotIn('style="width: 85,8%;"', html)

    def test_training_chart_is_oldest_to_newest_while_table_is_newest_first(self):
        import json
        from datetime import timedelta
        from unittest.mock import patch

        from django.urls import reverse
        from django.utils import timezone

        from .models import ModelTraining

        now = timezone.now()

        older = ModelTraining.objects.create(
            accuracy=0.61,
            dataset_size=100,
            model_file="older.joblib",
            notes="ancien",
            is_active=False,
        )
        middle = ModelTraining.objects.create(
            accuracy=0.72,
            dataset_size=100,
            model_file="middle.joblib",
            notes="milieu",
            is_active=False,
        )
        newest = ModelTraining.objects.create(
            accuracy=0.83,
            dataset_size=100,
            model_file="newest.joblib",
            notes="récent",
            is_active=True,
        )

        ModelTraining.objects.filter(pk=older.pk).update(
            training_date=now - timedelta(days=2)
        )
        ModelTraining.objects.filter(pk=middle.pk).update(
            training_date=now - timedelta(days=1)
        )
        ModelTraining.objects.filter(pk=newest.pk).update(
            training_date=now
        )

        with patch("predictor.views.load_current_model", return_value=None):
            response = self.client.get(reverse("train_model"))

        self.assertEqual(response.status_code, 200)

        table_trainings = list(response.context["trainings"])

        self.assertEqual(
            [item.pk for item in table_trainings[:3]],
            [newest.pk, middle.pk, older.pk],
        )

        history = json.loads(response.context["training_history"])

        self.assertEqual(
            history["accuracies"][-3:],
            [61.0, 72.0, 83.0],
        )

class NotificationCenterTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.urls import reverse

        self.reverse = reverse
        self.password = "Notif-2026!Solide"
        self.user = get_user_model().objects.create_user(
            username="notif-user",
            email="notif@example.com",
            password=self.password,
        )

    def test_auth_page_has_visibility_toggles(self):
        response = self.client.get(self.reverse("login_register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-visibility-target="id_login-username"')
        self.assertContains(response, 'data-visibility-target="id_login-password"')
        self.assertContains(response, "auth-visibility-toggle")

    def test_logout_message_is_consumed_on_auth_page(self):
        self.client.force_login(self.user)

        # Suivre la redirection une seule fois et vérifier le message
        # sur la vraie page de connexion obtenue après déconnexion.
        auth_response = self.client.post(
            self.reverse("logout"),
            follow=True,
        )

        self.assertEqual(auth_response.status_code, 200)
        self.assertEqual(
            auth_response.redirect_chain[-1][0],
            self.reverse("login_register"),
        )
        self.assertContains(
            auth_response,
            "Vous avez été déconnecté avec succès.",
        )

        # Le message a maintenant été rendu/consommé. Après reconnexion,
        # il ne doit donc plus réapparaître sur le dashboard.
        login_response = self.client.post(
            self.reverse("login_register"),
            {
                "form_type": "login",
                "login-username": self.user.username,
                "login-password": self.password,
            },
            follow=True,
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertNotContains(
            login_response,
            "Vous avez été déconnecté avec succès.",
        )

    def test_successful_login_creates_notification(self):
        from .models import Notification

        response = self.client.post(
            self.reverse("login_register"),
            {
                "form_type": "login",
                "login-username": self.user.username,
                "login-password": self.password,
            },
        )
        self.assertRedirects(response, self.reverse("home"))
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                event_type="auth",
                title="Connexion réussie",
            ).exists()
        )

    def test_notification_feed_and_mark_read(self):
        from .models import Notification

        self.client.force_login(self.user)
        notification = Notification.objects.create(
            user=self.user,
            title="Test",
            message="Notification de test",
            level="info",
            event_type="system",
        )

        feed = self.client.get(self.reverse("notifications_feed"))
        self.assertEqual(feed.status_code, 200)
        payload = feed.json()
        self.assertEqual(payload["unread_count"], 1)
        self.assertEqual(payload["notifications"][0]["id"], notification.id)

        marked = self.client.post(self.reverse("notification_mark_read", args=[notification.id]))
        self.assertEqual(marked.status_code, 200)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_mark_all_notifications_as_read(self):
        from .models import Notification

        self.client.force_login(self.user)
        Notification.objects.create(user=self.user, title="A", message="A")
        Notification.objects.create(user=self.user, title="B", message="B")
        response = self.client.post(self.reverse("notifications_mark_all_read"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)

    def test_authenticated_topbar_contains_notification_center(self):
        self.client.force_login(self.user)
        response = self.client.get(self.reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-notification-center")
        self.assertContains(response, "data-notification-badge")
        self.assertContains(response, "data-notification-panel")



class AuthEyeCssRegressionTests(TestCase):
    def test_auth_eye_hidden_state_is_forced_by_css(self):
        from pathlib import Path
        from django.conf import settings

        css_path = Path(settings.BASE_DIR) / "static" / "auth" / "st-inscr.css"
        css = css_path.read_text(encoding="utf-8")

        self.assertIn(".auth-eye[hidden]", css)
        self.assertIn("display: none !important;", css)


class AuthEyeToggleRegressionTests(TestCase):
    def test_auth_eye_icons_follow_the_action_semantics(self):
        from pathlib import Path
        from django.conf import settings

        js_path = Path(settings.BASE_DIR) / "static" / "auth" / "app.js"
        js = js_path.read_text(encoding="utf-8")

        self.assertIn(
            "if (openIcon) openIcon.hidden = visible;",
            js,
        )
        self.assertIn(
            "if (closedIcon) closedIcon.hidden = !visible;",
            js,
        )


class AuthEyeDynamicRegressionTests(TestCase):
    def test_dynamic_eye_renderer_contains_open_and_closed_states(self):
        from pathlib import Path
        from django.conf import settings

        js_path = Path(settings.BASE_DIR) / "static" / "auth" / "app.js"
        js = js_path.read_text(encoding="utf-8")

        self.assertIn("V6.4 — rendu robuste de l'icône show/hide", js)
        self.assertIn("const OPEN_EYE", js)
        self.assertIn("const CLOSED_EYE", js)
        self.assertIn("button.innerHTML = visible ? CLOSED_EYE : OPEN_EYE;", js)
        self.assertIn("requestAnimationFrame(() => renderIcon(button, input))", js)

class FinalStatisticsRegressionTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.user = get_user_model().objects.create_user(
            username="final-stats-validator",
            email="final-stats-validator@example.com",
            password="FinalStats123!",
        )
        self.client.force_login(self.user)

    def test_home_average_confidence_uses_predicted_class(self):
        from unittest.mock import patch
        from django.urls import reverse

        StudentFeedback.objects.create(
            qualite_enseignement=7,
            charge_travail=4,
            interactivite=7,
            type_cours="présentiel",
            niveau_etudiant="L3",
            predicted_satisfaction=True,
            probability_satisfied=80.0,
        )

        StudentFeedback.objects.create(
            qualite_enseignement=1,
            charge_travail=7,
            interactivite=1,
            type_cours="distanciel",
            niveau_etudiant="L1",
            predicted_satisfaction=False,
            probability_satisfied=10.0,
        )

        with patch("predictor.views.load_current_model", return_value=None):
            response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertAlmostEqual(
            response.context["average_confidence"],
            85.0,
            places=6,
        )
        self.assertNotIn("average_probability", response.context)

    def test_statistics_warn_when_sample_is_small(self):
        from unittest.mock import patch
        from django.urls import reverse

        StudentFeedback.objects.create(
            qualite_enseignement=4,
            charge_travail=4,
            interactivite=4,
            type_cours="hybride",
            niveau_etudiant="L2",
            predicted_satisfaction=False,
            probability_satisfied=42.0,
        )

        with patch("predictor.views.load_current_model", return_value=None):
            response = self.client.get(reverse("statistics"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Échantillon encore limité")
        self.assertContains(response, "pas comme des conclusions générales")

    def test_data_table_names_probability_satisfied_explicitly(self):
        from django.urls import reverse

        response = self.client.get(reverse("data_management"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Probabilité satisfait")

class ComplianceV8Tests(TestCase):
    @staticmethod
    def _load_generator():
        import importlib.util
        from pathlib import Path

        from django.conf import settings

        generator_path = Path(settings.BASE_DIR) / "generate_synthetic_data.py"
        spec = importlib.util.spec_from_file_location(
            "student_satisfaction_generate_synthetic_data",
            generator_path,
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_prediction_form_and_model_support_m1_m2(self):
        from .forms import PredictionForm
        from .models import StudentFeedback

        form_levels = {value for value, _label in PredictionForm.NIVEAU_CHOICES}
        model_levels = {value for value, _label in StudentFeedback.NIVEAU_CHOICES}

        self.assertEqual(form_levels, {"L1", "L2", "L3", "M1", "M2"})
        self.assertEqual(model_levels, {"L1", "L2", "L3", "M1", "M2"})

    def test_synthetic_generator_is_reproducible_and_covers_all_levels(self):
        generator = self._load_generator()

        first = generator.generate_dataset(rows=120, seed=42)
        second = generator.generate_dataset(rows=120, seed=42)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 120)
        self.assertEqual(
            {row["niveau_etudiant"] for row in first},
            {"L1", "L2", "L3", "M1", "M2"},
        )
        self.assertEqual({row["satisfaction"] for row in first}, {0, 1})
        self.assertEqual(
            len(
                {
                    (
                        row["qualite_enseignement"],
                        row["charge_travail"],
                        row["interactivite"],
                        row["type_cours"],
                        row["niveau_etudiant"],
                    )
                    for row in first
                }
            ),
            120,
        )

    def test_training_validation_accepts_master_levels_and_rejects_invalid_score(self):
        import pandas as pd

        from .neural_network_model import validate_training_dataframe

        generator = self._load_generator()
        frame = pd.DataFrame(generator.generate_dataset(rows=120, seed=7))

        validated = validate_training_dataframe(frame)
        self.assertTrue({"M1", "M2"}.issubset(set(validated["niveau_etudiant"])))

        invalid = frame.copy()
        invalid.loc[0, "qualite_enseignement"] = 8

        with self.assertRaises(ValueError):
            validate_training_dataframe(invalid)

    def test_real_training_creates_pipeline_artifact_and_metrics(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import joblib
        import pandas as pd

        from .neural_network_model import train_model

        generator = self._load_generator()
        frame = pd.DataFrame(generator.generate_dataset(rows=120, seed=99))

        with tempfile.TemporaryDirectory() as tmp:
            fake_base = Path(tmp)
            fake_model_dir = fake_base / "model_artifacts"

            with (
                patch("predictor.neural_network_model.BASE_DIR", fake_base),
                patch("predictor.neural_network_model.MODEL_DIR", fake_model_dir),
            ):
                accuracy, relative_path, metrics = train_model(frame)

            artifact_path = fake_base / relative_path
            self.assertTrue(artifact_path.is_file())

            artifact = joblib.load(artifact_path)
            self.assertEqual(artifact["schema_version"], 2)
            self.assertIn("pipeline", artifact)
            self.assertIn("preprocessor", artifact["pipeline"].named_steps)
            self.assertIn("classifier", artifact["pipeline"].named_steps)

            self.assertGreaterEqual(accuracy, 0.0)
            self.assertLessEqual(accuracy, 1.0)
            self.assertEqual(metrics["dataset_size"], 120)
            self.assertEqual(metrics["train_size"] + metrics["test_size"], 120)
            self.assertIn("precision", metrics)
            self.assertIn("recall", metrics)
            self.assertIn("f1", metrics)
            self.assertIn("confusion_matrix", metrics)

    def test_internal_training_failure_is_not_reported_as_invalid_csv(self):
        import pandas as pd
        from unittest.mock import patch

        from .neural_network_model import train_model

        generator = self._load_generator()
        frame = pd.DataFrame(generator.generate_dataset(rows=80, seed=11))

        with patch(
            "predictor.neural_network_model._build_pipeline",
            side_effect=RuntimeError("panne simulée"),
        ):
            with self.assertRaises(RuntimeError):
                train_model(frame)

    def test_database_constraints_reject_invalid_scores_probability_and_level(self):
        from django.db import IntegrityError, transaction

        valid = {
            "qualite_enseignement": 4,
            "charge_travail": 4,
            "interactivite": 4,
            "type_cours": "hybride",
            "niveau_etudiant": "M2",
            "predicted_satisfaction": True,
            "probability_satisfied": 75.0,
        }

        feedback = StudentFeedback.objects.create(**valid)
        self.assertEqual(feedback.niveau_etudiant, "M2")

        invalid_cases = [
            {"qualite_enseignement": 8},
            {"probability_satisfied": 101.0},
            {"niveau_etudiant": "M3"},
        ]

        for override in invalid_cases:
            payload = dict(valid)
            payload.update(override)
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    StudentFeedback.objects.create(**payload)

