from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
TESTS = ROOT / "predictor" / "tests.py"

if not (ROOT / "manage.py").is_file():
    print("ERREUR : exécute ce script depuis la racine du projet Django.")
    sys.exit(1)

if not TESTS.is_file():
    print("ERREUR : predictor/tests.py introuvable.")
    sys.exit(1)

text = TESTS.read_text(encoding="utf-8")

old = '        self.assertContains(response, "n\'est pas disponible pour cette session")\n'

new = '''        rendered_messages = [str(message) for message in response.context["messages"]]
        self.assertTrue(
            any(
                "n'est pas disponible pour cette session" in message
                for message in rendered_messages
            )
        )
'''

if new in text:
    print("Correctif V11.1 déjà appliqué : aucune modification.")
    sys.exit(0)

if old not in text:
    print("ERREUR : assertion V11 attendue introuvable. Aucun fichier modifié.")
    sys.exit(1)

patched = text.replace(old, new, 1)
compile(patched, "predictor/tests.py", "exec")

backup_dir = (
    ROOT
    / "correctif_backups"
    / f"batch-prediction-v11-1-{datetime.now():%Y%m%d-%H%M%S}"
)
backup_dir.mkdir(parents=True, exist_ok=True)

backup = backup_dir / "predictor" / "tests.py"
backup.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(TESTS, backup)

TESTS.write_text(patched, encoding="utf-8", newline="\n")

print("")
print("Correctif V11.1 appliqué avec succès.")
print(f"Sauvegarde : {backup_dir.relative_to(ROOT)}")
print("")
print("Fichier modifié :")
print("- predictor\\tests.py")
print("")
print("Correction :")
print("- le test du token batch inconnu vérifie maintenant le message Django")
print("  avant rendu/échappement HTML, au lieu de comparer l'apostrophe brute")
print("")
print("Aucun code applicatif V11 n'a été modifié.")
print("")
print("Validation :")
print("  python manage.py check")
print("  python manage.py makemigrations --check")
print("  python manage.py test")
