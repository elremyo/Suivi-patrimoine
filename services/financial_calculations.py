"""
services/financial_calculations.py
──────────────────────────────────
Module utilitaire pour les calculs financiers communs.
Évite la duplication de code entre tab_actifs.py et asset_detail.py.
"""

import pandas as pd
from typing import Dict, Tuple, Optional
from services.db_emprunts import load_emprunts


def calculate_immo_real_cost(prix_achat: float, frais_notaire: float, montant_travaux: float) -> float:
    """
    Calcule le coût réel d'acquisition d'un bien immobilier.
    
    Args:
        prix_achat: Prix d'achat du bien
        frais_notaire: Frais de notaire
        montant_travaux: Coût des travaux
        
    Returns:
        Coût réel total
    """
    return prix_achat + frais_notaire + montant_travaux


def calculate_rental_yield(loyer_mensuel: float, charges_mensuelles: float, cout_reel: float) -> float:
    """
    Calcule le rendement brut d'un investissement locatif.
    
    Args:
        loyer_mensuel: Loyer mensuel brut
        charges_mensuelles: Charges mensuelles
        cout_reel: Coût réel d'acquisition
        
    Returns:
        Rendement brut en pourcentage
    """
    if loyer_mensuel <= 0 or cout_reel <= 0:
        return 0.0
    return (loyer_mensuel - charges_mensuelles) * 12 / cout_reel * 100


def calculate_monthly_cashflow(loyer_mensuel: float, charges_mensuelles: float, 
                             taxe_fonciere_annuelle: float, mensualite_emprunt: float) -> float:
    """
    Calcule le cashflow mensuel d'un investissement locatif.
    
    Args:
        loyer_mensuel: Loyer mensuel brut
        charges_mensuelles: Charges mensuelles
        taxe_fonciere_annuelle: Taxe foncière annuelle
        mensualite_emprunt: Mensualité de l'emprunt
        
    Returns:
        Cashflow mensuel en euros
    """
    return loyer_mensuel - charges_mensuelles - taxe_fonciere_annuelle / 12 - mensualite_emprunt


def get_loan_monthly_payment(emprunt_id: str) -> float:
    """
    Récupère la mensualité d'un emprunt à partir de son ID.
    
    Args:
        emprunt_id: ID de l'emprunt
        
    Returns:
        Mensualité de l'emprunt (0.0 si non trouvé)
    """
    if not emprunt_id or pd.isna(emprunt_id):
        return 0.0
    
    try:
        df_emprunts = load_emprunts()
        emp = df_emprunts[df_emprunts["id"] == str(emprunt_id)]
        if not emp.empty:
            return float(emp.iloc[0]["mensualite"])
    except Exception:
        pass
    
    return 0.0


def calculate_rental_metrics(asset: pd.Series) -> Dict[str, float]:
    """
    Calcule toutes les métriques locatives pour un bien immobilier.
    
    Args:
        asset: Série pandas contenant les données de l'actif
        
    Returns:
        Dictionnaire avec les métriques calculées
    """
    # Extraire les données de l'actif
    loyer = float(asset.get("loyer_mensuel") or 0)
    charges = float(asset.get("charges_mensuelles") or 0)
    taxe = float(asset.get("taxe_fonciere_annuelle") or 0)
    prix_achat = float(asset.get("prix_achat") or 0)
    frais_notaire = float(asset.get("frais_notaire") or 0)
    montant_travaux = float(asset.get("montant_travaux") or 0)
    
    # Calculer le coût réel
    cout_reel = calculate_immo_real_cost(prix_achat, frais_notaire, montant_travaux)
    
    # Récupérer la mensualité d'emprunt si applicable
    emprunt_id = asset.get("emprunt_id")
    mensualite = get_loan_monthly_payment(emprunt_id) if emprunt_id else 0.0
    
    # Calculer les métriques
    rendement_brut = calculate_rental_yield(loyer, charges, cout_reel)
    cashflow = calculate_monthly_cashflow(loyer, charges, taxe, mensualite)
    
    return {
        "cout_reel": cout_reel,
        "rendement_brut": rendement_brut,
        "cashflow_mensuel": cashflow,
        "mensualite_emprunt": mensualite
    }


def calculate_investment_performance(prix_achat: float, frais_notaire: float, 
                                   montant_travaux: float, valeur_actuelle: float) -> Dict[str, float]:
    """
    Calcule la performance d'un investissement immobilier.
    
    Args:
        prix_achat: Prix d'achat
        frais_notaire: Frais de notaire
        montant_travaux: Montant des travaux
        valeur_actuelle: Valeur actuelle du bien
        
    Returns:
        Dictionnaire avec plus-value et pourcentage
    """
    cout_reel = calculate_immo_real_cost(prix_achat, frais_notaire, montant_travaux)
    plus_value = valeur_actuelle - cout_reel
    plus_value_pct = (plus_value / cout_reel * 100) if cout_reel > 0 else 0
    
    return {
        "cout_reel": cout_reel,
        "plus_value": plus_value,
        "plus_value_pct": plus_value_pct
    }


def calculate_auto_asset_pnl(montant_actuel: float, pru: float, quantite: float) -> Dict[str, float]:
    """
    Calcule le PnL pour un actif automatique (actions, crypto, etc.).
    
    Args:
        montant_actuel: Montant actuel de l'actif
        pru: Prix de revient unitaire
        quantite: Quantité détenue
        
    Returns:
        Dictionnaire avec PnL absolu et en pourcentage
    """
    if pru <= 0 or quantite <= 0:
        return {"pnl_absolu": 0.0, "pnl_pct": 0.0, "valeur_achat": 0.0}
    
    valeur_achat = pru * quantite
    pnl = montant_actuel - valeur_achat
    pnl_pct = (pnl / valeur_achat * 100) if valeur_achat > 0 else 0
    
    return {
        "valeur_achat": valeur_achat,
        "pnl_absolu": pnl,
        "pnl_pct": pnl_pct
    }
