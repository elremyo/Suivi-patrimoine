import streamlit as st
import plotly.graph_objects as go
from services.storage import init_storage, download_assets
from services.assets import (
    get_assets, add_asset, update_asset, delete_asset,
    compute_total, compute_by_category,
)
from services.historique import (
    init_historique, load_historique, save_snapshot, delete_snapshot,
    get_total_evolution, get_category_evolution, get_snapshot_table,
)
from constants import CATEGORIES_ASSETS

st.set_page_config(page_title="Suivi Patrimoine", layout="wide")
init_storage()
init_historique()

st.title("Suivi de patrimoine")

df = get_assets()

# ── Liste des actifs ──────────────────────────────────────────────────────────

st.subheader("Actifs")

if df.empty:
    st.info("Aucun actif enregistré, commencez par en ajouter un.")
else:
    for idx, row in df.iterrows():
        with st.container(border=True, vertical_alignment="center"):
            cols = st.columns([3, 2, 2, 1, 1])
            cols[0].write(row["nom"])
            cols[1].write(row["categorie"])
            cols[2].write(f"{row['montant']:,.2f} €")
            if cols[3].button("", key=f"mod_{idx}", icon=":material/edit_square:"):
                st.session_state["editing_idx"] = idx
            if cols[4].button("", key=f"del_{idx}", icon=":material/delete:"):
                st.session_state["deleting_idx"] = idx

# ── Formulaire de modification ────────────────────────────────────────────────

if "editing_idx" in st.session_state:
    idx = st.session_state["editing_idx"]
    row = df.loc[idx]

    with st.form("edit_asset"):
        nom = st.text_input("Nom", value=row["nom"])
        categorie = st.selectbox("Catégorie", options=CATEGORIES_ASSETS,
                                 index=CATEGORIES_ASSETS.index(row["categorie"]))
        montant = st.number_input("Montant", min_value=0.0, value=row["montant"], step=100.0)

        if st.form_submit_button("Sauvegarder"):
            df = update_asset(df, idx, nom, categorie, montant)
            st.toast("Actif modifié")
            del st.session_state["editing_idx"]
            st.rerun()

# ── Confirmation de suppression ───────────────────────────────────────────────

if "deleting_idx" in st.session_state:
    idx = st.session_state["deleting_idx"]
    row = df.loc[idx]

    st.warning(f"Supprimer **{row['nom']}** ? Cette action est irréversible.")
    if st.button("Confirmer la suppression", key=f"confirm_del_{idx}"):
        df = delete_asset(df, idx)
        st.toast("Actif supprimé")
        del st.session_state["deleting_idx"]
        st.rerun()

# ── Ajout d'un actif ──────────────────────────────────────────────────────────

with st.expander("Ajouter un nouvel actif"):
    with st.form("add_asset"):
        nom = st.text_input("Nom")
        categorie = st.selectbox("Catégorie", options=CATEGORIES_ASSETS)
        montant = st.number_input("Montant", min_value=0.0, step=100.0)

        if st.form_submit_button("Ajouter"):
            df = add_asset(df, nom, categorie, montant)
            st.toast("Actif ajouté")
            st.rerun()

# ── Statistiques actuelles ────────────────────────────────────────────────────

st.divider()

total = compute_total(df)
st.metric(label="Patrimoine total", value=f"{total:,.2f} €")

stats = compute_by_category(df)
if not stats.empty:
    st.subheader("Répartition par catégorie")
    display = stats.copy()
    display["montant"] = display["montant"].apply(lambda x: f"{x:,.2f} €")
    display["pourcentage"] = display["pourcentage"].apply(lambda x: f"{x:.1f} %")
    st.table(display.set_index("categorie"))

# ── Historique ────────────────────────────────────────────────────────────────

st.divider()
st.subheader("Historique")

df_hist = load_historique()

# Enregistrer un snapshot
col_snap, col_info = st.columns([2, 5])
with col_snap:
    if st.button("📸 Enregistrer un snapshot", disabled=df.empty):
        saved = save_snapshot(df)
        if saved:
            st.toast("Snapshot enregistré")
            st.rerun()
with col_info:
    st.caption("Sauvegarde l'état actuel de vos actifs par catégorie à la date d'aujourd'hui. "
               "Un seul snapshot par jour (le dernier écrase le précédent).")

if df_hist.empty:
    st.info("Aucun historique. Enregistrez un premier snapshot pour commencer le suivi.")
else:
    # Courbe — patrimoine total
    st.subheader("Évolution du patrimoine total")
    total_evo = get_total_evolution(df_hist)
    fig_total = go.Figure()
    fig_total.add_trace(go.Scatter(
        x=total_evo["date"], y=total_evo["total"],
        mode="lines+markers", name="Total",
        line=dict(color="#4C9BE8", width=2),
        marker=dict(size=5),
    ))
    fig_total.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        yaxis_title="Patrimoine (€)",
        xaxis_title="Date",
        hovermode=False,
    )
    st.plotly_chart(fig_total, config={"staticPlot": True})

    # Courbes — par catégorie
    st.subheader("Évolution par catégorie")
    cat_evo = get_category_evolution(df_hist)
    fig_cat = go.Figure()
    for col in cat_evo.columns:
        fig_cat.add_trace(go.Scatter(
            x=cat_evo.index, y=cat_evo[col],
            mode="lines+markers", name=col,
            marker=dict(size=5),
        ))
    fig_cat.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        yaxis_title="Montant (€)",
        xaxis_title="Date",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode=False,
    )
    st.plotly_chart(fig_cat, config={"staticPlot": True})

    # Tableau des snapshots
    st.subheader("Tableau des snapshots")
    snap_table = get_snapshot_table(df_hist)

    # Formatage des montants
    formatted = snap_table.copy()
    for col in formatted.columns:
        formatted[col] = formatted[col].apply(lambda x: f"{x:,.2f} €")
    st.dataframe(formatted)

    # Suppression d'un snapshot
    with st.expander("Supprimer un snapshot"):
        dates_dispo = sorted(df_hist["date"].dt.date.unique(), reverse=True)
        date_to_delete = st.selectbox(
            "Choisir la date à supprimer",
            options=dates_dispo,
            format_func=lambda d: d.strftime("%d/%m/%Y"),
        )
        if st.button("Supprimer ce snapshot", icon=":material/delete:"):
            df_hist = delete_snapshot(df_hist, date_to_delete)
            st.toast("Snapshot supprimé")
            st.rerun()

# ── Export ────────────────────────────────────────────────────────────────────

st.divider()
st.subheader("Exporter les données")
if st.download_button("Télécharger le patrimoine", data=download_assets(df),
                      file_name="patrimoine.csv", mime="text/csv",
                      icon=":material/download:"):
    st.toast("Fichier téléchargé")