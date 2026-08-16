from __future__ import annotations

import argparse
import csv
import math
import random
from collections import Counter
from itertools import product
from pathlib import Path

COLUMNS = [
    "qualite_enseignement",
    "charge_travail",
    "interactivite",
    "type_cours",
    "niveau_etudiant",
    "satisfaction",
]

QUALITY_WEIGHTS = {1: 0.05, 2: 0.10, 3: 0.16, 4: 0.24, 5: 0.22, 6: 0.15, 7: 0.08}
WORKLOAD_WEIGHTS = {1: 0.04, 2: 0.08, 3: 0.17, 4: 0.28, 5: 0.22, 6: 0.14, 7: 0.07}
INTERACTIVITY_WEIGHTS = {1: 0.06, 2: 0.10, 3: 0.17, 4: 0.23, 5: 0.21, 6: 0.15, 7: 0.08}
COURSE_TYPE_WEIGHTS = {"présentiel": 0.45, "distanciel": 0.30, "hybride": 0.25}
LEVEL_WEIGHTS = {"L1": 0.24, "L2": 0.22, "L3": 0.20, "M1": 0.18, "M2": 0.16}

MAX_UNIQUE_PROFILES = (
    len(QUALITY_WEIGHTS)
    * len(WORKLOAD_WEIGHTS)
    * len(INTERACTIVITY_WEIGHTS)
    * len(COURSE_TYPE_WEIGHTS)
    * len(LEVEL_WEIGHTS)
)


def _profile_weight(profile):
    quality, workload, interactivity, course_type, level = profile
    return (
        QUALITY_WEIGHTS[quality]
        * WORKLOAD_WEIGHTS[workload]
        * INTERACTIVITY_WEIGHTS[interactivity]
        * COURSE_TYPE_WEIGHTS[course_type]
        * LEVEL_WEIGHTS[level]
    )


def _weighted_profiles(rows: int, rng: random.Random):
    profiles = list(
        product(
            QUALITY_WEIGHTS,
            WORKLOAD_WEIGHTS,
            INTERACTIVITY_WEIGHTS,
            COURSE_TYPE_WEIGHTS,
            LEVEL_WEIGHTS,
        )
    )

    # Tirage pondéré sans remise par "course exponentielle".
    # Chaque profil de caractéristiques est donc unique dans le CSV final.
    ranked = [
        (rng.expovariate(_profile_weight(profile)), profile)
        for profile in profiles
    ]
    ranked.sort(key=lambda item: item[0])
    return [profile for _key, profile in ranked[:rows]]


def _satisfaction_probability(profile, rng: random.Random) -> float:
    quality, workload, interactivity, course_type, level = profile

    score = -0.25
    score += 0.58 * (quality - 4)
    score += 0.48 * (interactivity - 4)
    score -= 0.24 * abs(workload - 4)

    score += {
        "présentiel": 0.08,
        "distanciel": -0.10,
        "hybride": 0.12,
    }[course_type]

    score += {
        "L1": -0.10,
        "L2": -0.05,
        "L3": 0.00,
        "M1": 0.05,
        "M2": 0.08,
    }[level]

    # Variabilité individuelle : deux profils proches ne donnent pas
    # nécessairement la même satisfaction.
    score += rng.gauss(0.0, 0.90)

    return 1.0 / (1.0 + math.exp(-score))


def generate_dataset(rows: int = 2000, seed: int = 42) -> list[dict]:
    if rows < 20:
        raise ValueError("Le nombre de lignes doit être au moins 20.")
    if rows > MAX_UNIQUE_PROFILES:
        raise ValueError(
            f"Maximum {MAX_UNIQUE_PROFILES} lignes avec profils uniques."
        )

    rng = random.Random(seed)
    profiles = _weighted_profiles(rows, rng)
    dataset = []

    for profile in profiles:
        quality, workload, interactivity, course_type, level = profile
        probability = _satisfaction_probability(profile, rng)
        satisfaction = 1 if rng.random() < probability else 0

        dataset.append(
            {
                "qualite_enseignement": quality,
                "charge_travail": workload,
                "interactivite": interactivity,
                "type_cours": course_type,
                "niveau_etudiant": level,
                "satisfaction": satisfaction,
            }
        )

    classes = {row["satisfaction"] for row in dataset}
    if classes != {0, 1}:
        # Garde-fou pour les très petits jeux générés.
        dataset[0]["satisfaction"] = 0
        dataset[1]["satisfaction"] = 1

    return dataset


def write_dataset(dataset: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(dataset)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Génère des avis étudiants synthétiques pour le MLP Django."
    )
    parser.add_argument("--rows", type=int, default=2000, help="Nombre de lignes (20 à 5145).")
    parser.add_argument("--seed", type=int, default=42, help="Graine aléatoire reproductible.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Chemin CSV de sortie. Par défaut : data/satisfaction_etudiants_synthetiques_v8_<rows>.csv",
    )
    args = parser.parse_args()

    output = args.output or (
        Path(__file__).resolve().parent
        / "data"
        / f"satisfaction_etudiants_synthetiques_v8_{args.rows}.csv"
    )

    dataset = generate_dataset(rows=args.rows, seed=args.seed)
    write_dataset(dataset, output)

    satisfaction_counts = Counter(row["satisfaction"] for row in dataset)
    level_counts = Counter(row["niveau_etudiant"] for row in dataset)

    print(f"CSV généré : {output}")
    print(f"Lignes : {len(dataset)}")
    print(f"Satisfaits : {satisfaction_counts.get(1, 0)}")
    print(f"Non satisfaits : {satisfaction_counts.get(0, 0)}")
    print(
        "Niveaux : "
        + ", ".join(
            f"{level}={level_counts.get(level, 0)}"
            for level in LEVEL_WEIGHTS
        )
    )
    print("Profils de caractéristiques dupliqués : 0")


if __name__ == "__main__":
    main()
