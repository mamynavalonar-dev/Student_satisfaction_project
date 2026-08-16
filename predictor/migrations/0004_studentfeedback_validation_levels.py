from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("predictor", "0003_notification"),
    ]

    operations = [
        migrations.AlterField(
            model_name="studentfeedback",
            name="qualite_enseignement",
            field=models.IntegerField(
                validators=[MinValueValidator(1), MaxValueValidator(7)]
            ),
        ),
        migrations.AlterField(
            model_name="studentfeedback",
            name="charge_travail",
            field=models.IntegerField(
                validators=[MinValueValidator(1), MaxValueValidator(7)]
            ),
        ),
        migrations.AlterField(
            model_name="studentfeedback",
            name="interactivite",
            field=models.IntegerField(
                validators=[MinValueValidator(1), MaxValueValidator(7)]
            ),
        ),
        migrations.AlterField(
            model_name="studentfeedback",
            name="niveau_etudiant",
            field=models.CharField(
                choices=[
                    ("L1", "L1"),
                    ("L2", "L2"),
                    ("L3", "L3"),
                    ("M1", "M1"),
                    ("M2", "M2"),
                ],
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="studentfeedback",
            name="probability_satisfied",
            field=models.FloatField(
                blank=True,
                null=True,
                validators=[MinValueValidator(0), MaxValueValidator(100)],
            ),
        ),
        migrations.AddConstraint(
            model_name="studentfeedback",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    qualite_enseignement__gte=1,
                    qualite_enseignement__lte=7,
                ),
                name="feedback_quality_1_7",
            ),
        ),
        migrations.AddConstraint(
            model_name="studentfeedback",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    charge_travail__gte=1,
                    charge_travail__lte=7,
                ),
                name="feedback_workload_1_7",
            ),
        ),
        migrations.AddConstraint(
            model_name="studentfeedback",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    interactivite__gte=1,
                    interactivite__lte=7,
                ),
                name="feedback_interactivity_1_7",
            ),
        ),
        migrations.AddConstraint(
            model_name="studentfeedback",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    type_cours__in=["présentiel", "distanciel", "hybride"]
                ),
                name="feedback_course_type_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="studentfeedback",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    niveau_etudiant__in=["L1", "L2", "L3", "M1", "M2"]
                ),
                name="feedback_level_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="studentfeedback",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(probability_satisfied__isnull=True)
                    | (
                        models.Q(probability_satisfied__gte=0)
                        & models.Q(probability_satisfied__lte=100)
                    )
                ),
                name="feedback_probability_0_100",
            ),
        ),
    ]
