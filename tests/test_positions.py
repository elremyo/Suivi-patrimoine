"""
tests/test_positions.py
────────────────────────
Tests de get_quantity_at dans services/positions.py.
Fonction critique : utilisée dans tous les calculs d'actifs automatiques.
"""

import pytest
import pandas as pd
from services.positions import get_quantity_at


class TestGetQuantityAt:

    def test_retourne_none_si_positions_vide(self, df_positions_vide):
        result = get_quantity_at("ccc", pd.Timestamp("2024-06-01"), df_positions_vide)
        assert result is None

    def test_retourne_none_si_asset_inconnu(self, df_positions_simple):
        result = get_quantity_at("inconnu", pd.Timestamp("2024-06-01"), df_positions_simple)
        assert result is None

    def test_retourne_none_si_date_avant_premiere_position(self, df_positions_simple):
        # Première position de "ccc" est le 2024-01-01
        result = get_quantity_at("ccc", pd.Timestamp("2023-12-31"), df_positions_simple)
        assert result is None

    def test_retourne_quantite_exacte_a_la_date(self, df_positions_simple):
        result = get_quantity_at("ccc", pd.Timestamp("2024-01-01"), df_positions_simple)
        assert result == 5.0

    def test_retourne_derniere_quantite_connue_avant_date(self, df_positions_simple):
        # Entre 2024-01-01 (5.0) et 2024-06-01 (10.0), on doit avoir 5.0
        result = get_quantity_at("ccc", pd.Timestamp("2024-03-15"), df_positions_simple)
        assert result == 5.0

    def test_retourne_quantite_apres_mise_a_jour(self, df_positions_simple):
        # Après le 2024-06-01 (10.0)
        result = get_quantity_at("ccc", pd.Timestamp("2024-07-01"), df_positions_simple)
        assert result == 10.0

    def test_retourne_float(self, df_positions_simple):
        result = get_quantity_at("ccc", pd.Timestamp("2024-06-01"), df_positions_simple)
        assert isinstance(result, float)

    def test_quantite_fractionnaire(self):
        """Cas crypto : quantités non entières."""
        df = pd.DataFrame([
            {"asset_id": "btc", "date": pd.Timestamp("2024-01-01"), "quantite": 0.00542},
        ])
        result = get_quantity_at("btc", pd.Timestamp("2024-06-01"), df)
        assert result == pytest.approx(0.00542)