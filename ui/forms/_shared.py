"""
ui/forms/_shared.py
────────────────────
Helpers partagés par tous les formulaires actifs.

Fonctions publiques :
    close_dialog()
    contrat_fields(row=None) → contrat_id | None
    resolve_contrat_id(contrat_id) → contrat_id | None
    ticker_picker(initial_ticker) → dict | None
    cancel_button(key)
"""
import streamlit as st
from services.pricer import validate_ticker, lookup_ticker



def _format_duree(duree_mois: int) -> str:
    ans = duree_mois // 12
    mois = duree_mois % 12
    if ans == 0:
        return f"{mois} mois"
    if mois == 0:
        return f"{ans} ans"
    return f"{ans} ans {mois} mois"

# ── Gestion de l'état ─────────────────────────────────────────────────────────

def close_dialog():
    """Ferme la modale asset et nettoie tout l'état du formulaire."""
    st.session_state.pop("_dialog", None)
    for key in list(st.session_state.keys()):
        if key.startswith("_form_") or key.startswith("_upd_"):
            st.session_state.pop(key, None)


# ── Champ contrat ─────────────────────────────────────────────────────────────

def contrat_fields(row=None):
    """
    Sélecteur de contrat (établissement + enveloppe).
    Si l'utilisateur choisit '+ Nouveau contrat...', affiche des champs de création.
    Retourne contrat_id (str) ou None si nouveau contrat en cours de saisie.
    """
    from services.db_contrats import load_contrats
    from constants import ENVELOPPES

    initial_contrat_id = str(row.get("contrat_id", "") or "").strip() if row is not None else ""
    NOUVEAU_CONTRAT = "+ Nouveau contrat..."

    df_contrats = load_contrats()
    contrat_options = []
    contrat_id_to_display = {}

    for _, contrat_row in df_contrats.iterrows():
        display = f"{contrat_row['etablissement']} ({contrat_row['enveloppe']})"
        contrat_options.append(display)
        contrat_id_to_display[display] = contrat_row["id"]

    contrat_options.append(NOUVEAU_CONTRAT)

    default_display = contrat_options[0] if len(contrat_options) > 1 else NOUVEAU_CONTRAT
    if initial_contrat_id:
        for display, cid in contrat_id_to_display.items():
            if cid == initial_contrat_id:
                default_display = display
                break

    default_idx = contrat_options.index(default_display) if default_display in contrat_options else 0

    contrat_selection = st.selectbox(
        "Contrat *",
        options=contrat_options,
        index=default_idx,
        key="_form_contrat_select",
        help="Établissement + enveloppe (ex: Boursorama — PEA)",
    )

    if contrat_selection == NOUVEAU_CONTRAT:
        with st.container(border=True):
            st.caption("Le contrat sera automatiquement créé après validation.")
            col1, col2 = st.columns(2)
            with col1:
                etablissement = st.text_input(
                    "Établissement *",
                    placeholder="ex. Boursorama, Degiro, Crédit Agricole",
                    key="_form_etablissement_new",
                ).strip()
            with col2:
                enveloppe = st.selectbox(
                    "Enveloppe *",
                    options=sorted(ENVELOPPES),
                    key="_form_enveloppe_new",
                )
            st.session_state["_new_contrat"] = {"etablissement": etablissement, "enveloppe": enveloppe}
            return None
    else:
        st.session_state.pop("_new_contrat", None)
        return contrat_id_to_display[contrat_selection]


def resolve_contrat_id(contrat_id):
    """
    Si contrat_id est déjà connu, le retourne tel quel.
    Sinon, crée le contrat depuis _new_contrat en session et retourne le nouvel id.
    """
    if contrat_id is not None:
        return contrat_id
    new_contrat = st.session_state.get("_new_contrat")
    if new_contrat and new_contrat["etablissement"] and new_contrat["enveloppe"]:
        from services.db_contrats import get_or_create_contrat
        return get_or_create_contrat(new_contrat["etablissement"], new_contrat["enveloppe"])
    return None


# ── Ticker picker ─────────────────────────────────────────────────────────────

def ticker_picker(initial_ticker: str = "") -> dict | None:
    """
    Champ texte ticker + bouton vérifier.
    Retourne un dict {ticker, name, price, currency} si validé, None sinon.
    En mode edit (initial_ticker non vide), retourne directement sans re-vérifier.
    """
    help_ticker = """:small[Le ticker est affiché entre parenthèses sur https://finance.yahoo.com/markets/]"""

    ticker_input = st.text_input(
        "Ticker *",
        value=initial_ticker,
        placeholder="ex. AAPL, BTC-USD, CW8.PA",
        key="_form_ticker_input",
        help=help_ticker,
    ).strip().upper()

    if st.session_state.get("_form_ticker_last") != ticker_input:
        st.session_state.pop("_form_ticker_preview", None)
        st.session_state["_form_ticker_last"] = ticker_input

    if ticker_input == initial_ticker and initial_ticker != "":
        return {"ticker": ticker_input, "prefilled": True}

    if st.button(
        "Vérifier le ticker",
        width="stretch",
        key="_form_verify_btn",
        icon=":material/search_check_2:",
    ):
        valid, err = validate_ticker(ticker_input)
        if not valid:
            st.error(err)
        else:
            with st.spinner("Recherche en cours…"):
                result = lookup_ticker(ticker_input)
            if result:
                st.session_state["_form_ticker_preview"] = result
            else:
                st.error(f"Ticker « {ticker_input} » introuvable sur yfinance.")

    if "_form_ticker_preview" in st.session_state:
        preview = st.session_state["_form_ticker_preview"]
        with st.container(border=True):
            st.markdown(f"**{preview['name']}**")
            price_str = f"{preview['price']:,.4f} {preview['currency']}".strip()
            st.caption(f"{preview['ticker']} · {price_str}")
        return preview

    return None


# ── Bouton annuler standalone ─────────────────────────────────────────────────

def cancel_button(key="_form_cancel_early"):
    """Bouton Annuler affiché seul (avant que le ticker soit validé)."""
    if st.button("Annuler", width="stretch", key=key):
        close_dialog()
        st.rerun()