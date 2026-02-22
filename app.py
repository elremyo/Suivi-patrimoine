import streamlit as st
import pandas as pd
from services.storage import init_storage, load_assets, save_assets
from constants import CATEGORIES_ASSETS


st.set_page_config(page_title="Suivi Patrimoine", layout="wide")

init_storage()

st.title("Suivi de patrimoine")

st.subheader("Actifs")

df = load_assets()
if df.empty:
    st.info("Aucun actif enregistré, commencez par en ajouter un.")
else:
    # --- Ici tu ajoutes la section modification ---
    for idx, row in df.iterrows():
        with st.container(border=True,vertical_alignment="center"):
            cols = st.columns([3, 2, 2, 2])
            cols[0].write(row["nom"])
            cols[1].write(row["categorie"])
            cols[2].write(row["montant"])
        
        if cols[3].button("Modifier", key=f"mod_{idx}"):
            st.session_state["editing_idx"] = idx

    if "editing_idx" in st.session_state:
        idx = st.session_state["editing_idx"]
        row = df.loc[idx]

        with st.form("edit_asset"):
            nom = st.text_input("Nom", value=row["nom"])
            categorie = st.selectbox("Catégorie", options=CATEGORIES_ASSETS,
                                     index=CATEGORIES_ASSETS.index(row["categorie"]))
            montant = st.number_input("Montant", min_value=0.0, value=row["montant"], step=100.0)

            submitted = st.form_submit_button("Sauvegarder")
            if submitted:
                df.loc[idx] = [nom, categorie, montant]
                save_assets(df)
                st.toast("Actif modifié")
                del st.session_state["editing_idx"]
                st.rerun()

st.subheader("Ajouter un actif")

with st.form("add_asset"):
    nom = st.text_input("Nom")
    categorie = st.selectbox("Catégorie", options=CATEGORIES_ASSETS)
    montant = st.number_input("Montant", min_value=0.0, step=100.0)

    submitted = st.form_submit_button("Ajouter")

    if submitted:
        new_row = pd.DataFrame([[nom, categorie, montant]], columns=df.columns)
        df = pd.concat([df, new_row], ignore_index=True)
        save_assets(df)
        st.toast("Actif ajouté")
        st.rerun()