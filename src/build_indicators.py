"""
Construction des 8 indicateurs comportementaux à partir du log de séances.

Méthodologie (transposée d'un cas de segmentation d'usage d'une plateforme
data-driven vers ce contexte fitness) :

Axe INTENSITÉ
  1. nb_sessions_total       : volume global d'usage
  2. duree_moyenne_session   : effort moyen par séance

Axe RÉCENCE
  3. jours_depuis_derniere_session : engagement actuel

Axe RÉGULARITÉ TEMPORELLE
  4. ecart_type_intervalle   : régularité des intervalles entre séances (faible = régulier)
  5. taux_semaines_actives   : proportion de semaines avec au moins 1 séance

Axe STYLE D'USAGE
  6. diversite_activites     : nombre de types d'activités distincts pratiqués
  7. intensite_moyenne_ressentie : effort perçu moyen
  8. tendance_recente        : évolution de la fréquence (2e moitié vs 1re moitié de la période)
"""

import numpy as np
import pandas as pd

from config import DATA_DIR, END_DATE, START_DATE


def build_indicators(df_sessions: pd.DataFrame) -> pd.DataFrame:
    df = df_sessions.copy()
    df["date"] = pd.to_datetime(df["date"])

    rows = []
    for user_id, g in df.groupby("user_id"):
        g = g.sort_values("date")
        dates = g["date"].tolist()

        nb_sessions_total = len(g)
        duree_moyenne_session = g["duree_minutes"].mean()
        intensite_moyenne_ressentie = g["intensite_ressentie"].mean()
        diversite_activites = g["activite"].nunique()

        jours_depuis_derniere_session = (END_DATE - dates[-1]).days

        if len(dates) > 1:
            intervalles = np.diff(dates).astype("timedelta64[D]").astype(int)
            ecart_type_intervalle = float(np.std(intervalles))
        else:
            ecart_type_intervalle = np.nan  # une seule séance : régularité non définie

        semaines_actives = g["date"].dt.isocalendar().week.nunique()
        total_semaines = int((END_DATE - START_DATE).days / 7)
        taux_semaines_actives = semaines_actives / total_semaines

        midpoint = START_DATE + (END_DATE - START_DATE) / 2
        n_premiere_moitie = (g["date"] < midpoint).sum()
        n_seconde_moitie = (g["date"] >= midpoint).sum()
        # évite division par zéro ; +1 lissage
        tendance_recente = (n_seconde_moitie + 1) / (n_premiere_moitie + 1)

        rows.append({
            "user_id": user_id,
            "nb_sessions_total": nb_sessions_total,
            "duree_moyenne_session": duree_moyenne_session,
            "jours_depuis_derniere_session": jours_depuis_derniere_session,
            "ecart_type_intervalle": ecart_type_intervalle,
            "taux_semaines_actives": taux_semaines_actives,
            "diversite_activites": diversite_activites,
            "intensite_moyenne_ressentie": intensite_moyenne_ressentie,
            "tendance_recente": tendance_recente,
        })

    df_indic = pd.DataFrame(rows)

    # Utilisateurs avec une seule séance : on impute l'écart-type par la valeur
    # max observée (= pire régularité), plutôt que de les exclure
    max_ecart = df_indic["ecart_type_intervalle"].max()
    df_indic["ecart_type_intervalle"] = df_indic["ecart_type_intervalle"].fillna(max_ecart)

    return df_indic


def main():
    df_sessions = pd.read_csv(DATA_DIR / "sessions.csv")
    df_indic = build_indicators(df_sessions)
    df_indic.to_csv(DATA_DIR / "indicateurs.csv", index=False)
    print(df_indic.describe().round(2))
    print(f"\n{len(df_indic)} utilisateurs avec indicateurs calculés")


if __name__ == "__main__":
    main()
