import streamlit as st
import controller.utils as utils
import view.list_page as list_page
import view.analise_page as analise_page
import view.simulacao_page as simulacao_page
import view.historico_page as historico_page
import view.sidebar as sidebar

# =======================
# Main
# =======================
def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    qp = st.query_params  

    if "page" in qp:
        st.session_state.page = qp["page"]
    if "ticker" in qp:
        st.session_state.selected_ticker = qp["ticker"]

    sidebar.render_sidebar()

    page = st.session_state.page
    if page == "lista":
        list_page.render_lista()
    elif page == "detalhe":
        analise_page.render_analise()
    elif page == "simulacao":
        simulacao_page.render_simulacao()
    elif page == "historico":
        historico_page.render_historico()

    else:
        utils.goto("lista")

        