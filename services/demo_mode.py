"""
services/demo_mode.py
──────────────────────
Gestion du mode démo : activation, désactivation, reset complet.
Fonctionne avec SQLite : on copie/restaure patrimoine.db entier.
"""

import os
import shutil
from constants import DEMO_USER_NAME

_ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR   = os.path.join(_ROOT, "data")
BACKUP_DIR = os.path.join(DATA_DIR, "data_backup")
DEMO_DB    = os.path.join(DATA_DIR, "donnees_fictives", "patrimoine.db")
LIVE_DB    = os.path.join(DATA_DIR, "patrimoine.db")
BACKUP_DB  = os.path.join(BACKUP_DIR, "patrimoine.db")
MODE_FILE  = os.path.join(DATA_DIR, ".mode")


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_demo_mode() -> bool:
    try:
        return open(MODE_FILE).read().strip() == "demo"
    except FileNotFoundError:
        return False


def has_backup() -> bool:
    return os.path.exists(BACKUP_DB)


def has_personal_data() -> bool:
    """Retourne True si l'utilisateur a au moins un actif dans ses données."""
    if not os.path.exists(LIVE_DB):
        return False
    try:
        import sqlite3
        conn = sqlite3.connect(LIVE_DB)
        count = conn.execute("SELECT COUNT(*) FROM actifs").fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


# ── Actions ───────────────────────────────────────────────────────────────────

def activate_demo() -> str:
    """
    Active le mode démo :
    - Sauvegarde patrimoine.db dans data_backup/ si des données perso existent
    - Copie la base de démo à la place
    - Écrit le marqueur .mode = demo
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    if has_personal_data():
        os.makedirs(BACKUP_DIR, exist_ok=True)
        shutil.copy2(LIVE_DB, BACKUP_DB)

    if not os.path.exists(DEMO_DB):
        return "Erreur : base de démo introuvable. Lance scripts/generate_demo_db.py d'abord."

    shutil.copy2(DEMO_DB, LIVE_DB)

    with open(MODE_FILE, "w") as fp:
        fp.write("demo")

    return f"Données fictives chargées. Bienvenue chez {DEMO_USER_NAME} 👋"


def deactivate_demo() -> str:
    """
    Désactive le mode démo :
    - Restaure patrimoine.db depuis data_backup/ si un backup existe
    - Sinon, supprime patrimoine.db (retour à état vide)
    - Écrit le marqueur .mode = perso
    """
    if has_backup():
        shutil.copy2(BACKUP_DB, LIVE_DB)
        shutil.rmtree(BACKUP_DIR, ignore_errors=True)
        msg = "Vos données personnelles ont été restaurées."
    else:
        if os.path.exists(LIVE_DB):
            os.remove(LIVE_DB)
        msg = "Mode démo désactivé."

    with open(MODE_FILE, "w") as fp:
        fp.write("perso")

    return msg


def reset_all_data() -> str:
    """
    Supprime toutes les données (base live + backup).
    """
    shutil.rmtree(BACKUP_DIR, ignore_errors=True)

    if os.path.exists(LIVE_DB):
        os.remove(LIVE_DB)

    with open(MODE_FILE, "w") as fp:
        fp.write("perso")

    return "Toutes les données ont été supprimées."