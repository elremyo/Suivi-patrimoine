"""
services/demo_mode.py
──────────────────────
Gestion du mode démo : activation, désactivation, reset complet.
"""

import os
import shutil
import pandas as pd

_ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR   = os.path.join(_ROOT, "data")
BACKUP_DIR = os.path.join(DATA_DIR, "data_backup")
DEMO_DIR   = os.path.join(DATA_DIR, "donnees_fictives")
MODE_FILE  = os.path.join(DATA_DIR, ".mode")

FICHIERS = ["patrimoine.csv", "historique.csv", "positions.csv"]


def is_demo_mode() -> bool:
    try:
        return open(MODE_FILE).read().strip() == "demo"
    except FileNotFoundError:
        return False


def has_backup() -> bool:
    return os.path.exists(BACKUP_DIR) and any(
        os.path.exists(os.path.join(BACKUP_DIR, f)) for f in FICHIERS
    )


def has_personal_data() -> bool:
    """Retourne True si l'utilisateur a au moins un actif dans ses données."""
    path = os.path.join(DATA_DIR, "patrimoine.csv")
    try:
        df = pd.read_csv(path)
        return not df.empty
    except Exception:
        return False


def activate_demo() -> str:
    """
    Active le mode démo :
    - Sauvegarde les données perso dans data/data_backup/ si elles existent
    - Copie les données fictives dans data/
    - Écrit le marqueur .mode = demo
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    if has_personal_data():
        for f in FICHIERS:
            src = os.path.join(DATA_DIR, f)
            dst = os.path.join(BACKUP_DIR, f)
            if os.path.exists(src):
                shutil.copy2(src, dst)

    for f in FICHIERS:
        src = os.path.join(DEMO_DIR, f)
        dst = os.path.join(DATA_DIR, f)
        if os.path.exists(src):
            shutil.copy2(src, dst)

    with open(MODE_FILE, "w") as fp:
        fp.write("demo")

    return "Données fictives chargées. Bienvenue chez Thomas Mercier 👋"


def deactivate_demo() -> str:
    """
    Désactive le mode démo :
    - Restaure les données perso depuis data/data_backup/
    - Supprime data/data_backup/
    - Écrit le marqueur .mode = perso
    """
    if not has_backup():
        return "Aucune donnée personnelle à restaurer."

    for f in FICHIERS:
        src = os.path.join(BACKUP_DIR, f)
        dst = os.path.join(DATA_DIR, f)
        if os.path.exists(src):
            shutil.copy2(src, dst)

    shutil.rmtree(BACKUP_DIR, ignore_errors=True)

    with open(MODE_FILE, "w") as fp:
        fp.write("perso")

    return "Vos données personnelles ont été restaurées. ✅"


def reset_all_data() -> str:
    """
    Supprime toutes les données (data/ + backup).
    """
    shutil.rmtree(BACKUP_DIR, ignore_errors=True)

    for f in FICHIERS:
        path = os.path.join(DATA_DIR, f)
        if os.path.exists(path):
            os.remove(path)

    with open(MODE_FILE, "w") as fp:
        fp.write("perso")

    return "Toutes les données ont été supprimées."