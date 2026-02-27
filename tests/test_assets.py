"""
tests/test_assets.py
─────────────────────
Tests des fonctions de calcul dans services/assets.py.
Ces fonctions sont pures (pas d'I/O) : faciles à tester, zéro mock nécessaire.
"""

import pytest
import pandas as pd
from services.assets import compute_total, compute_by_category


class TestComputeTotal:

    def test_retourne_zero_si_vide(self, df_assets_vide):
        assert compute_total(df_assets_vide) == 0.0

    def test_somme_correcte(self, df_assets_simple):
        # 10 000 + 200 000 + 1 500 = 211 500
        assert compute_total(df_assets_simple) == 211_500.0

    def test_un_seul_actif(self):
        df = pd.DataFrame([
            {"id": "x", "nom": "Test", "categorie": "Livrets",
             "montant": 5000.0, "ticker": "", "quantite": 0.0, "pru": 0.0}
        ])
        assert compute_total(df) == 5000.0

    def test_avec_montants_decimaux(self):
        df = pd.DataFrame([
            {"id": "x", "nom": "A", "categorie": "Livrets", "montant": 1234.56,
             "ticker": "", "quantite": 0.0, "pru": 0.0},
            {"id": "y", "nom": "B", "categorie": "Livrets", "montant": 0.44,
             "ticker": "", "quantite": 0.0, "pru": 0.0},
        ])
        assert compute_total(df) == pytest.approx(1235.0)


class TestComputeByCategory:

    def test_retourne_dataframe_vide_si_assets_vide(self, df_assets_vide):
        result = compute_by_category(df_assets_vide)
        assert result.empty
        assert list(result.columns) == ["categorie", "montant", "pourcentage"]

    def test_colonnes_presentes(self, df_assets_simple):
        result = compute_by_category(df_assets_simple)
        assert list(result.columns) == ["categorie", "montant", "pourcentage"]

    def test_somme_des_pourcentages_egale_100(self, df_assets_simple):
        result = compute_by_category(df_assets_simple)
        assert result["pourcentage"].sum() == pytest.approx(100.0, abs=0.1)

    def test_trie_par_montant_decroissant(self, df_assets_simple):
        result = compute_by_category(df_assets_simple)
        montants = result["montant"].tolist()
        assert montants == sorted(montants, reverse=True)

    def test_regroupe_deux_actifs_meme_categorie(self):
        df = pd.DataFrame([
            {"id": "a", "nom": "Livret A", "categorie": "Livrets", "montant": 10000.0,
             "ticker": "", "quantite": 0.0, "pru": 0.0},
            {"id": "b", "nom": "Livret B", "categorie": "Livrets", "montant": 5000.0,
             "ticker": "", "quantite": 0.0, "pru": 0.0},
        ])
        result = compute_by_category(df)
        assert len(result) == 1
        assert result.iloc[0]["montant"] == 15000.0
        assert result.iloc[0]["pourcentage"] == pytest.approx(100.0)

    def test_pourcentage_calcule_correctement(self):
        df = pd.DataFrame([
            {"id": "a", "nom": "A", "categorie": "Livrets",    "montant": 75000.0,
             "ticker": "", "quantite": 0.0, "pru": 0.0},
            {"id": "b", "nom": "B", "categorie": "Immobilier", "montant": 25000.0,
             "ticker": "", "quantite": 0.0, "pru": 0.0},
        ])
        result = compute_by_category(df)
        livrets = result[result["categorie"] == "Livrets"].iloc[0]
        immo = result[result["categorie"] == "Immobilier"].iloc[0]
        assert livrets["pourcentage"] == pytest.approx(75.0)
        assert immo["pourcentage"] == pytest.approx(25.0)