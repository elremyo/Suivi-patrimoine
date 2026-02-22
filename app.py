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
            cols = st.columns([3, 2, 2, 1, 1])
            with cols[0]:
                st.write(row["nom"])
            with cols[1]:
                st.write(row["categorie"])
            with cols[2]:
                st.write(row["montant"])
            with cols[3]:
                if st.button("", key=f"mod_{idx}", icon=":material/edit_square:"):
                    st.session_state["editing_idx"] = idx
            with cols[4]:
                if st.button("", key=f"del_{idx}", icon=":material/delete:"):
                    st.session_state["deleting_idx"] = idx

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

    if "deleting_idx" in st.session_state:
        idx = st.session_state["deleting_idx"]
        row = df.loc[idx]

        if st.warning(f"Supprimer {row['nom']} ? Cette action est irréversible."):
            if st.button("Confirmer la suppression", key=f"confirm_del_{idx}"):
                df = df.drop(index=idx).reset_index(drop=True)
                save_assets(df)
                st.toast("Actif supprimé")
                del st.session_state["deleting_idx"]
                st.rerun()

with st.expander("Ajouter un nouvel actif"):
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


total_patrimoine = df["montant"].sum()
st.metric(label="Patrimoine total", value=f"{total_patrimoine:,.2f} €")

# Grouper les actifs par catégorie et sommer les montants
montant_par_categorie = df.groupby("categorie")["montant"].sum()

st.subheader("Répartition par catégorie (montant)")

# Affichage sous forme de tableau simple
st.table(montant_par_categorie.apply(lambda x: f"{x:,.2f} €"))

total_patrimoine = df["montant"].sum()

# Calcul des pourcentages
pourcentage_par_categorie = (montant_par_categorie / total_patrimoine * 100).round(2)

st.subheader("Répartition par catégorie (%)")
st.table(pourcentage_par_categorie.apply(lambda x: f"{x:,.1f} %"))