import streamlit as st
from services.storage import init_storage, download_assets
from services.assets import (
    get_assets, add_asset, update_asset, delete_asset,
    compute_total, compute_by_category,
)
from constants import CATEGORIES_ASSETS

st.set_page_config(page_title="Suivi Patrimoine", layout="wide", page_icon="📊")
init_storage()

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
            cols[2].write(row["montant"])
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

        if st.form_submit_button("Sauvegarder",type="primary"):
            df = update_asset(df, idx, nom, categorie, montant)
            st.toast("Actif modifié")
            del st.session_state["editing_idx"]
            st.rerun()

        if st.form_submit_button("Annuler"):
            del st.session_state["editing_idx"]
            st.rerun()

# ── Confirmation de suppression ───────────────────────────────────────────────

if "deleting_idx" in st.session_state:
    idx = st.session_state["deleting_idx"]
    row = df.loc[idx]

    with st.container(border=True, vertical_alignment="center"):
        st.warning(f"Supprimer **{row['nom']}** ? Cette action est irréversible.")
        if st.button("Confirmer la suppression", key=f"confirm_del_{idx}",type="primary"):
            df = delete_asset(df, idx)
            st.toast("Actif supprimé")
            del st.session_state["deleting_idx"]
            st.rerun()
        if st.button("Annuler", key=f"cancel_del_{idx}"):
            del st.session_state["deleting_idx"]
            st.rerun()

# ── Ajout d'un actif ─────────────────────────────────────────────────────────

with st.expander("Ajouter un nouvel actif"):
    with st.form("add_asset"):
        nom = st.text_input("Nom")
        categorie = st.selectbox("Catégorie", options=CATEGORIES_ASSETS)
        montant = st.number_input("Montant", min_value=0.0, step=100.0)

        if st.form_submit_button("Ajouter"):
            df = add_asset(df, nom, categorie, montant)
            st.toast("Actif ajouté")
            st.rerun()

# ── Export ────────────────────────────────────────────────────────────────────

st.subheader("Exporter les données")
if st.download_button("Télécharger le patrimoine", data=download_assets(df),
                      file_name="patrimoine.csv", mime="text/csv",
                      icon=":material/download:"):
    st.toast("Fichier téléchargé", icon="✅")

# ── Statistiques ──────────────────────────────────────────────────────────────

total = compute_total(df)
st.metric(label="Patrimoine total", value=f"{total:,.2f} €")

stats = compute_by_category(df)

if not stats.empty:
    st.subheader("Répartition par catégorie")
    display = stats.copy()
    display["montant"] = display["montant"].apply(lambda x: f"{x:,.2f} €")
    display["pourcentage"] = display["pourcentage"].apply(lambda x: f"{x:.1f} %")
    st.table(display.set_index("categorie"))