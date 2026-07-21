"""Constantes partagées entre les scripts du pipeline (chemins, fenêtre
temporelle de référence, liste des indicateurs) — pour éviter que chaque
script ne redéfinisse sa propre copie."""

from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"

OBSERVATION_DAYS = 180  # ~6 mois d'historique
END_DATE = datetime(2026, 7, 1)
START_DATE = END_DATE - timedelta(days=OBSERVATION_DAYS)

INDICATOR_COLS = [
    "nb_sessions_total", "duree_moyenne_session", "jours_depuis_derniere_session",
    "ecart_type_intervalle", "taux_semaines_actives", "diversite_activites",
    "intensite_moyenne_ressentie", "tendance_recente",
]
