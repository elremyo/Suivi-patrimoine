import streamlit as st

def flash(msg: str, type: str = "success"):
    st.session_state["_flash"] = {"msg": msg, "type": type}

def show_flash():
    if "_flash" in st.session_state:
        f = st.session_state.pop("_flash")
        icons = {"success": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}
        st.toast(f["msg"], icon=icons.get(f["type"], "ℹ️"))