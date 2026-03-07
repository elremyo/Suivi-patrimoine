"""
tests/test_asset_manager.py
────────────────────────────
Tests des séquences métier dans services/asset_manager.py.

On utilise tmp_path et on redirige la base SQLite vers un fichier temporaire
pour isoler les tests. yfinance est mocké pour éviter le réseau.
"""

import pytest
import pandas as pd
from unittest.mock import patch


def _make_empty_df():
    return pd.DataFrame(
        columns=["id", "nom", "categorie", "montant", "ticker", "quantite", "pru", "courtier", "enveloppe"]
    )


def _patch_db_path(tmp_path):
    """Patch constants.DB_PATH pour utiliser une base SQLite temporaire."""
    return patch("constants.DB_PATH", str(tmp_path / "patrimoine.db"))


def _init_storage():
    """Crée la base et les tables (à appeler après le patch DB_PATH)."""
    from services.storage import init_storage
    init_storage()


# ── Tests create_manual_asset ─────────────────────────────────────────────────

class TestCreateManualAsset:

    def test_ajoute_un_actif_au_dataframe(self, tmp_path):
        with _patch_db_path(tmp_path):
            _init_storage()
            from services.asset_manager import create_manual_asset
            df = _make_empty_df()
            df_result, msg, msg_type = create_manual_asset(df, "Livret A", "Livrets", 10000.0)

            assert len(df_result) == 1
            assert df_result.iloc[0]["nom"] == "Livret A"
            assert df_result.iloc[0]["categorie"] == "Livrets"
            assert df_result.iloc[0]["montant"] == 10000.0

    def test_retourne_success(self, tmp_path):
        with _patch_db_path(tmp_path):
            _init_storage()
            from services.asset_manager import create_manual_asset
            df = _make_empty_df()
            _, msg, msg_type = create_manual_asset(df, "Livret A", "Livrets", 10000.0)

            assert msg_type == "success"
            assert len(msg) > 0

    def test_actif_a_un_uuid(self, tmp_path):
        with _patch_db_path(tmp_path):
            _init_storage()
            from services.asset_manager import create_manual_asset
            df = _make_empty_df()
            df_result, _, _ = create_manual_asset(df, "Test", "Livrets", 1000.0)

            asset_id = df_result.iloc[0]["id"]
            assert asset_id is not None
            assert len(str(asset_id)) > 0

    def test_colonnes_courtier_enveloppe_presentes(self, tmp_path):
        """Les colonnes courtier et enveloppe doivent exister."""
        with _patch_db_path(tmp_path):
            _init_storage()
            from services.asset_manager import create_manual_asset
            df = _make_empty_df()
            df_result, _, _ = create_manual_asset(df, "Livret A", "Livrets", 10000.0,
                                                   courtier="Banque", enveloppe="Livret réglementé")

            assert df_result.iloc[0]["courtier"] == "Banque"
            assert df_result.iloc[0]["enveloppe"] == "Livret réglementé"


# ── Tests remove_asset ────────────────────────────────────────────────────────

class TestRemoveAsset:

    def test_supprime_actif_du_dataframe(self, tmp_path):
        with _patch_db_path(tmp_path):
            _init_storage()
            from services.asset_manager import remove_asset
            df = pd.DataFrame([{
                "id": "aaa", "nom": "Livret A", "categorie": "Livrets",
                "montant": 10000.0, "ticker": "", "quantite": 0.0, "pru": 0.0,
                "courtier": "", "enveloppe": ""
            }])
            df_result, msg, msg_type = remove_asset(df, 0, "aaa")

            assert df_result.empty
            assert msg_type == "success"

    def test_ne_supprime_pas_les_autres_actifs(self, tmp_path):
        with _patch_db_path(tmp_path):
            _init_storage()
            from services.asset_manager import remove_asset
            df = pd.DataFrame([
                {"id": "aaa", "nom": "Livret A", "categorie": "Livrets",
                 "montant": 10000.0, "ticker": "", "quantite": 0.0, "pru": 0.0,
                 "courtier": "", "enveloppe": ""},
                {"id": "bbb", "nom": "Livret B", "categorie": "Livrets",
                 "montant": 5000.0, "ticker": "", "quantite": 0.0, "pru": 0.0,
                 "courtier": "", "enveloppe": ""},
            ])
            df_result, _, _ = remove_asset(df, 0, "aaa")

            assert len(df_result) == 1
            assert df_result.iloc[0]["id"] == "bbb"