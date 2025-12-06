# app.py
import streamlit as st
import pandas as pd
from typing import List
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder
import re
import altair as alt
import os
import controller.utils as utils
import view.sidebar as sidebar
import view.list_page as list_page
import view.analise_page as analise_page
import view.simulacao_page as simulacao_page
import view.historico_page as historico_page

APP_TITLE = "Simulador de Ações (Fundamentalista)"


utils.apply_period_watchers()


# =======================
# Estado global
# =======================

def init_state():
    if "page" not in st.session_state:
        st.session_state.page = "lista"  
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = {}
    if "selected_ticker" not in st.session_state:
        st.session_state.selected_ticker = None
    if "mostrar_todos" not in st.session_state:
        st.session_state.mostrar_todos = False
    
init_state()

def main():
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

        
if __name__ == "__main__":
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    main()
