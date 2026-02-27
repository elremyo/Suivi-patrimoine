"""
tests/test_asset_manager.py
────────────────────────────
Tests des séquences métier dans services/asset_manager.py.

On utilise tmp_path (fixture pytest intégrée) et monkeypatch pour :
- Rediriger les écritures CSV vers un dossier temporaire
- Éviter d'appeler yfinance (réseau) dans les tests
"""

import pytest
import pandas as pd
from unittest.mock import patch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_empty_df():
    return pd.DataFrame(
        columns=["id", "nom", "categorie", "montant", "ticker", "quantite", "pru"]
    )


# ── Tests create_manual_asset ─────────────────────────────────────────────────

class TestCreateManualAsset:

    def test_ajoute_un_actif_au_dataframe(self, tmp_path):
        with patch("services.storage.DATA_PATH", str(tmp_path / "assets.csv")), \
             patch("services.historique.HISTORIQUE_PATH", str(tmp_path / "historique.csv")), \
             patch("constants.DATA_PATH", str(tmp_path / "assets.csv")), \
             patch("constants.HISTORIQUE_PATH", str(tmp_path / "historique.csv")):

            from services.asset_manager import create_manual_asset
            df = _make_empty_df()
            df_result, msg, msg_type = create_manual_asset(df, "Livret A", "Livrets", 10000.0)

            assert len(df_result) == 1
            assert df_result.iloc[0]["nom"] == "Livret A"
            assert df_result.iloc[0]["categorie"] == "Livrets"
            assert df_result.iloc[0]["montant"] == 10000.0

    def test_retourne_success(self, tmp_path):
        with patch("services.storage.DATA_PATH", str(tmp_path / "assets.csv")), \
             patch("services.historique.HISTORIQUE_PATH", str(tmp_path / "historique.csv")), \
             patch("constants.DATA_PATH", str(tmp_path / "assets.csv")), \
             patch("constants.HISTORIQUE_PATH", str(tmp_path / "historique.csv")):

            from services.asset_manager import create_manual_asset
            df = _make_empty_df()
            _, msg, msg_type = create_manual_asset(df, "Livret A", "Livrets", 10000.0)

            assert msg_type == "success"
            assert len(msg) > 0

    def test_actif_a_un_uuid(self, tmp_path):
        with patch("services.storage.DATA_PATH", str(tmp_path / "assets.csv")), \
             patch("services.historique.HISTORIQUE_PATH", str(tmp_path / "historique.csv")), \
             patch("constants.DATA_PATH", str(tmp_path / "assets.csv")), \
             patch("constants.HISTORIQUE_PATH", str(tmp_path / "historique.csv")):

            from services.asset_manager import create_manual_asset
            df = _make_empty_df()
            df_result, _, _ = create_manual_asset(df, "Test", "Livrets", 1000.0)

            asset_id = df_result.iloc[0]["id"]
            assert asset_id is not None
            assert len(str(asset_id)) > 0


# ── Tests remove_asset ────────────────────────────────────────────────────────

class TestRemoveAsset:

    def test_supprime_actif_du_dataframe(self, tmp_path):
        with patch("services.storage.DATA_PATH", str(tmp_path / "assets.csv")), \
             patch("services.historique.HISTORIQUE_PATH", str(tmp_path / "historique.csv")), \
             patch("services.positions.POSITIONS_PATH", str(tmp_path / "positions.csv")), \
             patch("constants.DATA_PATH", str(tmp_path / "assets.csv")):

            from services.asset_manager import remove_asset
            df = pd.DataFrame([{
                "id": "aaa", "nom": "Livret A", "categorie": "Livrets",
                "montant": 10000.0, "ticker": "", "quantite": 0.0, "pru": 0.0
            }])
            df_result, msg, msg_type = remove_asset(df, 0, "aaa")

            assert df_result.empty
            assert msg_type == "success"

    def test_ne_supprime_pas_les_autres_actifs(self, tmp_path):
        with patch("services.storage.DATA_PATH", str(tmp_path / "assets.csv")), \
             patch("services.historique.HISTORIQUE_PATH", str(tmp_path / "historique.csv")), \
             patch("services.positions.POSITIONS_PATH", str(tmp_path / "positions.csv")), \
             patch("constants.DATA_PATH", str(tmp_path / "assets.csv")):

            from services.asset_manager import remove_asset
            df = pd.DataFrame([
                {"id": "aaa", "nom": "Livret A", "categorie": "Livrets",
                 "montant": 10000.0, "ticker": "", "quantite": 0.0, "pru": 0.0},
                {"id": "bbb", "nom": "Livret B", "categorie": "Livrets",
                 "montant": 5000.0, "ticker": "", "quantite": 0.0, "pru": 0.0},
            ])
            df_result, _, _ = remove_asset(df, 0, "aaa")

            assert len(df_result) == 1
            assert df_result.iloc[0]["id"] == "bbb"