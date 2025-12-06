# app.py
import streamlit as st
import pandas as pd
# from typing import List
import numpy as np
# from st_aggrid import AgGrid, GridOptionsBuilder
# import re
# import altair as alt
# import os


HISTORY_FILE = "src/sim_history_store.csv"
# quais filtros mapeiam para querystring
FILTER_STATE_MAP = {
    "filtro_ano": "fy",
    "filtro_tri": "fq",
    "filtro_setor": "sector",
    "filtro_busca": "q",
}

def _norm_year(x):
    if x in (None, "Selecione"):
        return None
    try:
        return int(x)
    except Exception:
        return None

def _norm_quarter(x):
    if x in (None, "Selecione"):
        return None
    try:
        return int(x)
    except Exception:
        return None

def get_current_period():
    """Retorna (ano, tri) normalizados a partir dos filtros da UI."""
    ano = _norm_year(st.session_state.get("filtro_ano"))
    tri = _norm_quarter(st.session_state.get("filtro_tri"))
    return (ano, tri)

def get_locked_period():
    """Retorna o período travado da carteira (ou (None, None))."""
    return st.session_state.get("_periodo_lock_portfolio", (None, None))

def lock_period_if_portfolio_filled():
    """
    Se a carteira acabou de ficar não-vazia e ainda não há lock, 
    trava o período atual (mesmo que o trimestre esteja None).
    """
    if st.session_state.get("portfolio"):
        if "_periodo_lock_portfolio" not in st.session_state or st.session_state["_periodo_lock_portfolio"] == (None, None):
            st.session_state["_periodo_lock_portfolio"] = get_current_period()

def reset_portfolio_on_period_change():
    """
    Reseta a carteira somente quando:
      - já existe carteira;
      - o período atual está DEFINIDO (ano e/ou trimestre não são '(Todos)');
      - e é diferente do período travado anterior.
    Em seguida atualiza o lock para o novo período.
    """
    atual = get_current_period()
    travado = get_locked_period()
    carteira = st.session_state.get("portfolio", {})

    # Só considera reset se houver carteira e pelo menos o ANO estiver definido
    if carteira and (atual[0] is not None or atual[1] is not None) and atual != travado:
        st.session_state["portfolio"] = {}
        st.session_state["_periodo_lock_portfolio"] = atual
        st.session_state["_portfolio_reset_message"] = f"Carteira resetada ao alterar o período (Ano={atual[0] if atual[0] is not None else 'Selecione'}, Trim={atual[1] if atual[1] is not None else 'Selecione'})."

def _latest_row(df_year: pd.DataFrame) -> pd.Series:
    if df_year.empty:
        return pd.Series(dtype="float64")
    if "Data_Referencia" in df_year.columns and df_year["Data_Referencia"].notna().any():
        i = df_year["Data_Referencia"].idxmax()
        return df_year.loc[i]
    return df_year.iloc[-1]

def _to_num(x):
    try:
        return float(pd.to_numeric(x, errors="coerce"))
    except Exception:
        return np.nan

def _get_pair(df_cur: pd.DataFrame, df_prev: pd.DataFrame, col: str) -> tuple:
    v_cur = _to_num(_latest_row(df_cur).get(col, np.nan))
    v_prev = _to_num(_latest_row(df_prev).get(col, np.nan))
    return v_cur, v_prev


def apply_period_watchers():
    """
    Deve ser chamada no INÍCIO do script, antes de criar widgets.
    1) Se a carteira acabou de ser preenchida, trava o período.
    2) Se o período foi alterado para um valor definido, reseta a carteira.
    """
    # inicializa o lock na primeira execução
    st.session_state.setdefault("_periodo_lock_portfolio", (None, None))
    # aplica regras
    lock_period_if_portfolio_filled()
    reset_portfolio_on_period_change()
  
@st.cache_data(show_spinner=False)
def build_qy_panel(path_csv: str) -> pd.DataFrame:
    df = pd.read_csv(path_csv, encoding="utf-8-sig")
    if "Data_Referencia" not in df.columns:
        raise ValueError("Base sem coluna 'Data_Referencia'.")

    # normaliza
    df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    df["Data_Referencia"] = pd.to_datetime(df["Data_Referencia"], errors="coerce")
    df = df[df["Data_Referencia"] < "2025-05-01"]  # filtra datas inválidas
    df["FY"] = df["Data_Referencia"].dt.year
    df["FQ"] = df["Data_Referencia"].dt.quarter

    # Aliases
    def first_col(*cands):
        for c in cands:
            if c in df.columns:
                return c
        return None

    col_preco  = first_col("Preco_Atual", "Preco", "Close")
    col_acoes  = first_col("Acoes_Emitidas", "Qtde_Acoes", "Acoes")
    col_div    = first_col("Dividendos")
    col_jcp    = first_col("Juros_Sobre_Capital_Proprio")

    if col_preco is None:
        raise ValueError("Não encontrei coluna de preço (ex.: 'Preco_Atual', 'Preco' ou 'Close').")

    # helpers sem min_count
    def _safe_mean(s: pd.Series):
        s = pd.to_numeric(s, errors="coerce")
        return s.mean() if s.notna().any() else np.nan

    def _safe_sum(s: pd.Series):
        s = pd.to_numeric(s, errors="coerce")
        return s.sum() if s.notna().any() else np.nan

    def _last_non_null(s: pd.Series):
        s = pd.to_numeric(s, errors="coerce").ffill()
        return s.iloc[-1] if s.notna().any() else np.nan

    gb = df.sort_values(["Ticker", "Data_Referencia"]).groupby(["Ticker", "FY", "FQ"], group_keys=False)

    preco_qy = gb[col_preco].apply(_safe_mean)                      # média do preço no trimestre
    acoes_qy = gb[col_acoes].apply(_last_non_null) if col_acoes else pd.Series(np.nan, index=preco_qy.index)
    divid_qy = gb[col_div].apply(_safe_sum)   if col_div else pd.Series(0.0, index=preco_qy.index)
    jcp_qy   = gb[col_jcp].apply(_safe_sum)   if col_jcp  else pd.Series(0.0, index=preco_qy.index)

    out = (
        pd.DataFrame({
            "Preco_QY": preco_qy,
            "Acoes_Emitidas_QY": acoes_qy,
            "Dividendos_QY": divid_qy,
            "JCP_QY": jcp_qy,
        })
        .reset_index()
    )
    out["DPS_QY"] = (out["Dividendos_QY"].fillna(0.0) + out["JCP_QY"].fillna(0.0)) / out["Acoes_Emitidas_QY"]
    out.loc[~np.isfinite(out["DPS_QY"]), "DPS_QY"] = np.nan
    out["DY_QY"] = out["DPS_QY"] / out["Preco_QY"]
    return out

@st.cache_data(show_spinner=False)  
def load_base_full(path: str = "src/base_para_simulador_indicadores_refatorado.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    # garante tipos básicos
    if "Data_Referencia" in df.columns:
        df["Data_Referencia"] = pd.to_datetime(df["Data_Referencia"], errors="coerce")
        df = df[df["Data_Referencia"] < "2025-05-01"]  # filtra datas inválidas
    # garante FY/FQ se não existirem
    if "FY" not in df.columns and "Data_Referencia" in df.columns:
        df["FY"] = df["Data_Referencia"].dt.year
    if "FQ" not in df.columns and "Data_Referencia" in df.columns:
        # converte mês → trimestre
        df["FQ"] = (((df["Data_Referencia"].dt.month - 1) // 3) + 1).astype("Int64")
    # normaliza ticker
    if "Ticker" in df.columns:
        df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    return df


def _pick_first(df: pd.DataFrame, cols: list[str], default=np.nan):
    for c in cols:
        if c in df.columns:
            return df[c]
    return pd.Series(default, index=df.index if len(df.index) else pd.RangeIndex(0))

def _ensure_sim_history():
    if "sim_history" not in st.session_state:
        try:
            dfh = pd.read_csv(HISTORY_FILE)
            st.session_state["sim_history"] = dfh.to_dict(orient="records")
        except Exception:
            st.session_state["sim_history"] = []

def _portfolio_signature(portfolio: dict) -> str:
    items = []
    for t, d in sorted(portfolio.items(), key=lambda x: str(x[0]).upper()):
        q = d.get("quantidade", 0)
        p = d.get("preco_unitario", 0.0)
        items.append(f"{str(t).upper()}:{int(q)}@{float(p):.4f}")
    return "|".join(items)

def _append_or_update_history(row: dict):
    _ensure_sim_history()
    # dedupe por run_key (mesma composição + mesmo período base e fim)
    found = False
    for i, r in enumerate(st.session_state["sim_history"]):
        if r.get("run_key") == row.get("run_key"):
            st.session_state["sim_history"][i] = row
            found = True
            break
    if not found:
        st.session_state["sim_history"].append(row)
    # persiste em CSV leve (sem objetos grandes)
    try:
        dfh = pd.DataFrame(st.session_state["sim_history"])
        dfh.to_csv(HISTORY_FILE, index=False, encoding="utf-8-sig")
    except Exception:
        pass

def save_simulation_run(portfolio: dict,
                        base_fy: int, base_fq: int,
                        timeline: pd.DataFrame,
                        kpis: dict,
                        vol_anual: float, hit_ratio: float, max_dd: float):
    _ensure_sim_history()
    if timeline is None or timeline.empty or not portfolio:
        return
    end_ano = int(timeline["Ano"].iloc[-1])
    end_tri = int(timeline["Trimestre"].iloc[-1])

    sig = _portfolio_signature(portfolio)
    run_key = f"{base_fy}T{base_fq}->{end_ano}T{end_tri}|{sig}"
    ts = pd.Timestamp.now()

    valor_inicial = float(kpis.get("valor_inicial", 0.0))
    valor_final   = float(kpis.get("valor_final", 0.0))
    div_acum      = float(kpis.get("div_acum", 0.0))
    ret_total     = float(kpis.get("ret_total", np.nan))
    cagr          = float(kpis.get("cagr", np.nan))

    ret_sem_div = ((valor_final / valor_inicial) - 1.0) if valor_inicial > 0 else np.nan

    row = {
        "sim_id": f"{ts:%Y%m%d%H%M%S}",
        "timestamp": f"{ts:%Y-%m-%d %H:%M:%S}",
        "base_fy": int(base_fy), "base_fq": int(base_fq),
        "end_fy": end_ano, "end_fq": end_tri,
        "tickers": ",".join(sorted([str(t).upper() for t in portfolio.keys()])),
        "n_tickers": int(len(portfolio)),
        "valor_inicial": valor_inicial,
        "valor_final": valor_final,
        "div_acum": div_acum,
        "ret_total": ret_total,            # fração (0.18 => 18%)
        "ret_sem_div": ret_sem_div,        # fração
        "cagr": cagr,                      # fração
        "vol_anual": float(vol_anual) if np.isfinite(vol_anual) else np.nan,
        "hit_ratio": float(hit_ratio) if np.isfinite(hit_ratio) else np.nan,
        "max_dd": float(max_dd) if np.isfinite(max_dd) else np.nan,
        "run_key": run_key,
    }
    _append_or_update_history(row)

def _save_sim_history_to_disk():
    try:
        if "sim_history" in st.session_state and st.session_state["sim_history"]:
            pd.DataFrame(st.session_state["sim_history"]).to_csv(HISTORY_FILE, index=False, encoding="utf-8-sig")
    except Exception:
        pass


def log_simulation(record: dict):
    """Chame isso ao final da simulação (Página 2) para gravar na sessão + CSV."""
    st.session_state.setdefault("sim_history", [])
    st.session_state["sim_history"].append(record)
    _save_sim_history_to_disk()
    
def simulate_historical_quarterly(portfolio: dict, df_qy: pd.DataFrame, base_year: int, base_quarter: int):
    if not portfolio:
        kpis = {"valor_inicial": 0.0, "valor_final": 0.0, "div_acum": 0.0, "ret_total": np.nan, "cagr": np.nan}
        return pd.DataFrame(), kpis, [], pd.DataFrame()

    df_qy = df_qy.copy()
    df_qy["Ticker"] = df_qy["Ticker"].astype(str).str.strip().str.upper()
    portfolio = {str(k).strip().upper(): v for k, v in portfolio.items()}
    base_year, base_quarter = int(base_year), int(base_quarter)

    base = df_qy[(df_qy["FY"] == base_year) & (df_qy["FQ"] == base_quarter)][["Ticker", "Preco_QY"]].dropna()
    base_prices = dict(zip(base["Ticker"], base["Preco_QY"]))

    excluidos, valid = [], {}
    for tck, d in portfolio.items():
        if tck in base_prices and np.isfinite(base_prices[tck]):
            valid[tck] = {"qtd": int(d.get("quantidade", 0)), "preco_base": float(base_prices[tck])}
        else:
            excluidos.append(tck)
    if not valid:
        kpis = {"valor_inicial": 0.0, "valor_final": 0.0, "div_acum": 0.0, "ret_total": np.nan, "cagr": np.nan}
        return pd.DataFrame(), kpis, excluidos, pd.DataFrame()

    valor_inicial = sum(v["qtd"] * v["preco_base"] for v in valid.values())

    base_key = base_year * 4 + base_quarter
    df_qy["qkey"] = df_qy["FY"] * 4 + df_qy["FQ"]
    qkeys = sorted(df_qy.loc[df_qy["qkey"] > base_key, "qkey"].dropna().unique().tolist())
    fy_idx = df_qy.set_index(["Ticker", "FY", "FQ"])

    timeline, details_rows = [], []
    div_acum = 0.0
    valor_final = valor_inicial

    for qk in qkeys:
        ano = qk // 4
        tri = qk % 4
        if tri == 0:
            ano -= 1
            tri = 4

        valor_trim = 0.0
        div_trim = 0.0

        for tck, v in valid.items():
            preco = np.nan
            dps = 0.0
            if (tck, ano, tri) in fy_idx.index:
                row = fy_idx.loc[(tck, ano, tri)]
                preco = float(row.get("Preco_QY")) if np.isfinite(row.get("Preco_QY")) else np.nan
                dps   = float(row.get("DPS_QY"))   if np.isfinite(row.get("DPS_QY"))   else 0.0

            qtd = v["qtd"]
            valor_ticker = (qtd * preco) if np.isfinite(preco) else np.nan
            div_ticker   = qtd * dps
            if np.isfinite(valor_ticker):
                valor_trim += valor_ticker
            div_trim += div_ticker

            details_rows.append({
                "Ano": int(ano), "Trimestre": int(tri), "Ticker": tck,
                "Valor_Ticker": valor_ticker, "Dividendos_Ticker": div_ticker
            })

        div_acum += div_trim
        valor_final = valor_trim if np.isfinite(valor_trim) else valor_final
        timeline.append({"Ano": int(ano), "Trimestre": int(tri), "Valor_Sem_Dividendos": valor_trim, "Dividendos_Trimestre": div_trim})

    n_quarters = len(qkeys)
    ret_total = ((valor_final + div_acum - valor_inicial) / valor_inicial) if valor_inicial > 0 else np.nan
    cagr = (((valor_final + div_acum) / valor_inicial) ** (4 / n_quarters) - 1) if (valor_inicial > 0 and n_quarters > 0) else np.nan
    kpis = {"valor_inicial": float(valor_inicial), "valor_final": float(valor_final), "div_acum": float(div_acum),
            "ret_total": float(ret_total) if np.isfinite(ret_total) else np.nan,
            "cagr": float(cagr) if np.isfinite(cagr) else np.nan}

    details = pd.DataFrame(details_rows)
    return pd.DataFrame(timeline), kpis, excluidos, details

def _prep_timeline_quarterly(timeline: pd.DataFrame) -> pd.DataFrame:
    tl = timeline.copy()
    tl["Ano"] = pd.to_numeric(tl["Ano"], errors="coerce").astype("Int64")
    tl["Trimestre"] = pd.to_numeric(tl["Trimestre"], errors="coerce").astype("Int64")

    # cria uma data do fim do trimestre para usar no eixo X temporal
    tl["Periodo"] = pd.PeriodIndex(year=tl["Ano"].astype("float").astype("Int64"),
                                   quarter=tl["Trimestre"].astype("float").astype("Int64"),
                                   freq="Q").to_timestamp(how="end")
    tl = tl.sort_values("Periodo").reset_index(drop=True)

    # derivados
    tl["Div_Acumulado"] = tl["Dividendos_Trimestre"].fillna(0).cumsum()
    tl["Valor_Total"] = tl["Valor_Sem_Dividendos"].fillna(0) + tl["Div_Acumulado"]

    # drawdown sobre Valor_Sem_Dividendos (sem dividendos)
    v = tl["Valor_Sem_Dividendos"].astype(float)
    roll_max = v.cummax()
    with np.errstate(divide="ignore", invalid="ignore"):
        tl["Drawdown"] = (v / roll_max) - 1.0
    return tl

def _prep_metrics_quarterly(tl: pd.DataFrame, valor_inicial: float) -> tuple[pd.DataFrame, float, float, float]:
    """
    tl: DataFrame da simulação trimestral com colunas:
        Ano, Trimestre, Valor_Sem_Dividendos, Dividendos_Trimestre
    valor_inicial: float com o valor inicial da carteira no trimestre-base.

    Retorna: (tl_enriquecido, vol_anualizada, hit_ratio, max_drawdown)
    """
    tl = tl.sort_values(["Ano", "Trimestre"]).reset_index(drop=True).copy()

    # Base para retorno do 1º trimestre pós-base = valor_inicial;
    # depois disso, usa o Valor_Sem_Dividendos do trimestre anterior.
    base_vals = [valor_inicial] + tl["Valor_Sem_Dividendos"].tolist()[:-1]
    base_vals = pd.Series(base_vals, index=tl.index, dtype=float)

    # Retorno total do trimestre (preço + dividendo)
    with np.errstate(divide="ignore", invalid="ignore"):
        ret = ((tl["Valor_Sem_Dividendos"].astype(float) + tl["Dividendos_Trimestre"].astype(float)) / base_vals) - 1.0
    tl["Retorno_Trimestre"] = ret

    # Vol anualizada (desvio-padrão dos retornos trimestrais × √4)
    valid_ret = ret[np.isfinite(ret)]
    vol_anual = valid_ret.std(ddof=0) * (4 ** 0.5) if len(valid_ret) > 1 else np.nan

    # Hit ratio = % de trimestres com retorno positivo
    hit = (valid_ret > 0).mean() if len(valid_ret) > 0 else np.nan

    # Drawdown (sobre Valor_Sem_Dividendos; dividendos não entram no pico)
    v = tl["Valor_Sem_Dividendos"].astype(float)
    roll_max = v.cummax()
    with np.errstate(divide="ignore", invalid="ignore"):
        dd = (v / roll_max) - 1.0
    tl["Drawdown"] = dd
    mmdd = dd.min() if len(dd) else np.nan

    return tl, (float(vol_anual) if np.isfinite(vol_anual) else np.nan), \
              (float(hit) if np.isfinite(hit) else np.nan), \
              (float(mmdd) if np.isfinite(mmdd) else np.nan)

@st.cache_data(show_spinner=True)
def load_base(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=",", decimal=".", encoding="utf-8-sig", engine="python")
    # Tipos básicos
    if "Data_Referencia" in df.columns:
        df["Data_Referencia"] = pd.to_datetime(df["Data_Referencia"], errors="coerce")
        df = df[df["Data_Referencia"] < "2025-05-01"]  # filtra datas inválidas
    # Normaliza campos numéricos usados nos filtros (garantir coerção)
    for col in ["Dividend_Yield", "Preco_Lucro", "ROE"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

@st.cache_data(show_spinner=False)
def latest_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """Mantém apenas a última linha por Ticker, com base em Data_Referencia."""
    if "Data_Referencia" in df.columns:
        idx = df.sort_values(["Ticker", "Data_Referencia"]).groupby("Ticker")["Data_Referencia"].idxmax()
        snap = df.loc[idx].copy()
    else:
        snap = df.drop_duplicates(subset=["Ticker"]).copy()
    return snap

def _sync_filters_from_query():
    """Se o filtro ainda não está no session_state, popula a partir de st.query_params."""
    qp = st.query_params
    for s_key, q_key in FILTER_STATE_MAP.items():
        if s_key not in st.session_state and q_key in qp:
            val = qp[q_key]
            if isinstance(val, list):
                val = val[0]
            if s_key in ("filtro_ano", "filtro_tri"):
                try:
                    val = int(val)
                except Exception:
                    pass
            st.session_state[s_key] = val

def _push_filters_to_query():
    """Empurra o estado atual dos filtros para a querystring."""
    payload = {}
    for s_key, q_key in FILTER_STATE_MAP.items():
        val = st.session_state.get(s_key, None)
        if val not in (None, ""):
            payload[q_key] = str(val)
    if payload:
        st.query_params.update(payload)

def goto(page: str, **overrides):
    """Navega preservando filtros na querystring. Use sempre em vez de manipular query_params diretamente."""
    payload = {"page": page}
    # preserva filtros atuais
    for s_key, q_key in FILTER_STATE_MAP.items():
        val = st.session_state.get(s_key, None)
        if val not in (None, ""):
            payload[q_key] = str(val)
    # permite sobrescrever algo específico
    for k, v in overrides.items():
        payload[k] = str(v)
    st.query_params.update(payload)
    st.session_state["page"] = page
    st.rerun()


    