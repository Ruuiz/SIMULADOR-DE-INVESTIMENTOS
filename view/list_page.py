import streamlit as st
import controller.utils as utils
import pandas as pd
import re
from st_aggrid import AgGrid, GridOptionsBuilder

DATA_FILE = "src/base_para_simulador_indicadores_refatorado_minimal.csv"  # caminho já OK no upload atual

@st.dialog("Adicionar ação à carteira")
def adicionar_acao_dialog(ticker, preco_unitario):
    st.write(f"**Ticker:** {ticker}")
    st.write(f"**Preço atual:** R$ {preco_unitario:.2f}")
    quantidade = st.number_input("Quantidade de ações", min_value=1, step=1, key=f"qtd_{ticker}")
    
    if st.button("Confirmar"):
        if "portfolio" not in st.session_state or not isinstance(st.session_state.portfolio, dict):
            st.session_state.portfolio = {}
            utils.lock_period_if_portfolio_filled()

        t = str(ticker).strip().upper()        
        st.session_state.portfolio[t] = {
            "quantidade": int(quantidade),
            "preco_unitario": float(preco_unitario),
        }
        st.success(f"{t} adicionado à carteira!")
        st.rerun()

def _reset_filtros():
    # limpa sliders
    for k in list(st.session_state.keys()):
        if k.startswith("slider_"):
            st.session_state.pop(k, None)

    # zera explicitamente os filtros básicos
    st.session_state["filtro_busca"] = ""
    st.session_state["filtro_setor"] = "Selecione"
    st.session_state["filtro_ano"] = "Selecione"
    st.session_state["filtro_tri"] = "Selecione"

    # st.rerun()

# =======================
# Página 1: Lista + filtros + ações
# =======================
def render_lista():
    st.title("Simulador de Ações (Fundamentalista)")
    # st.subheader("Lista de Ações (Página 1)")
    utils._sync_filters_from_query()

    if "filtro_ano" in st.session_state:
        st.session_state["filtro_ano"] = str(st.session_state["filtro_ano"])
    if "filtro_tri" in st.session_state:
        st.session_state["filtro_tri"] = str(st.session_state["filtro_tri"])

    try:
        df_raw = utils.load_base(DATA_FILE)
    except Exception as e:
        st.error(f"Erro ao carregar a base: {e}")
        st.stop()
        
    # Linha do título e botão de reset
    col_filtros, col_reset = st.columns([6, 1])
    with col_filtros:
        st.markdown("### Filtros")
    with col_reset:
        st.button("🔄 Resetar filtros", key="btn_reset", on_click=_reset_filtros)

        
        
    # depois de ler o CSV em df_raw
    df_raw["Data_Referencia"] = pd.to_datetime(df_raw["Data_Referencia"], errors="coerce")
    df_raw["Ano"] = df_raw["Data_Referencia"].dt.year.astype("Int64")
    df_raw["Trimestre"] = df_raw["Data_Referencia"].dt.quarter.astype("Int64")
    
    
    # seletores de ano e trimestre (strings homogêneas; estado lógico separado)
    col1, col2 = st.columns(2)

    # ====================
    # Filtros: Ano e Trimestre
    # ====================

    years = (
        pd.to_numeric(df_raw["Ano"], errors="coerce")
        .dropna().astype(int).sort_values(ascending=False).unique().tolist()
    )
    fy_options = ["Selecione"] + [str(y) for y in years]
    fq_options = ["Selecione", "1", "2", "3", "4"]

    col1, col2 = st.columns(2)

    # Selectbox com chave unificada no session_state
    col1.selectbox("Ano (FY)", options=fy_options, key="filtro_ano")
    col2.selectbox("Trimestre (FQ)", options=fq_options, key="filtro_tri")

    # Extrai valores e converte para int ou None
    fy_raw = st.session_state.get("filtro_ano", "Selecione")
    fq_raw = st.session_state.get("filtro_tri", "Selecione")

    new_fy = int(fy_raw) if fy_raw not in ("Selecione", None) else None
    new_fq = int(fq_raw) if fq_raw not in ("Selecione", None) else None

    # Compara com período anterior salvo
    old_fy, old_fq = st.session_state.get("_periodo_lock_portfolio", (None, None))

    # Se mudou, reseta carteira e atualiza lock
    if (old_fy, old_fq) != (new_fy, new_fq):
        st.session_state["portfolio"] = {}
        st.session_state["_portfolio_reset_message"] = (
            f"Período alterado para "
            f"{new_fy if new_fy is not None else 'Todos'}T"
            f"{new_fq if new_fq is not None else 'Todos'}; carteira resetada."
        )
        st.session_state["_periodo_lock_portfolio"] = (new_fy, new_fq)


    # base de trabalho conforme filtros (None = "Selecione")
    df_f = df_raw.copy()
    if new_fy is not None:
        df_f = df_f[df_f["Ano"] == new_fy]
    if new_fq is not None:
        df_f = df_f[df_f["Trimestre"] == new_fq]


    # garante 1 linha por Ticker: pega a mais recente dentro do subset filtrado
    if not df_f.empty:
        idx_last = df_f.groupby("Ticker")["Data_Referencia"].idxmax()
        df = df_f.loc[idx_last].sort_values("Ticker").reset_index(drop=True)
    else:
        df = df_f


    # garante 1 linha por Ticker: pega a mais recente dentro do subset filtrado
    if not df_f.empty:
        idx_last = df_f.groupby("Ticker")["Data_Referencia"].idxmax()
        df = df_f.loc[idx_last].sort_values("Ticker").reset_index(drop=True)
    else:
        df = df_f

    numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns.tolist()
    exclude_sliders = {"Preco_Atual","Valor_Empresa","Capital_Giro","Net_Debt","Lucro_Por_Acao", "CAGR5_Receita","DY_Medio_5anos","EBIT_per_share","EV_Receita","Giro_Ativos","Liquidez_Corrente_Calc",
"Margem_EBIT_Sector","Margem_Liquida_Sector","NetDebt_Patrimonio","Passivos_Ativos","Payout_TTM","Trimestre","Ano", "EBIT"}
    filtered_cols = [c for c in numeric_cols if c not in exclude_sliders]
    
    # Antes dos widgets:
    if st.session_state.get("reset_filtros", False):
        st.session_state["filtro_busca"] = ""
        st.session_state["filtro_setor"] = "Selecione"
        # Limpe sliders se necessário
        for k in list(st.session_state.keys()):
            if k.startswith("slider_"):
                del st.session_state[k]
        st.session_state["reset_filtros"] = False

    

    # Agora os filtros vêm abaixo normalmente
    
    col1.text_input("Buscar por Ticker:", key="filtro_busca", placeholder="ex.: ABCB4")
    setor_opcoes = ["Selecione"] + sorted(df["Setor_Oficial_final"].dropna().unique())
    setor_sel = col2.selectbox("Filtrar por Setor:", options=setor_opcoes, key="filtro_setor")
    

    term = st.session_state.get("filtro_busca", "").strip()

    df_base = df.copy()

    if term:
        pattern = re.escape(term)
        df = df[df["Ticker"].astype(str).str.contains(pattern, case=False, na=False)]
    if setor_sel != "Selecione":
        df = df[df["Setor_Oficial_final"] == setor_sel]
    df = df_base.copy()

    with st.expander("Filtros Avançados (Indicadores Numéricos)", expanded=False):
        for i in range(0, len(filtered_cols), 3):
            cols = st.columns(3)
            for j, col in enumerate(filtered_cols[i:i+3]):
                serie = df_base[col].dropna()   # <-- importante: sempre sobre df_base
                if serie.empty:
                    continue

                min_val, max_val = float(serie.min()), float(serie.max())
                if min_val < 0:
                    min_val = 0.0

                if df_base[col].name == "ROE" or df_base[col].name == "ROA" or df_base[col].name == "ROIC":
                    max_val = 1.0

                if max_val > 100:
                    max_val = 100.0

                step = (max_val - min_val) / 100 if max_val != min_val else 1.0

                if min_val == max_val:
                    cols[j].markdown(f"*{col}: valor único ({min_val}) — filtro ignorado*")
                    continue

                # slider mantém estado automaticamente via session_state
                selected_range = cols[j].slider(
                    f"{col}", min_value=min_val, max_value=max_val,
                    value=(min_val, max_val), step=step, key=f"slider_{col}"
                )

                # aplica o filtro refinado
                # df = df[(df[col] >= selected_range[0]) & (df[col] <= selected_range[1])]
                if selected_range[0]==0:
                    df = df[(df[col] >= selected_range[0]) | (df[col].isna()) | (df[col] < selected_range[0])]
                    # pass
                else:
                    df = df[(df[col] >= selected_range[0]) | (df[col].isna())]
                    
                #condicional para quando o filtro for 100 ele tambem puxar valores maiores que 100
                if selected_range[1]==100.0:
                    pass
                else:
                    df = df[(df[col] <= selected_range[1])]

    st.caption(f"{len(df)} ativos encontrados (1 linha por Ticker).")

    # ... depois da detecção de mudança de ano/trimestre e eventual reset da carteira:
    utils._push_filters_to_query()


    #  Tabela interativa com seleção via AgGrid
    df_view = df.reset_index(drop=True)
    st.markdown("### 🔘 Clique em uma linha da tabela para filtrar abaixo")

    gb = GridOptionsBuilder.from_dataframe(df_view)
    gb.configure_selection('single', use_checkbox=True)
    grid_options = gb.build()
    
    grid_response = AgGrid(
        df_view,
        gridOptions=grid_options,
        height=350,
        width='100%',
        update_mode='SELECTION_CHANGED',
        allow_unsafe_jscode=True,
        theme='streamlit'
    )

    selected = grid_response['selected_rows']
    # st.write("DEBUG - selected:", selected)

    ticker_selecionado = None
    if isinstance(selected, list) and len(selected) > 0:
        # st-aggrid normalmente retorna lista de dicts
        ticker_selecionado = selected[0].get('Ticker', None)
    elif isinstance(selected, pd.DataFrame) and not selected.empty:
        # fallback raro: DataFrame
        ticker_selecionado = selected.iloc[0].get('Ticker', None)

    if ticker_selecionado:
        # st.write("DEBUG - ticker_selecionado:", ticker_selecionado)
        df_filtrado = df_view[df_view["Ticker"].astype(str).str.contains(str(ticker_selecionado), case=False, na=False)]
    
    else:
        # st.write("DEBUG - Nenhuma linha selecionada")
        df_filtrado = df_view

    st.divider()
    st.write("**Ações disponíveis**")

    for _, row in df_filtrado.iterrows():
        ticker = str(row.get("Ticker", "")).strip()
        preco_atual = float(row.get("Preco_Atual", 0))
        if not ticker or preco_atual <= 0:
            continue
        c1, c2, c3 = st.columns([2, 1, 1])
        c1.write(f"**{ticker}** — {row.get('Setor_Oficial_final','')}")
        if c2.button("➕ Adicionar", key=f"add_{ticker}"):
            adicionar_acao_dialog(ticker, preco_atual)
        if c3.button("🔎 Analisar", key=f"det_{ticker}"):
            utils.goto("detalhe", ticker=ticker)
