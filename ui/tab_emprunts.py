"""
ui/tab_emprunts.py
──────────────────
Onglet Passifs : liste des emprunts, ajout / modification / suppression (modales).
"""

import streamlit as st
import pandas as pd

from services.db_emprunts import load_emprunts, get_total_emprunts
from ui.emprunt_form import set_emprunt_dialog_create, set_emprunt_dialog_edit, set_emprunt_dialog_delete, _format_duree
import plotly.graph_objects as go
from datetime import date
from constants import PLOTLY_LAYOUT

def _build_crd_evolution(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule le CRD total mois par mois jusqu'à extinction du dernier emprunt."""
    from services.db_emprunts import _compute_capital_restant_du

    if df.empty:
        return pd.DataFrame()

    # Trouver la date de fin la plus lointaine
    today = date.today().replace(day=1)
    max_mois = int(df["duree_mois"].max())

    rows = []
    for i in range(max_mois + 1):
        d = (pd.Timestamp(today) + pd.DateOffset(months=i)).date()
        total = sum(
            _compute_capital_restant_du(
                row["montant_emprunte"],
                row["taux_annuel"],
                row["mensualite"],
                row["date_debut"],
                int(row["duree_mois"]),
                as_of_date=d,
            )
            for _, row in df.iterrows()
        )
        rows.append({"date": d, "crd": total})
        if total == 0.0:
            break

    return pd.DataFrame(rows)


def _render_crd_chart(df: pd.DataFrame) -> None:
    df_evo = _build_crd_evolution(df)
    if df_evo.empty:
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_evo["date"],
        y=df_evo["crd"],
        mode="lines",
        fill="tozeroy",
        line=dict(color="#75cbd1", width=2),
        fillcolor="rgba(117, 203, 209, 0.15)",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=220,
    )
    
    fig.update_yaxes(ticksuffix=" €", tickformat=",.0f")
    st.plotly_chart(fig, use_container_width=True, config={"staticPlot": True})

def _render_emprunt_row(row: pd.Series):
    cols = st.columns([6, 3, 1, 2, 2, 2, 0.5, 0.5])

    # Nom
    cols[0].write(row["nom"])
    date_debut = row.get("date_debut")
    if date_debut is not None and not (isinstance(date_debut, float) and pd.isna(date_debut)):
        cols[0].caption(f"Depuis {pd.Timestamp(date_debut).strftime('%b %Y')} · {_format_duree(int(row['duree_mois']))}")


    # Montant emprunté
    cols[1].write(f"{row['montant_emprunte']:,.0f} €")

    # Taux
    cols[2].write(f"{row['taux_annuel']:.2f} %")

    # Mensualité
    cols[3].write(f"{row['mensualite']:,.0f} €")

    # Capital restant dû
    crd = row.get("capital_restant_du")
    if crd is not None and not (isinstance(crd, float) and pd.isna(crd)):
        cols[4].write(f"{crd:,.0f} €")
    else:
        cols[4].caption("—")

    # Remboursé
    montant_emprunte = float(row["montant_emprunte"])
    if crd is not None and not (isinstance(crd, float) and pd.isna(crd)) and montant_emprunte > 0:
        capital_rembourse = montant_emprunte - float(crd)
        cols[5].write(f"{capital_rembourse:,.0f} €")
    else:
        cols[5].caption("—")

    # Actions
    if cols[6].button("", key=f"emprunt_edit_{row['id']}", icon=":material/edit_square:", help="Modifier"):
        set_emprunt_dialog_edit(row["id"])
        st.rerun()
    if cols[7].button("", key=f"emprunt_del_{row['id']}", icon=":material/delete:", help="Supprimer"):
        set_emprunt_dialog_delete(row["id"])
        st.rerun()

# Barre de progression + détail coût total
    interets_totaux = row["mensualite"] * row["duree_mois"] - montant_emprunte
    cout_total = montant_emprunte + interets_totaux

    if crd is not None and not (isinstance(crd, float) and pd.isna(crd)) and montant_emprunte > 0:
        capital_rembourse = montant_emprunte - float(crd)
        pct = capital_rembourse / montant_emprunte

        with cols[0]:
            with st.container(horizontal=True):
                st.progress(value=pct)
                st.caption(f"{pct*100:.0f}%")
        with cols[1]:
            st.caption(f"Intérêts {interets_totaux:,.0f} €")
            st.caption(f"Coût total {cout_total:,.0f} €")


def _compute_interets_restants(row: pd.Series) -> float:
    """Intérêts restant à payer = paiements futurs - capital restant dû."""
    from datetime import date as date_type
    crd = row.get("capital_restant_du") or 0.0
    if not row.get("date_debut") or pd.isna(row["date_debut"]):
        return 0.0
    debut = pd.Timestamp(row["date_debut"]).date()
    today = date_type.today()
    months_elapsed = (today.year - debut.year) * 12 + (today.month - debut.month)
    if debut.day > today.day:
        months_elapsed -= 1
    months_elapsed = max(0, min(months_elapsed, int(row["duree_mois"])))
    months_remaining = int(row["duree_mois"]) - months_elapsed
    return max(0.0, float(row["mensualite"]) * months_remaining - float(crd))


def render(flash_fn) -> None:
    df = load_emprunts()
    total_crd = get_total_emprunts()

# ── Métriques clés ─────────────────────────────────────────────────────────
    total_mensualites = float(df["mensualite"].sum()) if not df.empty else 0.0
    total_emprunte = float(df["montant_emprunte"].sum()) if not df.empty else 0.0
    total_interets_restants = float(df.apply(_compute_interets_restants, axis=1).sum()) if not df.empty else 0.0

    from services.db_parametres import get_parametre
    revenu = get_parametre("revenu_mensuel_net")
    revenu_val = float(revenu) if revenu else None
    taux_endettement = (total_mensualites / revenu_val * 100) if revenu_val and revenu_val > 0 else None

    with st.container(horizontal=True):
        st.metric("Total emprunté", f"{total_emprunte:,.0f} €", border=True)
        st.metric("Mensualités / mois", f"{total_mensualites:,.0f} €", border=True)
        st.metric("Capital restant dû", f"{total_crd:,.0f} €", border=True)
        st.metric("Intérêts restants", f"{total_interets_restants:,.0f} €", border=True)
        if taux_endettement is not None:
            alerte = ":red[:material/error:]" if taux_endettement > 35 else ":orange[:material/warning:]" if taux_endettement > 30 else ":green[:material/check_circle:]"
            st.metric(
                "Taux d'endettement",
                f"{alerte} {taux_endettement:.1f} %",
                border=True,
                help="Mensualités ÷ revenus nets. Seuil bancaire : 35 %."
            )
        else:
            st.metric(
                "Taux d'endettement",
                "?",
                border=True,
                help="Renseigne ton revenu mensuel net dans Paramètres pour voir ce calcul."
            )
    st.space(size="small")

    # ── Graphique évolution CRD ───────────────────────────────────────────────
    if not df.empty:
        _render_crd_chart(df)

    with st.container(horizontal=True, vertical_alignment="center"):
        st.write("")
        if st.button("Ajouter un emprunt", type="primary", key="btn_add_emprunt", icon=":material/add:"):
            set_emprunt_dialog_create()
            st.rerun()

    st.space(size="small")

    if df.empty:
        st.info("Aucun emprunt pour l'instant. Ajoute un prêt immobilier, un crédit conso, etc.")
        return

    # ── En-tête des colonnes ──────────────────────────────────────────────────
    header_cols = st.columns([6, 3, 1, 2, 2, 2, 0.5, 0.5])
    header_cols[0].empty()
    header_cols[1].caption("Montant emprunté")
    header_cols[2].caption("Taux")
    header_cols[3].caption("Mensualité")
    header_cols[4].caption("Restant dû")
    header_cols[5].caption("Remboursé")

    # ── Liste des emprunts ────────────────────────────────────────────────────
    for _, row in df.iterrows():
        with st.container(border=True, vertical_alignment="center"):
            _render_emprunt_row(row)