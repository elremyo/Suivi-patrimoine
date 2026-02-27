"""
tests/test_historique.py
─────────────────────────
Tests des fonctions de consultation de l'historique dans services/historique.py.
On teste uniquement les fonctions pures (lecture/calcul) — pas les écritures CSV.
"""

import pytest
import pandas as pd
from services.historique import get_montant_at, build_total_evolution


class TestGetMontantAt:

    def test_retourne_none_si_historique_vide(self, df_hist_vide):
        result = get_montant_at("aaa", pd.Timestamp("2024-06-01"), df_hist_vide)
        assert result is None

    def test_retourne_none_si_asset_inconnu(self, df_hist_simple):
        result = get_montant_at("inconnu", pd.Timestamp("2024-06-01"), df_hist_simple)
        assert result is None

    def test_retourne_none_si_date_avant_premier_enregistrement(self, df_hist_simple):
        # Premier enregistrement de "aaa" est le 2024-01-01
        result = get_montant_at("aaa", pd.Timestamp("2023-12-31"), df_hist_simple)
        assert result is None

    def test_retourne_montant_exact_a_la_date(self, df_hist_simple):
        result = get_montant_at("aaa", pd.Timestamp("2024-01-01"), df_hist_simple)
        assert result == 9000.0

    def test_retourne_dernier_montant_connu_avant_date(self, df_hist_simple):
        # Entre 2024-01-01 (9000) et 2024-06-01 (9500), on doit avoir 9000
        result = get_montant_at("aaa", pd.Timestamp("2024-03-15"), df_hist_simple)
        assert result == 9000.0

    def test_retourne_montant_le_plus_recent_avant_date(self, df_hist_simple):
        # Après 2024-06-01 (9500) mais avant 2024-12-01 (10000)
        result = get_montant_at("aaa", pd.Timestamp("2024-09-01"), df_hist_simple)
        assert result == 9500.0

    def test_retourne_dernier_montant_apres_toutes_les_dates(self, df_hist_simple):
        result = get_montant_at("aaa", pd.Timestamp("2025-01-01"), df_hist_simple)
        assert result == 10000.0


class TestBuildTotalEvolution:

    def test_retourne_vide_si_assets_vide(self, df_hist_simple, df_positions_vide):
        df_assets_vide = pd.DataFrame(
            columns=["id", "nom", "categorie", "montant", "ticker", "quantite", "pru"]
        )
        result = build_total_evolution(
            df_assets_vide, df_hist_simple, df_positions_vide,
            pd.DataFrame(), set()
        )
        assert result.empty

    def test_retourne_vide_si_aucune_donnee_historique(self, df_assets_simple):
        result = build_total_evolution(
            df_assets_simple,
            pd.DataFrame(columns=["asset_id", "date", "montant"]),
            pd.DataFrame(columns=["asset_id", "date", "quantite"]),
            pd.DataFrame(),
            {"Actions & Fonds", "Crypto"},
        )
        assert result.empty

    def test_contient_colonnes_date_et_total(self, df_assets_simple, df_hist_simple, df_positions_vide):
        # On exclut l'actif auto pour ce test (pas de prix yfinance)
        df_manuels = df_assets_simple[df_assets_simple["categorie"].isin(["Livrets", "Immobilier"])]
        result = build_total_evolution(
            df_manuels, df_hist_simple, df_positions_vide,
            pd.DataFrame(), {"Actions & Fonds", "Crypto"},
        )
        assert "date" in result.columns
        assert "total" in result.columns

    def test_total_est_positif(self, df_assets_simple, df_hist_simple, df_positions_vide):
        df_manuels = df_assets_simple[df_assets_simple["categorie"].isin(["Livrets", "Immobilier"])]
        result = build_total_evolution(
            df_manuels, df_hist_simple, df_positions_vide,
            pd.DataFrame(), {"Actions & Fonds", "Crypto"},
        )
        assert (result["total"] > 0).all()

    def test_dates_sont_triees_chronologiquement(self, df_assets_simple, df_hist_simple, df_positions_vide):
        df_manuels = df_assets_simple[df_assets_simple["categorie"].isin(["Livrets", "Immobilier"])]
        result = build_total_evolution(
            df_manuels, df_hist_simple, df_positions_vide,
            pd.DataFrame(), {"Actions & Fonds", "Crypto"},
        )
        assert result["date"].is_monotonic_increasing

    def test_total_a_date_connue(self, df_hist_simple, df_positions_vide):
        """À 2024-01-01 : Livret A = 9000, Immobilier = 195000 → total = 204000."""
        df_manuels = pd.DataFrame([
            {"id": "aaa", "nom": "Livret A",    "categorie": "Livrets",    "montant": 10000.0, "ticker": "", "quantite": 0.0, "pru": 0.0},
            {"id": "bbb", "nom": "Appartement", "categorie": "Immobilier", "montant": 200000.0,"ticker": "", "quantite": 0.0, "pru": 0.0},
        ])
        result = build_total_evolution(
            df_manuels, df_hist_simple, df_positions_vide,
            pd.DataFrame(), {"Actions & Fonds", "Crypto"},
        )
        row = result[result["date"] == pd.Timestamp("2024-01-01")]
        assert not row.empty
        assert row.iloc[0]["total"] == pytest.approx(204_000.0)