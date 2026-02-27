"""
tests/conftest.py
─────────────────
Fixtures pytest partagées entre tous les fichiers de test.
Un fixture = une fonction qui prépare des données réutilisables.
"""

import pytest
import pandas as pd


# ── Fixtures actifs ───────────────────────────────────────────────────────────

@pytest.fixture
def df_assets_vide():
    """DataFrame d'actifs vide avec les bonnes colonnes."""
    return pd.DataFrame(columns=["id", "nom", "categorie", "montant", "ticker", "quantite", "pru"])


@pytest.fixture
def df_assets_simple():
    """Quelques actifs représentatifs pour les tests."""
    return pd.DataFrame([
        {"id": "aaa", "nom": "Livret A",    "categorie": "Livrets",        "montant": 10000.0, "ticker": "",        "quantite": 0.0, "pru": 0.0},
        {"id": "bbb", "nom": "Appartement", "categorie": "Immobilier",     "montant": 200000.0,"ticker": "",        "quantite": 0.0, "pru": 0.0},
        {"id": "ccc", "nom": "Apple",       "categorie": "Actions & Fonds","montant": 1500.0,  "ticker": "AAPL",   "quantite": 10.0,"pru": 130.0},
    ])


# ── Fixtures historique ───────────────────────────────────────────────────────

@pytest.fixture
def df_hist_vide():
    """DataFrame historique vide."""
    return pd.DataFrame(columns=["asset_id", "date", "montant"])


@pytest.fixture
def df_hist_simple():
    """Historique avec quelques entrées sur deux actifs."""
    return pd.DataFrame([
        {"asset_id": "aaa", "date": pd.Timestamp("2024-01-01"), "montant": 9000.0},
        {"asset_id": "aaa", "date": pd.Timestamp("2024-06-01"), "montant": 9500.0},
        {"asset_id": "aaa", "date": pd.Timestamp("2024-12-01"), "montant": 10000.0},
        {"asset_id": "bbb", "date": pd.Timestamp("2024-01-01"), "montant": 195000.0},
        {"asset_id": "bbb", "date": pd.Timestamp("2024-12-01"), "montant": 200000.0},
    ])


# ── Fixtures positions ────────────────────────────────────────────────────────

@pytest.fixture
def df_positions_vide():
    """DataFrame positions vide."""
    return pd.DataFrame(columns=["asset_id", "date", "quantite"])


@pytest.fixture
def df_positions_simple():
    """Positions avec un historique d'achats progressifs."""
    return pd.DataFrame([
        {"asset_id": "ccc", "date": pd.Timestamp("2024-01-01"), "quantite": 5.0},
        {"asset_id": "ccc", "date": pd.Timestamp("2024-06-01"), "quantite": 10.0},
    ])