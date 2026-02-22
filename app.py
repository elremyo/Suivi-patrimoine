import streamlit as st
import pandas as pd
from services.storage import init_storage, load_assets, save_assets

st.set_page_config(page_title="Suivi Patrimoine", layout="wide")

init_storage()

st.title("Suivi de patrimoine")

df = load_assets()

st.subheader("Actifs")

st.dataframe(df, use_container_width=True)

st.subheader("Ajouter un actif")

with st.form("add_asset"):
    nom = st.text_input("Nom")
    categorie = st.text_input("Catégorie")
    montant = st.number_input("Montant", min_value=0.0, step=100.0)

    submitted = st.form_submit_button("Ajouter")

    if submitted:
        new_row = pd.DataFrame([[nom, categorie, montant]], columns=df.columns)
        df = pd.concat([df, new_row], ignore_index=True)
        save_assets(df)
        st.success("Actif ajouté")
        st.rerun()