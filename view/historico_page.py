import streamlit as st
import pandas as pd
import numpy as np
import controller.utils as utils
import altair as alt
import os

HISTORY_FILE = "src/sim_history.csv"

# =======================
# Pagina 4 - Historico simulações
# =======================

def _ensure_sim_history():
    if "sim_history" not in st.session_state:
        st.session_state["sim_history"] = []
    # carrega do CSV só uma vez
    if os.path.exists(HISTORY_FILE) and not st.session_state.get("_hist_loaded", False):
        try:
            df = pd.read_csv(HISTORY_FILE, encoding="utf-8-sig")
            st.session_state["sim_history"] = df.to_dict("records")
        except Exception:
            pass
        st.session_state["_hist_loaded"] = True




def render_historico():
    # --- garante estrutura do histórico na sessão ---
    _ensure_sim_history()

    st.header("Histórico de simulações")

    # voltar sem resetar filtros/carteira da página 1
    if st.button("← Voltar para a lista", key="hist_btn_voltar_lista"):
        utils.goto("lista")
        return

    hist = st.session_state.get("sim_history", [])
    if not hist:
        st.info("Nenhuma simulação salva ainda. Faça uma simulação na Página 2.")
        return

    # ---------------- Base e tipos ----------------
    dfh = pd.DataFrame(hist).copy()

    if "timestamp" in dfh.columns:
        dfh["timestamp"] = pd.to_datetime(dfh["timestamp"], errors="coerce")

    for c in [
        "base_fy", "base_fq", "end_fy", "end_fq", "n_tickers",
        "valor_inicial", "valor_final", "div_acum",
        "ret_total", "ret_sem_div", "cagr", "vol_anual", "hit_ratio", "max_dd"
    ]:
        if c in dfh.columns:
            dfh[c] = pd.to_numeric(dfh[c], errors="coerce")

    # ---------------- Callback: só marca flag ----------------
    def _reset_hist_filters_cb():
        st.session_state["_hist_filters_reset"] = True

    # ---------------- Cálculo dos defaults dinâmicos ----------------
    fy_opts_base = ["(Todos)"] + (
        sorted(dfh["base_fy"].dropna().astype(int).unique(), reverse=True)
        if "base_fy" in dfh.columns else []
    )
    fq_opts_base = ["(Todos)"] + (
        sorted(dfh["base_fq"].dropna().astype(int).unique())
        if "base_fq" in dfh.columns else []
    )

    fy_opts_end = ["(Todos)"] + (
        sorted(dfh["end_fy"].dropna().astype(int).unique(), reverse=True)
        if "end_fy" in dfh.columns else []
    )
    fq_opts_end = ["(Todos)"] + (
        sorted(dfh["end_fq"].dropna().astype(int).unique())
        if "end_fq" in dfh.columns else []
    )

    rmin = rmax = None
    if "ret_total" in dfh.columns and dfh["ret_total"].notna().any():
        ret_pct = (dfh["ret_total"] * 100).astype(float)
        rmin, rmax = float(np.nanmin(ret_pct)), float(np.nanmax(ret_pct))

    dmin = dmax = None
    if "timestamp" in dfh.columns and dfh["timestamp"].notna().any():
        dmin = pd.to_datetime(dfh["timestamp"]).min().date()
        dmax = pd.to_datetime(dfh["timestamp"]).max().date() 

    options_ids = dfh["sim_id"].tolist() if "sim_id" in dfh.columns else []
    default_ms = options_ids[:2] if len(options_ids) >= 2 else options_ids

    # ---------------- Cabeçalho de filtros + reset ----------------
    row = st.columns([6, 1])
    with row[0]:
        st.subheader("Filtros")
    with row[1]:
        st.button("🔄 Resetar", key="btn_hist_reset", on_click=_reset_hist_filters_cb)

    # ---------------- Aplica defaults quando reset solicitado ----------------
    if st.session_state.pop("_hist_filters_reset", False):
        st.session_state["hist_base_fy"] = "(Todos)"
        st.session_state["hist_base_fq"] = "(Todos)"
        st.session_state["hist_end_fy"]  = "(Todos)"
        st.session_state["hist_end_fq"]  = "(Todos)"
        st.session_state["hist_term"]    = ""
        st.session_state["hist_min_tk"]  = 1

        if (rmin is not None) and (rmax is not None):
            st.session_state["hist_ret_range"] = (min(rmin, rmax), max(rmin, rmax))
        else:
            st.session_state.pop("hist_ret_range", None)

        if (dmin is not None) and (dmax is not None):
            st.session_state["hist_date_range"] = (dmin, dmax)
        else:
            st.session_state.pop("hist_date_range", None)

        # key exclusiva do multiselect de comparação
        st.session_state["hist_simsel_cmp"] = default_ms
        st.rerun()

    # ---------------- Garante defaults no session_state (sem value nos widgets) ----------------
    st.session_state.setdefault("hist_base_fy", "(Todos)")
    st.session_state.setdefault("hist_base_fq", "(Todos)")
    st.session_state.setdefault("hist_end_fy",  "(Todos)")
    st.session_state.setdefault("hist_end_fq",  "(Todos)")
    st.session_state.setdefault("hist_term", "")
    st.session_state.setdefault("hist_min_tk", 1)

    if (rmin is not None) and (rmax is not None):
        st.session_state.setdefault("hist_ret_range", (min(rmin, rmax), max(rmin, rmax)))
    else:
        st.session_state.pop("hist_ret_range", None)

    if (dmin is not None) and (dmax is not None):
        st.session_state.setdefault("hist_date_range", (dmin, dmax))
    else:
        st.session_state.pop("hist_date_range", None)

    st.session_state.setdefault("hist_simsel_cmp", default_ms)

    # ---------------- Widgets dos filtros ----------------
    colA, colB, colC, colD = st.columns(4)
    base_fy_sel = colA.selectbox("Base FY", options=fy_opts_base, key="hist_base_fy")
    base_fq_sel = colB.selectbox("Base FQ", options=fq_opts_base, key="hist_base_fq")
    end_fy_sel  = colC.selectbox("Fim FY",  options=fy_opts_end,  key="hist_end_fy")
    end_fq_sel  = colD.selectbox("Fim FQ",  options=fq_opts_end,  key="hist_end_fq")

    colE, colF = st.columns([2, 2])
    term = colE.text_input("Buscar por Ticker (ex.: ABCB4)", key="hist_term")


    # ---------------- Aplica filtros ao DF ----------------
    m = pd.Series(True, index=dfh.index)

    if "base_fy" in dfh.columns and base_fy_sel != "(Todos)":
        m &= (dfh["base_fy"] == int(base_fy_sel))
    if "base_fq" in dfh.columns and base_fq_sel != "(Todos)":
        m &= (dfh["base_fq"] == int(base_fq_sel))
    if "end_fy" in dfh.columns and end_fy_sel != "(Todos)":
        m &= (dfh["end_fy"] == int(end_fy_sel))
    if "end_fq" in dfh.columns and end_fq_sel != "(Todos)":
        m &= (dfh["end_fq"] == int(end_fq_sel))

    if term and "tickers" in dfh.columns:
        def _has_term(v):
            if isinstance(v, (list, tuple)):
                return any(term.upper() in str(x).upper() for x in v)
            return term.upper() in str(v).upper()
        m &= dfh["tickers"].apply(_has_term)

    if "n_tickers" in dfh.columns:
        m &= (dfh["n_tickers"] >= int(st.session_state.get("hist_min_tk", 1)))

    if ("ret_total" in dfh.columns) and ("hist_ret_range" in st.session_state):
        lo, hi = st.session_state["hist_ret_range"]
        m &= ((dfh["ret_total"] * 100) >= lo) & ((dfh["ret_total"] * 100) <= hi)

    if ("timestamp" in dfh.columns) and ("hist_date_range" in st.session_state):
        d0, d1 = st.session_state["hist_date_range"]
        m &= dfh["timestamp"].dt.date.between(d0, d1)

    dfh_f = dfh[m].copy()
    if dfh_f.empty:
        st.info("Nenhuma simulação corresponde aos filtros selecionados.")
        return

    if "timestamp" in dfh_f.columns:
        dfh_f = dfh_f.sort_values("timestamp", ascending=False)

    # ---------------- Tabela sintética ----------------
    cols_order = [
        "sim_id", "timestamp",
        "base_fy", "base_fq", "end_fy", "end_fq",
        "n_tickers", "tickers",
        "valor_inicial", "valor_final", "div_acum",
        "ret_sem_div", "ret_total", "cagr",
        "vol_anual", "hit_ratio", "max_dd"
    ]
    cols_order = [c for c in cols_order if c in dfh_f.columns]
    tbl = dfh_f[cols_order].copy()

    for c in ["valor_inicial", "valor_final", "div_acum"]:
        if c in tbl.columns:
            tbl[c] = pd.to_numeric(tbl[c], errors="coerce").round(2)

    pct_map = {
        "ret_sem_div": "Ret s/ Div (%)",
        "ret_total": "Ret c/ Div (%)",
        "cagr": "CAGR (%)",
        "vol_anual": "Vol anual (%)",
        "hit_ratio": "Hit ratio (%)",
        "max_dd": "Máx. DD (%)",
    }
    for c, newc in pct_map.items():
        if c in tbl.columns:
            tbl[newc] = (pd.to_numeric(tbl[c], errors="coerce") * 100).round(2)
    tbl = tbl.drop(columns=[c for c in pct_map if c in tbl.columns], errors="ignore")

    tbl = tbl.rename(columns={
        "sim_id": "ID",
        "timestamp": "Quando",
        "base_fy": "Base FY", "base_fq": "Base FQ",
        "end_fy": "Fim FY", "end_fq": "Fim FQ",
        "n_tickers": "#Tickers",
        "tickers": "Tickers",
        "valor_inicial": "Valor Inicial (R$)",
        "valor_final": "Valor Final (R$)",
        "div_acum": "Dividendos (R$)",
    })

    if "Tickers" in tbl.columns:
        tbl["Tickers"] = tbl["Tickers"].apply(
            lambda v: ", ".join(v) if isinstance(v, (list, tuple)) else (str(v) if pd.notna(v) else "")
        )

    st.subheader("Lista de simulações")
    st.dataframe(tbl, use_container_width=True, hide_index=True)

    st.download_button(
        "Baixar histórico filtrado (.CSV)",
        data=tbl.to_csv(index=False, encoding="utf-8-sig"),
        file_name="sim_history_export_filtrado.csv",
        mime="text/csv",
        key="btn_download_hist"
    )

    # ---------------- Comparação entre simulações ----------------
    st.subheader("⚖️ Comparar simulações (retorno, dividendos e risco)")

    if "sim_id" not in dfh_f.columns:
        st.info("Sem identificadores de simulação para comparar.")
        return

    def _fmt_label(row):
        def _as_int(x): 
            try: return int(x)
            except: return x
        base = f"{_as_int(row.get('base_fy','?'))}T{_as_int(row.get('base_fq','?'))}"
        end  = f"{_as_int(row.get('end_fy','?'))}T{_as_int(row.get('end_fq','?'))}"
        n = int(row.get('n_tickers', 0)) if pd.notna(row.get('n_tickers', np.nan)) else 0
        return f"{row['sim_id']} — {base}→{end} ({n} tkrs)"

    dfh_f["__label"] = dfh_f.apply(_fmt_label, axis=1)
    options = dfh_f["sim_id"].tolist()
    label_map = dict(zip(dfh_f["sim_id"], dfh_f["__label"]))

    sel = st.multiselect(
        "Selecione 2 ou mais simulações",
        options=options,
        format_func=lambda x: label_map.get(x, x),
        key="hist_simsel_cmp"  # key exclusiva
    )

    if len(sel) >= 1:
        cmp_df = dfh_f[dfh_f["sim_id"].isin(sel)].copy()

        for c in ["ret_total", "ret_sem_div", "div_acum", "vol_anual", "max_dd"]:
            if c in cmp_df.columns:
                cmp_df[c] = pd.to_numeric(cmp_df[c], errors="coerce")

        cmp_df["Ret c/ Div (%)"] = (cmp_df["ret_total"] * 100).round(2) if "ret_total" in cmp_df.columns else np.nan
        cmp_df["Ret s/ Div (%)"] = (cmp_df["ret_sem_div"] * 100).round(2) if "ret_sem_div" in cmp_df.columns else np.nan
        cmp_df["Dividendos (R$)"] = cmp_df["div_acum"].round(2) if "div_acum" in cmp_df.columns else np.nan
        cmp_df["Vol anual (%)"] = (cmp_df["vol_anual"] * 100).round(2) if "vol_anual" in cmp_df.columns else np.nan
        cmp_df["Máx DD (%)"] = (cmp_df["max_dd"] * 100).round(2) if "max_dd" in cmp_df.columns else np.nan

        view = cmp_df[[
            "sim_id", "timestamp", "base_fy", "base_fq", "end_fy", "end_fq",
            "Ret c/ Div (%)", "Ret s/ Div (%)", "Dividendos (R$)", "Vol anual (%)", "Máx DD (%)"
        ]].copy().rename(columns={
            "sim_id": "ID", "timestamp": "Quando",
            "base_fy": "Base FY", "base_fq": "Base FQ",
            "end_fy": "Fim FY", "end_fq": "Fim FQ"
        })

        st.dataframe(view, use_container_width=True, hide_index=True)

        mlong = view.melt(
            id_vars=["ID"],
            value_vars=["Ret c/ Div (%)", "Ret s/ Div (%)", "Dividendos (R$)", "Vol anual (%)", "Máx DD (%)"],
            var_name="Métrica", value_name="Valor"
        ).dropna(subset=["Valor"])

        bar = alt.Chart(mlong).mark_bar().encode(
            x=alt.X("Métrica:N", title=None),
            y=alt.Y("Valor:Q", title=None),
            color=alt.Color("ID:N", legend=alt.Legend(orient="bottom", title=None)),
            tooltip=[alt.Tooltip("ID:N"), alt.Tooltip("Métrica:N"), alt.Tooltip("Valor:Q", format=",.2f")]
        ).properties(height=320)

        st.altair_chart(bar, use_container_width=True)
    else:
        st.info("Selecione ao menos 1 simulação para comparar.")
