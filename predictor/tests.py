from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import StudentFeedback


class DataManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="mot-de-passe-test")
        # V15A1_EXPLICIT_TEST_ROLE: this legacy fixture explicitly exercises ROLE_ANALYST access.
        from accounts.rbac import ROLE_ANALYST, assign_role
        assign_role(self.user, ROLE_ANALYST)
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
        # V15A1_EXPLICIT_TEST_ROLE: this legacy fixture explicitly exercises ROLE_ANALYST access.
        from accounts.rbac import ROLE_ANALYST, assign_role
        assign_role(self.user, ROLE_ANALYST)
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
        # V15A1_EXPLICIT_TEST_ROLE: this legacy fixture explicitly exercises ROLE_ML_MANAGER access.
        from accounts.rbac import ROLE_ML_MANAGER, assign_role
        assign_role(self.user, ROLE_ML_MANAGER)
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
        # V15A1_EXPLICIT_TEST_ROLE: this legacy fixture explicitly exercises ROLE_ANALYST access.
        from accounts.rbac import ROLE_ANALYST, assign_role
        assign_role(self.user, ROLE_ANALYST)
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
                accuracy, relative_path, metrics = train_model(
                    frame,
                    param_grid={
                        "classifier__hidden_layer_sizes": [(64, 32)],
                        "classifier__alpha": [0.001],
                    },
                    cv_splits=2,
                )

            artifact_path = fake_base / relative_path
            self.assertTrue(artifact_path.is_file())

            artifact = joblib.load(artifact_path)
            self.assertEqual(artifact["schema_version"], 3)
            self.assertIn("pipeline", artifact)
            self.assertIn("preprocessor", artifact["pipeline"].named_steps)
            self.assertIn("classifier", artifact["pipeline"].named_steps)
            self.assertIn("explanation_background", artifact)
            self.assertEqual(len(artifact["explanation_background"]), 40)
            self.assertIn("explanation_reference", artifact)
            self.assertIn("model_selection", artifact)
            self.assertEqual(artifact["model_selection"]["selection_metric"], "f1")
            self.assertEqual(artifact["model_selection"]["cv_splits"], 2)
            self.assertEqual(artifact["model_selection"]["candidate_count"], 1)
            self.assertIn("cv_f1_mean", metrics)
            self.assertIn("cv_f1_std", metrics)
            self.assertEqual(len(artifact["explanation_reference"]["features"]), metrics["test_size"])
            self.assertEqual(len(artifact["explanation_reference"]["target"]), metrics["test_size"])

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

class InterpretabilityTests(TestCase):
    class SimpleProbabilityPipeline:
        classes_ = [0, 1]

        def predict_proba(self, frame):
            import numpy as np

            quality = frame["qualite_enseignement"].astype(float).to_numpy()
            workload = frame["charge_travail"].astype(float).to_numpy()
            interactivity = frame["interactivite"].astype(float).to_numpy()
            course = frame["type_cours"].map({"présentiel": 0.20, "hybride": 0.10, "distanciel": -0.15}).astype(float).to_numpy()
            level = frame["niveau_etudiant"].map({"L1": -0.10, "L2": -0.05, "L3": 0.0, "M1": 0.05, "M2": 0.10}).astype(float).to_numpy()
            score = 0.45 * (quality - 4) - 0.18 * abs(workload - 4) + 0.38 * (interactivity - 4) + course + level
            satisfied = 1.0 / (1.0 + np.exp(-score))
            return np.column_stack([1.0 - satisfied, satisfied])

    @staticmethod
    def _background_records():
        return [
            {"qualite_enseignement": 2, "charge_travail": 6, "interactivite": 2, "type_cours": "distanciel", "niveau_etudiant": "L1"},
            {"qualite_enseignement": 4, "charge_travail": 4, "interactivite": 4, "type_cours": "hybride", "niveau_etudiant": "L3"},
            {"qualite_enseignement": 6, "charge_travail": 3, "interactivite": 6, "type_cours": "présentiel", "niveau_etudiant": "M1"},
            {"qualite_enseignement": 7, "charge_travail": 4, "interactivite": 7, "type_cours": "présentiel", "niveau_etudiant": "M2"},
        ]

    def test_exact_shapley_explanation_is_additive_and_has_five_features(self):
        from .utils_explain import get_local_explanation

        model_data = {"pipeline": self.SimpleProbabilityPipeline(), "explanation_background": self._background_records()}
        input_data = {"qualite_enseignement": 7, "charge_travail": 4, "interactivite": 7, "type_cours": "présentiel", "niveau_etudiant": "M2"}
        explanation = get_local_explanation(model_data, input_data)

        self.assertTrue(explanation["available"])
        self.assertEqual(len(explanation["items"]), 5)
        contribution_sum = sum(item["contribution"] for item in explanation["items"])
        expected_delta = explanation["predicted_probability"] - explanation["baseline_probability"]
        self.assertAlmostEqual(contribution_sum, expected_delta, places=2)
        self.assertLess(explanation["additivity_error"], 1e-6)

    def test_global_importance_keeps_exactly_the_five_business_features(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        import numpy as np
        from .utils_explain import get_global_importance

        model_data = {
            "training_date": "test-importance-unique",
            "pipeline": self.SimpleProbabilityPipeline(),
            "explanation_reference": {"features": self._background_records(), "target": [0, 0, 1, 1]},
        }
        fake_result = SimpleNamespace(
            importances_mean=np.array([0.20, 0.05, 0.15, 0.02, 0.01]),
            importances_std=np.array([0.02, 0.01, 0.03, 0.01, 0.005]),
        )
        with patch("predictor.utils_explain.permutation_importance", return_value=fake_result):
            result = get_global_importance(model_data)

        self.assertTrue(result["available"])
        self.assertEqual(len(result["items"]), 5)
        self.assertEqual(result["items"][0]["feature"], "qualite_enseignement")

    def test_predict_view_exposes_local_explanation_without_breaking_prediction(self):
        from django.contrib.auth.models import User
        from django.urls import reverse
        from unittest.mock import patch

        user = User.objects.create_user(username="explain-predict", password="ProjetIA-2026!Solide")
        self.client.force_login(user)
        prediction = {"prediction": 1, "probability_satisfied": 82.0, "probability_unsatisfied": 18.0, "satisfaction_text": "Satisfait", "prediction_probability": 82.0}
        explanation = {"available": True, "items": [], "baseline_probability": 50.0, "predicted_probability": 82.0, "method": "test", "reference_source": "test"}

        with (
            patch("predictor.views.load_current_model", return_value={"pipeline": object()}),
            patch("predictor.views.predict_satisfaction", return_value=prediction),
            patch("predictor.views.get_local_explanation", return_value=explanation),
        ):
            response = self.client.post(
                reverse("predict"),
                {"qualite_enseignement": "7", "charge_travail": "4", "interactivite": "7", "type_cours": "présentiel", "niveau_etudiant": "M1"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["prediction_explanation"], explanation)
        self.assertContains(response, "Pourquoi cette prédiction ?")

    def test_statistics_exposes_model_importance(self):
        from django.contrib.auth.models import User
        from django.urls import reverse
        from unittest.mock import patch

        user = User.objects.create_user(username="explain-stats", password="ProjetIA-2026!Solide")
        # V15A1_EXPLICIT_TEST_ROLE: this legacy fixture explicitly exercises ROLE_ANALYST access.
        from accounts.rbac import ROLE_ANALYST, assign_role
        assign_role(user, ROLE_ANALYST)
        self.client.force_login(user)
        importance = {
            "available": True,
            "items": [{"label": "Qualité de l'enseignement", "importance_points": 12.5, "std_points": 1.0, "width": 100.0}],
            "method": "Importance par permutation",
            "metric": "F1-score",
            "sample_size": 100,
            "n_repeats": 8,
            "reference_source": "test",
        }
        with (
            patch("predictor.views.load_current_model", return_value={"pipeline": object()}),
            patch("predictor.views.get_global_importance", return_value=importance),
        ):
            response = self.client.get(reverse("statistics"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["model_importance"], importance)
        self.assertContains(response, "Importance globale du modèle")

class BatchPredictionTests(TestCase):
    @staticmethod
    def _valid_batch_frame():
        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "qualite_enseignement": 7,
                    "charge_travail": 4,
                    "interactivite": 7,
                    "type_cours": "presentiel",
                    "niveau_etudiant": "m1",
                },
                {
                    "qualite_enseignement": 1,
                    "charge_travail": 7,
                    "interactivite": 1,
                    "type_cours": "distanciel",
                    "niveau_etudiant": "M2",
                },
            ]
        )

    def setUp(self):
        self.user = User.objects.create_user(
            username="batch-user",
            password="mot-de-passe-batch",
        )
        # V15A1_EXPLICIT_TEST_ROLE: this legacy fixture explicitly exercises ROLE_ANALYST access.
        from accounts.rbac import ROLE_ANALYST, assign_role
        assign_role(self.user, ROLE_ANALYST)
        self.client.force_login(self.user)

    def test_validate_prediction_dataframe_accepts_m1_m2_and_normalizes_values(self):
        from .neural_network_model import validate_prediction_dataframe

        validated = validate_prediction_dataframe(self._valid_batch_frame())

        self.assertEqual(list(validated.columns), [
            "qualite_enseignement",
            "charge_travail",
            "interactivite",
            "type_cours",
            "niveau_etudiant",
        ])
        self.assertEqual(validated.loc[0, "type_cours"], "présentiel")
        self.assertEqual(validated.loc[0, "niveau_etudiant"], "M1")
        self.assertEqual(validated.loc[1, "niveau_etudiant"], "M2")

    def test_validate_prediction_dataframe_rejects_target_column(self):
        from .neural_network_model import validate_prediction_dataframe

        frame = self._valid_batch_frame()
        frame["satisfaction"] = [1, 0]

        with self.assertRaisesRegex(ValueError, "Colonnes supplémentaires"):
            validate_prediction_dataframe(frame)

    def test_validate_prediction_dataframe_rejects_more_than_5000_rows(self):
        import pandas as pd

        from .neural_network_model import validate_prediction_dataframe

        row = self._valid_batch_frame().iloc[0].to_dict()
        frame = pd.DataFrame([row] * 5001)

        with self.assertRaisesRegex(ValueError, "limite est de 5000"):
            validate_prediction_dataframe(frame)

    def test_predict_satisfaction_batch_is_vectorized_and_returns_expected_columns(self):
        import numpy as np

        from .neural_network_model import predict_satisfaction_batch

        class FakePipeline:
            classes_ = np.array([0, 1])

            def predict(self, frame):
                return np.array([1 if value >= 4 else 0 for value in frame["qualite_enseignement"]])

            def predict_proba(self, frame):
                satisfied = np.array([0.8 if value >= 4 else 0.2 for value in frame["qualite_enseignement"]])
                return np.column_stack([1.0 - satisfied, satisfied])

        result = predict_satisfaction_batch(
            {"pipeline": FakePipeline()},
            self._valid_batch_frame(),
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result.loc[0, "predicted_satisfaction"], 1)
        self.assertEqual(result.loc[1, "predicted_satisfaction"], 0)
        self.assertEqual(result.loc[0, "probability_satisfied"], 80.0)
        self.assertEqual(result.loc[1, "confidence"], 80.0)

    def test_batch_page_is_accessible(self):
        response = self.client.get(reverse("batch_predict"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Prédiction par lot")
        self.assertContains(response, "Lancer la prédiction par lot")

    def test_batch_upload_redirects_to_summary_and_creates_download(self):
        import tempfile

        import pandas as pd
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings

        predicted = pd.DataFrame(
            [
                {
                    "qualite_enseignement": 7,
                    "charge_travail": 4,
                    "interactivite": 7,
                    "type_cours": "présentiel",
                    "niveau_etudiant": "M1",
                    "predicted_satisfaction": 1,
                    "prediction_label": "Satisfait",
                    "probability_satisfied": 87.2,
                    "probability_unsatisfied": 12.8,
                    "confidence": 87.2,
                },
                {
                    "qualite_enseignement": 1,
                    "charge_travail": 7,
                    "interactivite": 1,
                    "type_cours": "distanciel",
                    "niveau_etudiant": "M2",
                    "predicted_satisfaction": 0,
                    "prediction_label": "Non satisfait",
                    "probability_satisfied": 1.7,
                    "probability_unsatisfied": 98.3,
                    "confidence": 98.3,
                },
            ]
        )

        csv_payload = (
            "qualite_enseignement,charge_travail,interactivite,type_cours,niveau_etudiant\n"
            "7,4,7,présentiel,M1\n"
            "1,7,1,distanciel,M2\n"
        ).encode("utf-8")

        with tempfile.TemporaryDirectory() as media_root:
            with (
                override_settings(MEDIA_ROOT=media_root),
                patch("predictor.views.load_current_model", return_value={"pipeline": object()}),
                patch("predictor.views.predict_satisfaction_batch", return_value=predicted),
            ):
                response = self.client.post(
                    reverse("batch_predict"),
                    {
                        "csv_file": SimpleUploadedFile(
                            "lot.csv",
                            csv_payload,
                            content_type="text/csv",
                        )
                    },
                    follow=True,
                )

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "2 lignes traitées")
                self.assertContains(response, "87,2%")
                batch_result = self.client.session["batch_prediction_result"]
                self.assertEqual(batch_result["summary"]["satisfied"], 1)
                self.assertEqual(batch_result["summary"]["unsatisfied"], 1)

                download = self.client.get(
                    reverse(
                        "batch_predict_download",
                        args=[batch_result["download_token"]],
                    )
                )
                self.assertEqual(download.status_code, 200)
                self.assertIn("text/csv", download["Content-Type"])
                self.assertIn(b"predicted_satisfaction", download.content)

    def test_batch_download_rejects_unknown_token(self):
        import uuid

        response = self.client.get(
            reverse("batch_predict_download", args=[uuid.uuid4()]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        rendered_messages = [str(message) for message in response.context["messages"]]
        self.assertTrue(
            any(
                "n'est pas disponible pour cette session" in message
                for message in rendered_messages
            )
        )

class ModelManagementTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.user = get_user_model().objects.create_user(
            username="model-manager",
            email="model-manager@example.com",
            password="ModelManagement123!",
        )
        # V15A1_EXPLICIT_TEST_ROLE: this legacy fixture explicitly exercises ROLE_ML_MANAGER access.
        from accounts.rbac import ROLE_ML_MANAGER, assign_role
        assign_role(self.user, ROLE_ML_MANAGER)
        self.client.force_login(self.user)

    def _training(self, *, accuracy=0.70, model_file="model.joblib", active=False):
        from .models import ModelTraining
        return ModelTraining.objects.create(
            accuracy=accuracy,
            dataset_size=200,
            model_file=model_file,
            notes="test gestion modèle",
            is_active=active,
        )

    def test_inspect_model_artifact_reports_missing_file_without_exception(self):
        from unittest.mock import patch
        from .neural_network_model import inspect_model_artifact
        with patch("predictor.neural_network_model._resolve_model_path", return_value=None):
            info = inspect_model_artifact("missing.joblib")
        self.assertFalse(info["available"])
        self.assertFalse(info["compatible"])
        self.assertIn("introuvable", info["reason"])

    def test_activate_model_keeps_exactly_one_active_training(self):
        from pathlib import Path
        from unittest.mock import patch
        from django.urls import reverse
        from .models import ModelTraining

        old = self._training(model_file="old.joblib", active=True)
        target = self._training(accuracy=0.81, model_file="target.joblib", active=False)

        with patch(
            "predictor.views.load_model_artifact",
            return_value=({"pipeline": object()}, Path("target.joblib")),
        ):
            response = self.client.post(reverse("activate_model", args=[target.pk]))

        self.assertEqual(response.status_code, 302)
        old.refresh_from_db()
        target.refresh_from_db()
        self.assertFalse(old.is_active)
        self.assertTrue(target.is_active)
        self.assertEqual(ModelTraining.objects.filter(is_active=True).count(), 1)

    def test_activate_model_refuses_missing_artifact_and_preserves_current(self):
        from unittest.mock import patch
        from django.urls import reverse

        current = self._training(model_file="current.joblib", active=True)
        target = self._training(model_file="missing.joblib", active=False)

        with patch("predictor.views.load_model_artifact", side_effect=FileNotFoundError("missing")):
            response = self.client.post(reverse("activate_model", args=[target.pk]))

        self.assertEqual(response.status_code, 302)
        current.refresh_from_db()
        target.refresh_from_db()
        self.assertTrue(current.is_active)
        self.assertFalse(target.is_active)

    def test_deactivate_active_model_leaves_no_active_training(self):
        from django.urls import reverse
        from .models import ModelTraining

        current = self._training(model_file="current.joblib", active=True)
        response = self.client.post(reverse("deactivate_model", args=[current.pk]))

        self.assertEqual(response.status_code, 302)
        current.refresh_from_db()
        self.assertFalse(current.is_active)
        self.assertEqual(ModelTraining.objects.filter(is_active=True).count(), 0)

    def test_model_management_actions_are_post_only(self):
        from django.urls import reverse
        training = self._training(model_file="current.joblib", active=False)
        self.assertEqual(self.client.get(reverse("activate_model", args=[training.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("deactivate_model", args=[training.pk])).status_code, 405)

    def test_training_page_displays_management_state_and_metrics(self):
        from unittest.mock import patch
        from django.urls import reverse

        training = self._training(accuracy=0.8125, model_file="available.joblib", active=False)
        artifact_info = {
            "available": True,
            "compatible": True,
            "format_label": "Pipeline v2",
            "reason": "",
            "file_name": "available.joblib",
            "file_size_mb": 0.42,
            "metrics": {
                "precision": 0.76,
                "recall": 0.72,
                "f1": 0.74,
                "train_size": 160,
                "test_size": 40,
            },
        }

        with (
            patch("predictor.views.inspect_model_artifact", return_value=artifact_info),
            patch("predictor.views.load_current_model", return_value=None),
        ):
            response = self.client.get(reverse("train_model"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestion et comparaison des modèles")
        self.assertContains(response, "74,00%")
        self.assertContains(response, "Pipeline v2")
        self.assertContains(response, reverse("activate_model", args=[training.pk]))

class ModelTuningTests(TestCase):
    def test_pipeline_builder_applies_hidden_layers_and_alpha(self):
        from .neural_network_model import _build_pipeline

        pipeline = _build_pipeline(
            hidden_layer_sizes=(64, 32),
            alpha=0.0001,
        )
        classifier = pipeline.named_steps["classifier"]

        self.assertEqual(classifier.hidden_layer_sizes, (64, 32))
        self.assertEqual(classifier.alpha, 0.0001)
        self.assertTrue(classifier.early_stopping)

    def test_model_search_is_stratified_three_fold_and_refits_on_f1(self):
        from sklearn.model_selection import StratifiedKFold

        from .neural_network_model import _make_model_search

        search = _make_model_search()

        self.assertEqual(search.refit, "f1")
        self.assertIsInstance(search.cv, StratifiedKFold)
        self.assertEqual(search.cv.n_splits, 3)
        self.assertTrue(search.cv.shuffle)
        self.assertEqual(search.cv.random_state, 42)
        self.assertEqual(
            set(search.scoring.keys()),
            {"accuracy", "precision", "recall", "f1"},
        )
        self.assertEqual(
            len(search.param_grid["classifier__hidden_layer_sizes"])
            * len(search.param_grid["classifier__alpha"]),
            4,
        )

    def test_model_search_rejects_less_than_two_folds(self):
        from .neural_network_model import _make_model_search

        with self.assertRaises(ValueError):
            _make_model_search(cv_splits=1)

    def test_active_training_configuration_reads_v3_selection(self):
        from .neural_network_model import _build_pipeline
        from .views import _active_training_configuration

        model_data = {
            "schema_version": 3,
            "pipeline": _build_pipeline(
                hidden_layer_sizes=(64, 32),
                alpha=0.0001,
            ),
            "model_selection": {
                "cv_splits": 3,
                "candidate_count": 4,
                "f1_mean": 0.7123,
                "f1_std": 0.021,
            },
        }

        config = _active_training_configuration(model_data)

        self.assertTrue(config["tuned"])
        self.assertEqual(config["layers_display"], "(64, 32)")
        self.assertEqual(config["alpha"], 0.0001)
        self.assertEqual(config["cv_folds"], 3)
        self.assertEqual(config["candidate_count"], 4)
        self.assertEqual(config["cv_f1_percent"], 71.23)

    def test_management_rows_expose_cv_metrics_and_selected_parameters(self):
        from unittest.mock import patch

        from .models import ModelTraining
        from .views import _model_management_rows

        training = ModelTraining.objects.create(
            accuracy=0.73,
            dataset_size=2000,
            model_file="v3.joblib",
            notes="v3 tuning",
            is_active=True,
        )
        artifact_info = {
            "available": True,
            "compatible": True,
            "format_label": "Pipeline v3",
            "reason": "",
            "file_name": "v3.joblib",
            "file_size_mb": 0.3,
            "metrics": {
                "f1": 0.70,
                "cv_f1_mean": 0.72,
                "cv_f1_std": 0.02,
                "cv_folds": 3,
                "candidate_count": 4,
            },
            "model_selection": {
                "selected_hidden_layer_sizes": [64, 32],
                "selected_alpha": 0.0001,
            },
        }

        with patch(
            "predictor.views.inspect_model_artifact",
            return_value=artifact_info,
        ):
            rows = _model_management_rows([training])

        self.assertEqual(rows[0]["cv_f1_percent"], 72.0)
        self.assertEqual(rows[0]["cv_f1_std_percent"], 2.0)
        self.assertEqual(rows[0]["selected_layers_display"], "(64, 32)")
        self.assertEqual(rows[0]["selected_alpha"], 0.0001)

class ModelVersionCompatibilityTests(TestCase):
    def _version_warning(self):
        from sklearn.exceptions import InconsistentVersionWarning

        return InconsistentVersionWarning(
            estimator_name="MLPClassifier",
            current_sklearn_version="1.9.0",
            original_sklearn_version="1.7.0",
        )

    def test_inspection_marks_cross_version_artifact_incompatible(self):
        from pathlib import Path
        from unittest.mock import patch

        from .neural_network_model import inspect_model_artifact

        fake_path = Path("legacy.joblib")
        fake_stat = type("Stat", (), {"st_size": 1024})()

        with (
            patch(
                "predictor.neural_network_model._resolve_model_path",
                return_value=fake_path,
            ),
            patch.object(Path, "stat", return_value=fake_stat),
            patch(
                "predictor.neural_network_model.joblib.load",
                side_effect=self._version_warning(),
            ),
        ):
            info = inspect_model_artifact("legacy.joblib")

        self.assertTrue(info["available"])
        self.assertFalse(info["compatible"])
        self.assertEqual(
            info["format_label"],
            "Version scikit-learn différente",
        )
        self.assertIn("1.7.0", info["reason"])
        self.assertIn("1.9.0", info["reason"])

    def test_activation_loader_refuses_cross_version_artifact(self):
        from pathlib import Path
        from unittest.mock import patch

        from .neural_network_model import load_model_artifact

        with (
            patch(
                "predictor.neural_network_model._resolve_model_path",
                return_value=Path("legacy.joblib"),
            ),
            patch(
                "predictor.neural_network_model.joblib.load",
                side_effect=self._version_warning(),
            ),
        ):
            with self.assertRaisesMessage(
                ValueError,
                "Version scikit-learn incompatible",
            ):
                load_model_artifact("legacy.joblib")


class UxAccessibilityV14ATests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.user = get_user_model().objects.create_user(
            username="ux-v14a-user",
            email="ux-v14a@example.com",
            password="UxV14A-2026!Solide",
        )
        self.client.force_login(self.user)

    def test_base_exposes_skip_link_main_target_and_primary_nav_label(self):
        from django.urls import reverse

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="skip-link"')
        self.assertContains(response, 'href="#main-content"')
        self.assertContains(response, 'id="main-content"')
        self.assertContains(response, 'tabindex="-1"')
        self.assertContains(response, 'aria-label="Navigation principale"')

    def test_theme_control_is_accessible_and_assets_are_linked(self):
        from django.urls import reverse

        response = self.client.get(reverse("home"))

        self.assertContains(response, "data-theme-toggle")
        self.assertContains(response, "Changer le thème")
        self.assertContains(response, "ux/theme_accessibility.css")
        self.assertContains(response, "ux/theme_accessibility.js")
        self.assertContains(response, "ux/favicon.svg")
        self.assertContains(response, 'name="color-scheme"')

    def test_favicon_root_route_no_longer_returns_404(self):
        response = self.client.get("/favicon.ico")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/static/ux/favicon.svg")

    def test_theme_script_supports_persistence_auto_mode_and_system_theme(self):
        from pathlib import Path
        from django.conf import settings

        path = Path(settings.BASE_DIR) / "static" / "ux" / "theme_accessibility.js"
        content = path.read_text(encoding="utf-8")

        self.assertIn("student-satisfaction-theme", content)
        self.assertIn("prefers-color-scheme: dark", content)
        self.assertIn("localStorage.setItem", content)
        self.assertIn("app-theme-change", content)

    def test_accessibility_styles_include_focus_and_reduced_motion(self):
        from pathlib import Path
        from django.conf import settings

        path = Path(settings.BASE_DIR) / "static" / "ux" / "theme_accessibility.css"
        content = path.read_text(encoding="utf-8")

        self.assertIn(":focus-visible", content)
        self.assertIn(".skip-link", content)
        self.assertIn("prefers-reduced-motion: reduce", content)
        self.assertIn('html[data-app-theme="dark"]', content)
