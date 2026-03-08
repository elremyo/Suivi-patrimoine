#!/usr/bin/env python3
"""
scripts/generate_demo_db.py
────────────────────────────
Génère data/donnees_fictives/patrimoine.db avec un profil fictif réaliste.

Profil : Thomas DOE ~200 000 € de patrimoine
  - Livrets     : Livret A + LDDS
  - PEA         : ETF World (CW8.PA) + ETF Nasdaq (PANX.PA)
  - CTO         : Apple (AAPL) + Microsoft (MSFT)
  - Crypto      : Bitcoin (BTC-USD) + Ethereum (ETH-USD)
  - Assurance vie : Fonds euros
  - Immobilier  : Résidence principale ~200k€ + emprunt associé

Usage (depuis la racine du projet) :
    python scripts/generate_demo_db.py
"""

import os
import sys
import sqlite3
import uuid
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEMO_DB_DIR  = ROOT / "data" / "donnees_fictives"
DEMO_DB_PATH = DEMO_DB_DIR / "patrimoine.db"
SCHEMA_PATH  = ROOT / "schema" / "schema.sql"


# ── Helpers ───────────────────────────────────────────────────────────────────

def new_id() -> str:
    return str(uuid.uuid4())


def months_ago(n: int) -> str:
    d = date.today()
    year  = d.year  - (n // 12)
    month = d.month - (n % 12)
    if month <= 0:
        month += 12
        year  -= 1
    return date(year, month, 1).isoformat()


def date_offset(start_iso: str, months: int) -> str:
    """Ajoute N mois à une date ISO."""
    d = date.fromisoformat(start_iso)
    year  = d.year  + (months // 12)
    month = d.month + (months % 12)
    if month > 12:
        month -= 12
        year  += 1
    return date(year, month, d.day).isoformat()


# ── Données fictives ──────────────────────────────────────────────────────────

ACTIFS = [
    # id, type, nom, montant_actuel, courtier, enveloppe
    ("liv_a",   "livret",    "Livret A",             22_950.0,  "Boursorama",   "Livret réglementé"),
    ("ldds",    "livret",    "LDDS",                 12_000.0,  "Crédit Mutuel","Livret réglementé"),
    ("cw8",     "action",    "ETF World Amundi CW8", 38_400.0,  "Boursorama",   "PEA"),
    ("panx",    "action",    "ETF Nasdaq Amundi",    11_200.0,  "Boursorama",   "PEA"),
    ("aapl",    "action",    "Apple Inc.",           8_750.0,   "Degiro",       "CTO"),
    ("msft",    "action",    "Microsoft Corp.",      6_300.0,   "Degiro",       "CTO"),
    ("btc",     "crypto",    "Bitcoin",              9_800.0,   "Binance",      "Crypto (wallet/exchange)"),
    ("eth",     "crypto",    "Ethereum",             3_200.0,   "Binance",      "Crypto (wallet/exchange)"),
    ("av_fe",   "fonds_euro","Assurance Vie Spirica", 25_000.0, "Linxea",       "Assurance vie"),
    ("rp",      "immobilier","Résidence principale", 210_000.0, "Crédit Mutuel",""),
]

TICKERS = [
    # actif_id, ticker, quantite, pru
    ("cw8",  "CW8.PA",   48.0,  720.0),
    ("panx", "PANX.PA",  32.0,  315.0),
    ("aapl", "AAPL",     35.0,  220.0),
    ("msft", "MSFT",     18.0,  310.0),
    ("btc",  "BTC-USD",  0.12,  58_000.0),
    ("eth",  "ETH-USD",  1.8,   1_500.0),
]

EMPRUNT_ID = new_id()
EMPRUNTS = [
    # id, nom, montant_emprunte, taux, mensualite, duree_mois, date_debut
    (EMPRUNT_ID, "Prêt immobilier résidence principale",
     180_000.0, 2.85, 920.0, 240, months_ago(24)),
]

IMMOBILIER = [
    # actif_id, prix_achat, emprunt_id, type_bien, adresse, superficie_m2
    ("rp", 195_000.0, EMPRUNT_ID, "appartement", "12 rue des Lilas, Lyon", 68.0),
]

REFERENTIEL = [
    ("courtier", "Boursorama"),
    ("courtier", "Crédit Mutuel"),
    ("courtier", "Degiro"),
    ("courtier", "Binance"),
    ("courtier", "Linxea"),
    ("enveloppe", "PEA"),
    ("enveloppe", "CTO"),
    ("enveloppe", "Assurance vie"),
    ("enveloppe", "Livret réglementé"),
    ("enveloppe", "Crypto (wallet/exchange)"),
    ("enveloppe", "Compte courant"),
]


def build_historique():
    """
    Génère 13 points d'historique (mois -12 à aujourd'hui) pour les actifs manuels.
    On simule une progression douce et réaliste.
    """
    rows = []  # (asset_id, date, montant)

    # Livret A : de 20 000 → 22 950 (versements progressifs)
    livret_a = [20_000, 20_500, 21_000, 21_200, 21_500, 21_700,
                22_000, 22_100, 22_300, 22_500, 22_700, 22_950, 22_950]

    # LDDS : stable puis léger versement
    ldds = [10_000, 10_000, 10_500, 10_500, 11_000, 11_000,
            11_000, 11_500, 11_500, 12_000, 12_000, 12_000, 12_000]

    # Assurance vie fonds euros : croissance lente
    av = [20_000, 20_200, 20_400, 20_600, 20_800, 21_200,
          21_500, 22_000, 22_500, 23_000, 24_000, 25_000, 25_000]

    # Immo : valorisation légère
    immo = [195_000, 196_000, 197_000, 197_500, 198_000, 199_000,
            200_000, 201_000, 203_000, 205_000, 207_000, 210_000, 210_000]

    for i, (asset_id, serie) in enumerate([
        ("liv_a", livret_a),
        ("ldds",  ldds),
        ("av_fe", av),
        ("rp",    immo),
    ]):
        for month_offset, montant in enumerate(serie):
            d = months_ago(12 - month_offset)
            rows.append((asset_id, d, float(montant)))

    return rows


def build_positions():
    """
    Génère l'historique des positions (quantités) pour les actifs ticker.
    Simule des achats progressifs sur l'année.
    """
    rows = []  # (asset_id, date, quantite)

    positions = [
        # (asset_id, [(mois_depuis_debut, quantite_cumulee), ...])
        ("cw8",  [(0, 30.0), (3, 38.0), (6, 43.0), (9, 48.0)]),
        ("panx", [(0, 20.0), (4, 26.0), (8, 32.0)]),
        ("aapl", [(0, 25.0), (5, 30.0), (10, 35.0)]),
        ("msft", [(0, 12.0), (6, 15.0), (11, 18.0)]),
        ("btc",  [(0, 0.07), (4, 0.10), (9, 0.12)]),
        ("eth",  [(0, 1.0),  (5, 1.5),  (10, 1.8)]),
    ]

    start = months_ago(12)
    for asset_id, steps in positions:
        for months_offset, quantite in steps:
            d = date_offset(start, months_offset)
            rows.append((asset_id, d, float(quantite)))

    return rows


# ── Génération ─────────────────────────────────────────────────────────────────

def generate():
    os.makedirs(DEMO_DB_DIR, exist_ok=True)

    if DEMO_DB_PATH.exists():
        DEMO_DB_PATH.unlink()
        print(f"  Ancienne base supprimée.")

    # Créer les tables
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = f.read()

    conn = sqlite3.connect(str(DEMO_DB_PATH))
    conn.executescript(schema)

    # Actifs
    for (aid, type_, nom, montant, courtier, enveloppe) in ACTIFS:
        conn.execute(
            "INSERT INTO actifs (id, type, nom, montant_actuel, courtier, enveloppe) VALUES (?,?,?,?,?,?)",
            (aid, type_, nom, montant, courtier, enveloppe)
        )

    # Tickers
    for (aid, ticker, quantite, pru) in TICKERS:
        conn.execute(
            "INSERT INTO actifs_ticker (actif_id, ticker, quantite, pru) VALUES (?,?,?,?)",
            (aid, ticker, quantite, pru)
        )

    # Emprunt
    for (eid, nom, montant, taux, mens, duree, debut) in EMPRUNTS:
        conn.execute(
            """INSERT INTO emprunts (id, nom, montant_emprunte, taux_annuel, mensualite, duree_mois, date_debut)
               VALUES (?,?,?,?,?,?,?)""",
            (eid, nom, montant, taux, mens, duree, debut)
        )

    # Immobilier
    for (aid, prix, emp_id, type_bien, adresse, superficie) in IMMOBILIER:
        conn.execute(
            """INSERT INTO actifs_immobilier (actif_id, prix_achat, emprunt_id, type_bien, adresse, superficie_m2)
               VALUES (?,?,?,?,?,?)""",
            (aid, prix, emp_id, type_bien, adresse, superficie)
        )

    # Historique
    for (asset_id, d, montant) in build_historique():
        conn.execute(
            "INSERT OR REPLACE INTO historique (asset_id, date, montant) VALUES (?,?,?)",
            (asset_id, d, montant)
        )

    # Positions
    for (asset_id, d, quantite) in build_positions():
        conn.execute(
            "INSERT OR REPLACE INTO positions (asset_id, date, quantite) VALUES (?,?,?)",
            (asset_id, d, quantite)
        )

    # Référentiel
    for (kind, value) in REFERENTIEL:
        conn.execute(
            "INSERT OR IGNORE INTO referentiel (kind, value) VALUES (?,?)",
            (kind, value)
        )

    conn.commit()
    conn.close()

    print(f"  Base générée : {DEMO_DB_PATH}")
    print(f"  {len(ACTIFS)} actifs · {len(TICKERS)} tickers · {len(EMPRUNTS)} emprunt(s)")
    print(f"  {len(build_historique())} entrées historique · {len(build_positions())} entrées positions")


if __name__ == "__main__":
    print("Génération de la base de démo...")
    print("-" * 40)
    generate()
    print("-" * 40)
    print("Terminé ✓")