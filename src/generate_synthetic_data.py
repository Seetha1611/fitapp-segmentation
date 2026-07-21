"""
Génération d'un jeu de données synthétique pour une appli de suivi sportif.

Contexte fictif : "FitTrack", une appli où les utilisateurs saisissent
manuellement leurs séances (type d'activité, durée, intensité ressentie).
Objectif : reproduire des profils d'usage réalistes et contrastés pour
pouvoir ensuite appliquer une méthodologie de segmentation comportementale.

Ce script ne contient aucune donnée réelle ni aucun code métier propriétaire :
uniquement une simulation générique inspirée du type de problème
(comportement de saisie d'un utilisateur dans une appli data-driven).
"""

from datetime import timedelta

import numpy as np
import pandas as pd

from config import DATA_DIR, END_DATE, OBSERVATION_DAYS, START_DATE

RNG = np.random.default_rng(42)

N_USERS = 1200

ACTIVITY_TYPES = [
    "course_a_pied", "velo", "musculation", "natation",
    "yoga", "hiit", "marche", "sport_collectif",
]

# Profils comportementaux archétypaux (utilisés seulement pour GENERER
# des données réalistes ; le clustering ne les connaîtra pas)
ARCHETYPES = {
    "assidu_intense":    dict(weight=0.12, sessions_per_week=(4, 7), duration=(45, 90), intensity=(7, 10), n_activities=(1, 3)),
    "regulier_modere":   dict(weight=0.28, sessions_per_week=(2, 4), duration=(30, 60), intensity=(4, 7), n_activities=(2, 4)),
    "sporadique":        dict(weight=0.25, sessions_per_week=(0.5, 2), duration=(20, 50), intensity=(3, 7), n_activities=(1, 5)),
    "abandonniste":      dict(weight=0.20, sessions_per_week=(1, 3), duration=(20, 60), intensity=(3, 8), n_activities=(1, 3)),  # actif puis arrêt
    "explorateur":       dict(weight=0.15, sessions_per_week=(1, 3), duration=(20, 70), intensity=(3, 9), n_activities=(4, 8)),
}


def pick_archetype():
    names = list(ARCHETYPES.keys())
    weights = [ARCHETYPES[n]["weight"] for n in names]
    return RNG.choice(names, p=np.array(weights) / sum(weights))


def generate_sessions_for_user(user_id):
    archetype = pick_archetype()
    profile = ARCHETYPES[archetype]

    sessions_per_week = RNG.uniform(*profile["sessions_per_week"])
    n_activities = RNG.integers(profile["n_activities"][0], profile["n_activities"][1] + 1)
    user_activities = RNG.choice(ACTIVITY_TYPES, size=n_activities, replace=False)

    # Pour l'archétype "abandonniste" : actif la 1ère moitié, quasi inactif ensuite
    if archetype == "abandonniste":
        active_end = START_DATE + timedelta(days=int(OBSERVATION_DAYS * RNG.uniform(0.3, 0.6)))
    else:
        active_end = END_DATE

    n_sessions_expected = int(sessions_per_week * (OBSERVATION_DAYS / 7))
    n_sessions_expected = max(1, n_sessions_expected)

    sessions = []
    current_date = START_DATE
    # Génère les dates de séance par un processus de Poisson simplifié
    while current_date < active_end:
        gap_days = RNG.exponential(scale=7 / max(sessions_per_week, 0.1))
        current_date += timedelta(days=gap_days)
        if current_date >= active_end:
            break
        activity = RNG.choice(user_activities)
        duration = int(RNG.uniform(*profile["duration"]))
        intensity = int(np.clip(RNG.normal(np.mean(profile["intensity"]), 1.3), 1, 10))
        sessions.append({
            "user_id": user_id,
            "date": current_date.date().isoformat(),
            "activite": activity,
            "duree_minutes": duration,
            "intensite_ressentie": intensity,
        })

    return sessions, archetype


def main():
    all_sessions = []
    user_archetypes = {}

    for i in range(N_USERS):
        user_id = f"U{i:05d}"
        sessions, archetype = generate_sessions_for_user(user_id)
        all_sessions.extend(sessions)
        user_archetypes[user_id] = archetype

    df_sessions = pd.DataFrame(all_sessions)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df_sessions.to_csv(DATA_DIR / "sessions.csv", index=False)

    df_archetypes = pd.DataFrame(
        [{"user_id": k, "archetype_genere": v} for k, v in user_archetypes.items()]
    )
    df_archetypes.to_csv(DATA_DIR / "archetypes_reference.csv", index=False)

    print(f"Sessions générées : {len(df_sessions)}")
    print(f"Utilisateurs : {N_USERS}")
    print(df_sessions.head())
    print("\nRépartition archétypes générés (pour validation ultérieure, non utilisée dans le clustering) :")
    print(df_archetypes["archetype_genere"].value_counts(normalize=True).round(3))


if __name__ == "__main__":
    main()
