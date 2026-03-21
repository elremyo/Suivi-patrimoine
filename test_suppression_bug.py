"""
Test pour vérifier la suppression des données liées lors de la suppression d'un actif
"""
import pytest
import pandas as pd
from datetime import date

def _make_empty_df():
    return pd.DataFrame(
        columns=["id", "nom", "categorie", "montant", "ticker", "quantite", "pru", "contrat_id"]
    )

def _patch_db_path(tmp_path):
    """Patch constants.DB_PATH pour utiliser une base SQLite temporaire."""
    from unittest.mock import patch
    return patch("constants.DB_PATH", str(tmp_path / "patrimoine.db"))

def _init_storage():
    """Crée la base et les tables (à appeler après le patch DB_PATH)."""
    from services.db import init_db
    init_db()

def test_suppression_actif_supprime_donnees_liees(tmp_path):
    """Vérifie que la suppression d'un actif supprime bien l'historique et les positions"""
    with _patch_db_path(tmp_path):
        _init_storage()
        
        # Créer un actif manuel avec historique
        from services.asset_manager import create_manual_asset, remove_asset
        from services.historique import load_historique
        from services.positions import load_positions
        
        df = _make_empty_df()
        df, _, _ = create_manual_asset(df, "Test Actif", "Livrets", 1000.0)
        asset_id = df.iloc[0]["id"]
        
        # Ajouter des données historiques supplémentaires
        from services.historique import record_montant
        record_montant(asset_id, 1200.0, date(2024, 1, 1))
        record_montant(asset_id, 1100.0, date(2024, 2, 1))
        
        # Vérifier que les données existent avant suppression
        historique_avant = load_historique()
        positions_avant = load_positions()
        
        print(f"Historique avant suppression: {len(historique_avant)} entrées")
        print(f"Positions avant suppression: {len(positions_avant)} entrées")
        
        # Supprimer l'actif
        df, _, _ = remove_asset(df, 0, asset_id)
        
        # Vérifier que les données sont supprimées après suppression
        historique_apres = load_historique()
        positions_apres = load_positions()
        
        print(f"Historique après suppression: {len(historique_apres)} entrées")
        print(f"Positions après suppression: {len(positions_apres)} entrées")
        
        # L'actif ne devrait plus avoir d'historique ou de positions
        historique_asset_apres = historique_apres[historique_apres["asset_id"] == asset_id]
        positions_asset_apres = positions_apres[positions_apres["asset_id"] == asset_id]
        
        assert len(historique_asset_apres) == 0, f"L'historique de l'actif {asset_id} devrait être vide"
        assert len(positions_asset_apres) == 0, f"Les positions de l'actif {asset_id} devraient être vides"

if __name__ == "__main__":
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_suppression_actif_supprime_donnees_liees(tmp_dir)
