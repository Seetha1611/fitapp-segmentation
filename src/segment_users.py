"""
Segmentation comportementale des utilisateurs FitTrack.

Approche en deux temps (reprise de la méthodologie originale) :
  1. Stratification par règles métier simples (garde-fous interprétables,
     évite qu'un clustering pur ne "invente" des groupes non actionnables)
  2. Clustering (KMeans) au sein des strates pour affiner les profils fins

Prétraitement : log1p sur les variables de volume (fortement asymétriques)
+ RobustScaler (résistant aux outliers, plus adapté que StandardScaler
sur ce type de distribution de comportement utilisateur).
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler
from sklearn.cluster import KMeans

from config import DATA_DIR, INDICATOR_COLS

LOG_COLS = ["nb_sessions_total", "jours_depuis_derniere_session", "ecart_type_intervalle"]

# Seuils de la strate de règles (cf. Limites dans le README : choix simples,
# à calibrer avec une équipe produit sur des données réelles)
INACTIVITY_DAYS = 45
COEUR_ACTIF_TAUX_SEMAINES_MIN = 0.6
COEUR_ACTIF_NB_SESSIONS_MIN = 60
USAGE_OCCASIONNEL_TAUX_SEMAINES_MAX = 0.25

# Nombre de clusters par strate et tailles minimales en dessous desquelles le
# clustering n'est pas jugé statistiquement stable (cf. Limites dans le README)
N_CLUSTERS_PAR_STRATE = 2
MIN_TAILLE_STRATE_POUR_CLUSTERING = 30
MIN_TAILLE_STRATE_POUR_K2 = 60


def apply_business_rules(df: pd.DataFrame) -> pd.DataFrame:
    """Strate 1 : règles interprétables, priorité à la lisibilité métier."""
    df = df.copy()
    conditions = [
        df["jours_depuis_derniere_session"] > INACTIVITY_DAYS,
        (df["taux_semaines_actives"] >= COEUR_ACTIF_TAUX_SEMAINES_MIN)
        & (df["nb_sessions_total"] >= COEUR_ACTIF_NB_SESSIONS_MIN),
        df["taux_semaines_actives"] < USAGE_OCCASIONNEL_TAUX_SEMAINES_MAX,
    ]
    choices = ["inactif_recent", "coeur_actif", "usage_occasionnel"]
    df["strate_regle"] = np.select(conditions, choices, default="usage_regulier")
    return df


def cluster_within_strate(df: pd.DataFrame) -> pd.DataFrame:
    """Strate 2 : affinage par clustering au sein de chaque strate de règle,
    uniquement quand la strate est assez grande pour que ce soit pertinent."""
    df = df.copy()
    df["sous_segment"] = -1

    X_full = df[INDICATOR_COLS].copy()
    for c in LOG_COLS:
        X_full[c] = np.log1p(X_full[c])

    for strate, idx in df.groupby("strate_regle").groups.items():
        idx = list(idx)
        if len(idx) < MIN_TAILLE_STRATE_POUR_CLUSTERING:
            df.loc[idx, "sous_segment"] = 0
            continue

        X = X_full.loc[idx]
        scaler = RobustScaler()
        X_scaled = scaler.fit_transform(X)

        if len(idx) < MIN_TAILLE_STRATE_POUR_K2:
            df.loc[idx, "sous_segment"] = 0
            continue

        km = KMeans(n_clusters=N_CLUSTERS_PAR_STRATE, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)
        df.loc[idx, "sous_segment"] = labels

    df["segment_final"] = df["strate_regle"] + "_" + df["sous_segment"].astype(str)
    return df


def main():
    df_indic = pd.read_csv(DATA_DIR / "indicateurs.csv")
    df_ref = pd.read_csv(DATA_DIR / "archetypes_reference.csv")

    df = apply_business_rules(df_indic)
    df = cluster_within_strate(df)

    df = df.merge(df_ref, on="user_id", how="left")

    df.to_csv(DATA_DIR / "utilisateurs_segmentes.csv", index=False)

    print("Répartition par strate de règle :")
    print(df["strate_regle"].value_counts())
    print("\nRépartition par segment final :")
    print(df["segment_final"].value_counts())

    print("\nValidation croisée : segment_final vs archétype généré (matrice de contingence)")
    print(pd.crosstab(df["segment_final"], df["archetype_genere"]))


if __name__ == "__main__":
    main()
