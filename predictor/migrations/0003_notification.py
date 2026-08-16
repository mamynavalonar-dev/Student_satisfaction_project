from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("predictor", "0002_alter_modeltraining_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120)),
                ("message", models.CharField(max_length=500)),
                ("level", models.CharField(choices=[("info", "Information"), ("success", "Succès"), ("warning", "Avertissement"), ("error", "Erreur")], default="info", max_length=10)),
                ("event_type", models.CharField(choices=[("auth", "Authentification"), ("prediction", "Prédiction"), ("training", "Entraînement"), ("data", "Données"), ("export", "Export"), ("system", "Système")], default="system", max_length=20)),
                ("target_url", models.CharField(blank=True, default="", max_length=255)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="satisfaction_notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["user", "is_read", "created_at"], name="notif_user_read_idx"),
        ),
    ]
