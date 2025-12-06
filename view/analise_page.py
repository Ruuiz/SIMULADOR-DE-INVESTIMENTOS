import streamlit as st
import pandas as pd
import numpy as np
import controller.utils as utils


# =======================
# Pagina 3 - Analise aprofundada
# =======================

def _abbr_currency(v: float) -> str:
    if not np.isfinite(v):
        return "n/d"
    a = abs(v)
    if a >= 1e12:
        return f"R$ {v/1e12:,.2f}T"
    if a >= 1e9:
        return f"R$ {v/1e9:,.2f}B"
    if a >= 1e6:
        return f"R$ {v/1e6:,.2f}M"
    return f"R$ {v:,.2f}"

def _get_session_filters_for_analysis() -> tuple[str, int, int]:

    # ticker
    tck = st.session_state.get("selected_ticker") or st.session_state.get("analise_ticker")
    if not tck:
        # fallback: se a carteira tiver 1 ativo, usar
        pf = st.session_state.get("portfolio", {})
        if isinstance(pf, dict) and len(pf) == 1:
            tck = list(pf.keys())[0]
    tck = str(tck).strip().upper() if tck else None

    # período (respeita o lock criado na Página 1)
    ano = st.session_state.get("filtro_ano")
    tri = st.session_state.get("filtro_tri")
    lock_ano, lock_tri = st.session_state.get("_periodo_lock_portfolio", (None, None))
    if ano in (None, "Selecione"): ano = lock_ano
    if tri in (None, "Selecione"): tri = lock_tri

    try:
        ano = int(ano) if ano is not None else None
        tri = int(tri) if tri is not None else None
    except Exception:
        ano, tri = None, None

    return tck, ano, tri


def render_analise():
    # Navegação para voltar
    cols_top = st.columns([1, 8])
    with cols_top[0]:
        if st.button("← Voltar", key="analise_btn_voltar"):
            utils.goto("lista")  # não limpa nada aqui
            return

    with cols_top[1]:
        st.header("Análise aprofundada da ação")

    # Carrega base e filtros herdados da Página 1
    df_full = utils.load_base_full("src/base_para_simulador_indicadores_refatorado.csv")
    tck, fy, fq = _get_session_filters_for_analysis()

    # Se não há Ticker definido, deixa o usuário escolher agora (apenas aqui)
    if not tck:
        st.info("Selecione um **Ticker** para analisar.")
        lista = sorted(df_full["Ticker"].dropna().unique().tolist())
        picked = st.selectbox("Ticker", options=lista, index=None, placeholder="Escolha o papel", key="analise_pick_ticker")
        if picked:
            st.session_state["analise_ticker"] = str(picked).upper()
            st.rerun()
        return

    # Valida período
    if fy is None:
        st.warning("Selecione **Ano (FY)** na Página 1 para ancorar a análise.")
        return

    # Fatiamento: atual (FY) e anterior (FY-1)
    df_t = df_full[df_full["Ticker"] == tck].copy()
    df_cur = df_t[df_t["FY"] == fy].copy()
    df_prev = df_t[df_t["FY"] == (fy - 1)].copy()

    if df_cur.empty:
        st.warning(f"Não há dados para {tck} no FY {fy}. Ajuste o filtro de Ano na Página 1.")
        return

    # Identidade & cabeçalho rico
    setor_col = "Setor_Oficial_final" if "Setor_Oficial_final" in df_full.columns else utils._pick_first(df_cur, ["Setor_Oficial", "Sector"]).name
    setor_val = df_cur[setor_col].iloc[0] if setor_col in df_cur.columns and not df_cur[setor_col].isna().all() else "—"

    # Preço médio do ano (se existir painel trimestral, depois poderemos mostrar intranuais)
    preco_cols = ["Preco_FY", "Preco_Atual", "Close"]
    preco_atual = None
    for c in preco_cols:
        if c in df_cur.columns and df_cur[c].notna().any():
            preco_atual = float(df_cur[c].dropna().iloc[-1])
            break

    st.subheader(f"{tck} — FY {fy}")
    cA, cB, cC, cD = st.columns(4)
    cA.metric("Setor", f"{setor_val}")
    cB.metric("Preço (base FY)", f"R$ {preco_atual:,.2f}" if preco_atual is not None else "n/d")
    cC.metric("FY anterior", f"{fy-1}" if not df_prev.empty else "n/d")
    # cD.metric("Trimestre filtrado (FQ)", f"{fq}" if fq is not None else "—")

    st.markdown("---")

    # Guarda no estado o ticker analisado (para navegação consistente)
    st.session_state["analise_ticker"] = tck

    # Placeholders (clusters) — próximos passos: preencher com os gráficos e comparativos
    with st.container():
        st.subheader("Indicadores-chave (resumo)")
        st.caption("Aqui vão cards de EV/EBIT, P/L, ROE, ROIC, DY, etc., comparando FY vs. FY-1 e vs. setor.")

    with st.container():
        st.subheader("Valuation")

        setor_col = "Setor_Oficial_final" if "Setor_Oficial_final" in df_full.columns else "Setor_Oficial"
        setor_val = utils._latest_row(df_cur).get(setor_col, "—")

        # Indicadores (menor = melhor)
        val_cols = ["EV_EBIT", "Preco_Lucro", "Preco_PVP", "Payout_TTM", "EV_Receita"]
        better_low = {"EV_EBIT", "Preco_Lucro", "Preco_PVP", "Payout_TTM", "EV_Receita"}

        df_sec = df_full[(df_full[setor_col] == setor_val) & (df_full["FY"] == fy)].copy() if setor_val != "—" else pd.DataFrame()

        cards = []
        for col in val_cols:
            v_cur, v_prev = utils._get_pair(df_cur, df_prev, col)

            # média do setor no FY corrente
            if not df_sec.empty and col in df_sec.columns:
                sec_series = pd.to_numeric(df_sec[col], errors="coerce")
                sec_mean = float(sec_series.mean()) if sec_series.notna().any() else np.nan
            else:
                sec_mean = np.nan

            # valor mostrado (bruto; mantenho formato simples para múltiplos)
            value_str = f"{v_cur:.2f}" if np.isfinite(v_cur) else "n/d"

            # deltas relativos (%) — sinal negativo = melhor para "menor = melhor"
            delta_sector_pct = (v_cur / sec_mean - 1.0) * 100.0 if (np.isfinite(v_cur) and np.isfinite(sec_mean) and sec_mean != 0) else None
            delta_yoy_pct    = (v_cur / v_prev - 1.0) * 100.0   if (np.isfinite(v_cur) and np.isfinite(v_prev) and v_prev != 0)    else None

            # contexto completo (mostrado como caption)
            parts = []
            if delta_sector_pct is not None:
                parts.append(f"Setor {delta_sector_pct:+.1f}%")
            if delta_yoy_pct is not None:
                parts.append(f"FY-1 {delta_yoy_pct:+.1f}%")
            delta_context = " | ".join(parts) if parts else None

            # referência primária para o delta numérico único do st.metric
            ref_cmp = delta_sector_pct if delta_sector_pct is not None else delta_yoy_pct
            delta_str = f"{ref_cmp:+.1f}%" if ref_cmp is not None else "—"

            # como "menor = melhor", use 'inverse' (negativo = verde)
            delta_cor = "inverse"

            cards.append((col, value_str, delta_str, delta_cor, delta_context))

        # Renderização
        cols = st.columns(len(cards))
        for i, (label, value_str, delta_str, delta_cor, delta_context) in enumerate(cards):
            with cols[i]:
                st.metric(label=label, value=value_str, delta=delta_str, delta_color=delta_cor)
                if delta_context and delta_context != delta_str:
                    st.caption(delta_context)

        st.markdown("---")

    with st.container():
        st.subheader("Lucratividade")

        # Definição de setor do papel
        setor_col = "Setor_Oficial_final" if "Setor_Oficial_final" in df_full.columns else "Setor_Oficial"
        setor_val = utils._latest_row(df_cur).get(setor_col, "—")

        # Indicadores (maior = melhor)
        luc_cols = ["ROE", "ROIC", "Margem_EBIT_Sector", "Margem_Liquida_Sector", "Margem_Bruta"]

        df_sec = df_full[(df_full[setor_col] == setor_val) & (df_full["FY"] == fy)].copy() if setor_val != "—" else pd.DataFrame()

        cards = []
        for col in luc_cols:
            v_cur, v_prev = utils._get_pair(df_cur, df_prev, col)  # fração (ex.: 0.123)

            # média setorial (fração) no FY corrente
            if not df_sec.empty and col in df_sec.columns:
                sec_series = pd.to_numeric(df_sec[col], errors="coerce")
                sec_mean = float(sec_series.mean()) if sec_series.notna().any() else np.nan
            else:
                sec_mean = np.nan

            # valor mostrado (%)
            value_str = f"{(v_cur * 100):.2f}%" if np.isfinite(v_cur) else "n/d"

            # deltas em p.p. (numéricos)
            delta_sector_pp = ((v_cur - sec_mean) * 100) if (np.isfinite(v_cur) and np.isfinite(sec_mean)) else None
            delta_yoy_pp    = ((v_cur - v_prev)   * 100) if (np.isfinite(v_cur) and np.isfinite(v_prev))   else None

            # texto de contexto (para help/caption)
            parts = []
            if delta_sector_pp is not None:
                parts.append(f"Setor {delta_sector_pp:+.1f} p.p.")
            if delta_yoy_pp is not None:
                parts.append(f"FY-1 {delta_yoy_pp:+.1f} p.p.")
            delta_context = " | ".join(parts) if parts else None

            # referência primária para cor **e** sinal do delta
            ref_cmp = delta_sector_pp if delta_sector_pp is not None else delta_yoy_pp
            delta_str = f"{ref_cmp:+.1f} p.p." if ref_cmp is not None else "—"

            # para lucratividade (maior = melhor) a direção é 'normal'
            delta_cor = "normal"   # positivo=verde, negativo=vermelho

            cards.append((col, value_str, delta_str, delta_cor, delta_context))

        # Renderização
        cols = st.columns(len(cards))
        for i, (label, value_str, delta_str, delta_cor, delta_context) in enumerate(cards):
            with cols[i]:
                st.metric(label=label, value=value_str, delta=delta_str, delta_color=delta_cor)
                if delta_context and delta_context != delta_str:
                    st.caption(delta_context)

        st.markdown("---")

    with st.container():
        st.subheader("Eficiência operacional")

        setor_col = "Setor_Oficial_final" if "Setor_Oficial_final" in df_full.columns else "Setor_Oficial"
        setor_val = utils._latest_row(df_cur).get(setor_col, "—")

        is_fin = False
        if isinstance(setor_val, str):
            s = setor_val.lower()
            is_fin = ("financial" in s) or ("financeiro" in s) or ("banco" in s) or ("financial services" in s)

        cols_receita = "Receita_Total_FY" if is_fin else "Receita_Liquida_FY"
        if cols_receita not in df_full.columns:
            cols_receita = "Receita_Total_TTM" if is_fin else "Receita_Liquida_TTM"

        col_ebit = "EBIT_FY"
        if col_ebit not in df_full.columns:
            col_ebit = "EBIT_TTM"
        if is_fin and col_ebit not in df_full.columns:
            col_ebit = "Lucro_Operacional_FY" if "Lucro_Operacional_FY" in df_full.columns else ("Lucro_Operacional_TTM" if "Lucro_Operacional_TTM" in df_full.columns else col_ebit)

        eff_cols = ["Giro_Ativos", cols_receita, col_ebit]
        labels = {"Giro_Ativos": "Giro de Ativos", cols_receita: "Receita", col_ebit: "EBIT/Operacional"}

        df_sec = df_full[(df_full[setor_col] == setor_val) & (df_full["FY"] == fy)].copy() if setor_val != "—" else pd.DataFrame()

        def _fmt_eff(col, v):
            if not np.isfinite(v):
                return "n/d"
            if col == "Giro_Ativos":
                return f"{v:.2f}x"
            if col in (cols_receita, col_ebit):
                return _abbr_currency(v)
            return f"{v:.2f}"

        cards = []
        for col in eff_cols:
            v_cur, v_prev = utils._get_pair(df_cur, df_prev, col)

            # média setorial no FY corrente (mesma unidade da métrica)
            if not df_sec.empty and col in df_sec.columns:
                sec_series = pd.to_numeric(df_sec[col], errors="coerce")
                sec_mean = float(sec_series.mean()) if sec_series.notna().any() else np.nan
            else:
                sec_mean = np.nan

            value_str = _fmt_eff(col, v_cur)

            # deltas relativos (%) — maior = melhor (positivo tende a ser bom)
            delta_sector_pct = (v_cur / sec_mean - 1.0) * 100.0 if (np.isfinite(v_cur) and np.isfinite(sec_mean) and sec_mean != 0) else None
            delta_yoy_pct    = (v_cur / v_prev - 1.0) * 100.0   if (np.isfinite(v_cur) and np.isfinite(v_prev) and v_prev != 0)    else None

            # contexto completo para caption
            parts = []
            if delta_sector_pct is not None:
                parts.append(f"vs setor {delta_sector_pct:+.1f}%")
            if delta_yoy_pct is not None:
                parts.append(f"vs FY-1 {delta_yoy_pct:+.1f}%")
            delta_context = " | ".join(parts) if parts else None

            # referência primária para cor e sinal do metric
            ref_cmp = delta_sector_pct if delta_sector_pct is not None else delta_yoy_pct
            delta_str = f"{ref_cmp:+.1f}%" if ref_cmp is not None else "—"

            # aqui é maior=melhor
            delta_cor = "normal"

            cards.append((labels.get(col, col), value_str, delta_str, delta_cor, delta_context))

        # Renderização
        cols = st.columns(len(cards))
        for i, (label, value_str, delta_str, delta_cor, delta_context) in enumerate(cards):
            with cols[i]:
                st.metric(label=label, value=value_str, delta=delta_str, delta_color=delta_cor)
                if delta_context and delta_context != delta_str:
                    st.caption(delta_context)

        st.markdown("**Notas**")
        st.caption(
            "- Em **Financeiras/Bancos**, usa-se `Receita Total` e pode-se usar `Lucro Operacional` como fallback ao EBIT.\n"
            "- `Giro de Ativos` pode distorcer entre setores; aqui a comparação é **intra-setor** no FY, mas ainda assim interprete com cautela para bancos."
        )
        st.markdown("---")


        with st.container():
            st.subheader("Estrutura de capital & Liquidez")

            setor_col = "Setor_Oficial_final" if "Setor_Oficial_final" in df_full.columns else "Setor_Oficial"
            setor_val = utils._latest_row(df_cur).get(setor_col, "—")

            cap_cols = [
                "Net_Debt",
                "NetDebt_EBIT",
                "NetDebt_Patrimonio",
                "Patrimonio_Ativos",
                "Passivos_Ativos",
                "Liquidez_Corrente_Calc",
                "Capital_Giro",
            ]
            better_low = {"NetDebt_EBIT", "NetDebt_Patrimonio", "Passivos_Ativos", "Net_Debt"}  # menor = melhor
            pp_cols    = {"Patrimonio_Ativos", "Passivos_Ativos"}

            labels = {
                "Net_Debt": "Dívida Líquida",
                "NetDebt_EBIT": "Dív. Líq./EBIT",
                "NetDebt_Patrimonio": "Dív. Líq./Patrimônio",
                "Patrimonio_Ativos": "Patrimônio / Ativos",
                "Passivos_Ativos": "Passivos / Ativos",
                "Liquidez_Corrente_Calc": "Liquidez Corrente",
                "Capital_Giro": "Capital de Giro",
            }

            df_sec = df_full[(df_full[setor_col] == setor_val) & (df_full["FY"] == fy)].copy() if setor_val != "—" else pd.DataFrame()

            def _fmt_cap(col, v):
                if not np.isfinite(v):
                    return "n/d"
                if col in {"Patrimonio_Ativos", "Passivos_Ativos"}:
                    return f"{v*100:.2f}%"
                if col in {"Liquidez_Corrente_Calc", "NetDebt_EBIT", "NetDebt_Patrimonio"}:
                    return f"{v:.2f}x"
                if col in {"Net_Debt", "Capital_Giro"}:
                    return _abbr_currency(v)
                return f"{v:.2f}"

            def _delta_text(col, v_cur, ref_val):
                """Retorna (texto_formatado, valor_bruto) — p.p. para frações e % para razões/valores"""
                if not (np.isfinite(v_cur) and np.isfinite(ref_val)):
                    return None, None
                if col in pp_cols:
                    d_pp = (v_cur - ref_val) * 100.0
                    return f"{d_pp:+.1f} p.p.", d_pp
                if ref_val == 0:
                    return None, None
                d_pct = (v_cur / ref_val - 1.0) * 100.0
                return f"{d_pct:+.1f}%", d_pct

            def _fmt_delta_single(col, raw):
                if raw is None:
                    return "—"
                return f"{raw:+.1f} p.p." if col in pp_cols else f"{raw:+.1f}%"

            cards = []
            for col in cap_cols:
                v_cur, v_prev = utils._get_pair(df_cur, df_prev, col)

                # média setorial no FY (mesma unidade da métrica)
                if not df_sec.empty and col in df_sec.columns:
                    sec_series = pd.to_numeric(df_sec[col], errors="coerce")
                    sec_mean = float(sec_series.mean()) if sec_series.notna().any() else np.nan
                else:
                    sec_mean = np.nan

                value_str = _fmt_cap(col, v_cur)

                # deltas (texto completo p/ caption) e brutos (número único p/ st.metric)
                txt_sec, raw_sec = _delta_text(col, v_cur, sec_mean)
                txt_yoy, raw_yoy = _delta_text(col, v_cur, v_prev)

                parts = []
                if txt_sec is not None:
                    parts.append(f"vs setor {txt_sec}")
                if txt_yoy is not None:
                    parts.append(f"vs FY-1 {txt_yoy}")
                delta_context = " | ".join(parts) if parts else None

                # delta único e direção de cor
                ref_cmp_raw = raw_sec if raw_sec is not None else raw_yoy
                delta_str = _fmt_delta_single(col, ref_cmp_raw)

                delta_cor = "inverse" if col in better_low else "normal"

                cards.append((labels.get(col, col), value_str, delta_str, delta_cor, delta_context))

            # Renderização em duas linhas (como no seu código)
            n = len(cards)
            mid = (n + 1) // 2
            row1, row2 = cards[:mid], cards[mid:]

            cols1 = st.columns(len(row1))
            for i, (label, value_str, delta_str, delta_cor, delta_context) in enumerate(row1):
                with cols1[i]:
                    st.metric(label=label, value=value_str, delta=delta_str, delta_color=delta_cor)
                    if delta_context and delta_context != delta_str:
                        st.caption(delta_context)

            if row2:
                cols2 = st.columns(len(row2))
                for i, (label, value_str, delta_str, delta_cor, delta_context) in enumerate(row2):
                    with cols2[i]:
                        # st.metric(label=label, value=value_str, delta=delta_cor)
                        st.metric(label=label, value=value_str, delta=delta_str, delta_color=delta_cor)  # <- linha correta
                        if delta_context and delta_context != delta_str:
                            st.caption(delta_context)

            st.caption(
                "- Leituras: dívida/alavancagem (**menor = melhor**), patrimônio/ativos e liquidez (**maior = melhor**). "
                "Dívida Líquida absoluta depende do porte — dê preferência às razões para comparação."
            )
            st.markdown("---")


    with st.container():
        st.subheader("Por ação & Dividendos")

        # Detecta financeiro (para escolher a coluna correta de Receita por ação)
        setor_col = "Setor_Oficial_final" if "Setor_Oficial_final" in df_full.columns else "Setor_Oficial"
        setor_val = utils._latest_row(df_cur).get(setor_col, "—")
        is_fin = False
        if isinstance(setor_val, str):
            s = setor_val.lower()
            is_fin = ("financial" in s) or ("financeiro" in s) or ("banco" in s) or ("financial services" in s)

        receita_ps_col = "Receita_Total_per_share" if is_fin else "Receita_Liquida_per_share"
        if receita_ps_col not in df_full.columns:
            receita_ps_col = "Receita_Total_per_share" if "Receita_Total_per_share" in df_full.columns else "Receita_Liquida_per_share"

        # Base setorial no FY corrente
        df_sec = df_full[(df_full[setor_col] == setor_val) & (df_full["FY"] == fy)].copy() if setor_val != "—" else pd.DataFrame()

        # DPS (dividendo por ação) FY — calcula par FY/FY-1
        def _get_dps_pair(df_c: pd.DataFrame, df_p: pd.DataFrame):
            def _extract(df_):
                if "DPS_FY" in df_.columns and df_["DPS_FY"].notna().any():
                    return utils._to_num(utils._latest_row(df_).get("DPS_FY"))
                div = utils._to_num(utils._latest_row(df_).get("Dividendos_FY")) if "Dividendos_FY" in df_.columns else np.nan
                jcp = utils._to_num(utils._latest_row(df_).get("Juros_Sobre_Capital_Proprio_FY")) if "Juros_Sobre_Capital_Proprio_FY" in df_.columns else np.nan
                shs = utils._to_num(utils._latest_row(df_).get("Acoes_Emitidas")) if "Acoes_Emitidas" in df_.columns else np.nan
                if np.isfinite(div) or np.isfinite(jcp):
                    num = (0 if not np.isfinite(div) else div) + (0 if not np.isfinite(jcp) else jcp)
                    return (num / shs) if (np.isfinite(shs) and shs > 0) else np.nan
                return np.nan
            return _extract(df_c), _extract(df_p)

        # Itens do cluster (coluna, rótulo, tipo="money"|"rate")
        pa_items = [
            ("LPA_calc",           "LPA (lucro por ação)",         "money"),
            ("VPA_calc",           "VPA (valor patrimonial/ação)", "money"),
            ("EBIT_per_share",     "EBIT por ação",                "money"),
            (receita_ps_col,       "Receita por ação",             "money"),
            ("Payout_TTM",         "Payout (TTM)",                 "rate"),
            ("Dividend_Yield_TTM", "Dividend Yield (TTM)",         "rate"),
            ("DY_Medio_5anos",     "DY médio 5 anos",              "rate"),
        ]

        def _fmt_pa(kind, v):
            if not np.isfinite(v):
                return "n/d"
            if kind == "money":  # valores por ação (R$)
                return f"R$ {v:,.2f}"
            if kind == "rate":   # frações (ex.: 0.12)
                return f"{v*100:.2f}%"
            return f"{v:.2f}"

        def _delta_text_pa(kind, v_cur, ref_val):
            """rate => p.p.; money => % relativo"""
            if not (np.isfinite(v_cur) and np.isfinite(ref_val)):
                return None, None
            if kind == "rate":
                d_pp = (v_cur - ref_val) * 100.0
                return f"{d_pp:+.1f} p.p.", d_pp  # valor base para cor
            # money
            if ref_val == 0:
                return None, None
            d_pct = (v_cur / ref_val - 1.0) * 100.0
            return f"{d_pct:+.1f}%", d_pct

        def _fmt_delta_single(kind, raw):
            if raw is None:
                return "—"
            return f"{raw:+.1f} p.p." if kind == "rate" else f"{raw:+.1f}%"

        # Payout = menor = melhor (coerente com Valuation)
        inverse_set = {"Payout_TTM"}

        cards = []

        # Monta cards para LPA/VPA/EBIT_ps/Receita_ps + Payout/DY/DY5y
        for col, label, kind in pa_items:
            v_cur, v_prev = utils._get_pair(df_cur, df_prev, col)

            # média setorial (FY)
            if not df_sec.empty and col in df_sec.columns:
                sec_series = pd.to_numeric(df_sec[col], errors="coerce")
                sec_mean = float(sec_series.mean()) if sec_series.notna().any() else np.nan
            else:
                sec_mean = np.nan

            value_str = _fmt_pa(kind, v_cur)

            # deltas (texto p/ caption) + valor bruto p/ st.metric
            txt_sec, raw_sec = _delta_text_pa(kind, v_cur, sec_mean)
            txt_yoy, raw_yoy = _delta_text_pa(kind, v_cur, v_prev)

            parts = []
            if txt_sec is not None:
                parts.append(f"vs setor {txt_sec}")
            if txt_yoy is not None:
                parts.append(f"vs FY-1 {txt_yoy}")
            delta_context = " | ".join(parts) if parts else None

            ref_cmp_raw = raw_sec if raw_sec is not None else raw_yoy
            delta_str = _fmt_delta_single(kind, ref_cmp_raw)

            # direção de cor: payout é 'inverse'; demais, 'normal'
            delta_cor = "inverse" if col in inverse_set else "normal"

            cards.append((label, value_str, delta_str, delta_cor, delta_context))

        # --- Card de DPS (FY) ---
        dps_cur, dps_prev = _get_dps_pair(df_cur, df_prev)
        value_str = _fmt_pa("money", dps_cur)

        # média setorial p/ DPS (com fallback de composição)
        if not df_sec.empty:
            if "DPS_FY" in df_sec.columns:
                sec_dps_mean = pd.to_numeric(df_sec["DPS_FY"], errors="coerce").mean()
            elif {"Dividendos_FY", "Juros_Sobre_Capital_Proprio_FY", "Acoes_Emitidas"}.issubset(df_sec.columns):
                _num = pd.to_numeric(df_sec["Dividendos_FY"], errors="coerce").fillna(0) + \
                    pd.to_numeric(df_sec["Juros_Sobre_Capital_Proprio_FY"], errors="coerce").fillna(0)
                _den = pd.to_numeric(df_sec["Acoes_Emitidas"], errors="coerce")
                sec_dps_series = _num / _den.replace(0, np.nan)
                sec_dps_mean = sec_dps_series.mean()
            else:
                sec_dps_mean = np.nan
        else:
            sec_dps_mean = np.nan

        txt_sec_dps, raw_sec_dps = _delta_text_pa("money", dps_cur, sec_dps_mean)
        txt_yoy_dps, raw_yoy_dps = _delta_text_pa("money", dps_cur, dps_prev)

        parts = []
        if txt_sec_dps is not None:
            parts.append(f"vs setor {txt_sec_dps}")
        if txt_yoy_dps is not None:
            parts.append(f"vs FY-1 {txt_yoy_dps}")
        delta_context_dps = " | ".join(parts) if parts else None

        ref_cmp_raw_dps = raw_sec_dps if raw_sec_dps is not None else raw_yoy_dps
        delta_str_dps = _fmt_delta_single("money", ref_cmp_raw_dps)

        cards.append(("DPS (FY)", value_str, delta_str_dps, "normal", delta_context_dps))

        # --- Render (duas linhas, sem duplicar) ---
        n = len(cards)
        mid = (n + 1) // 2
        row1, row2 = cards[:mid], cards[mid:]

        def _render_row(row):
            cols = st.columns(len(row))
            for i, (label, value_str, delta_str, delta_cor, delta_context) in enumerate(row):
                with cols[i]:
                    st.metric(label=label, value=value_str, delta=delta_str, delta_color=delta_cor)
                    if delta_context and delta_context != delta_str:
                        st.caption(delta_context)

        if row1:
            _render_row(row1)
        if row2:
            _render_row(row2)

        st.caption(
            "- Em **Financeiras/Bancos**, usa-se `Receita Total` como base para receita por ação.\n"
            "- `Payout` e `Dividend Yield` são calculados em TTM (últimos 12 meses) para refletir pagamentos recentes."
        )
        st.markdown("---")


    with st.container():
        st.subheader("Dados utilizados")

        # Quais colunas expor (agrupa o que foi usado nos clusters)
        cols_show = [
            # Valuation
            "EV_EBIT", "Preco_Lucro", "P_VP", "PSR_calc", "EV_Receita",
            # Lucratividade
            "ROE", "ROIC", "Margem_EBIT_Sector", "Margem_Liquida_Sector", "Margem_Bruta",
            # Eficiência
            "Giro_Ativos", "Receita_Liquida_FY", "Receita_Total_FY", "EBIT_FY", "Receita_Liquida_TTM", "Receita_Total_TTM", "EBIT_TTM",
            # Estrutura/Liquidez
            "Net_Debt", "NetDebt_EBIT", "NetDebt_Patrimonio", "Patrimonio_Ativos", "Passivos_Ativos", "Liquidez_Corrente_Calc", "Capital_Giro",
            # Por ação & Dividendos
            "LPA_calc", "VPA_calc", "EBIT_per_share", "Receita_Liquida_per_share", "Receita_Total_per_share",
            "Payout_TTM", "Dividend_Yield_TTM", "DY_Medio_5anos"
        ]
        # Heurística da "origem" (pelo sufixo)
        def _origin(col):
            if col.endswith("_FY"): return "FY"
            if col.endswith("_TTM"): return "TTM"
            if col.endswith("_AVG4Q"): return "AVG4Q"
            # indicadores calculados sem sufixo
            return "Calc/Spot"

        cur_row = utils._latest_row(df_cur)
        prev_row = utils._latest_row(df_prev) if not df_prev.empty else pd.Series(dtype="float64")

        out = []
        for col in cols_show:
            if col not in df_full.columns: 
                continue
            out.append({
                "Campo": col,
                "Origem": _origin(col),
                f"FY {fy}": utils._to_num(cur_row.get(col, np.nan)),
                f"FY {fy-1}": utils._to_num(prev_row.get(col, np.nan)) if not df_prev.empty else np.nan
            })

        # DPS FY (se existiu/composição)
        out.append({
            "Campo": "DPS_FY",
            "Origem": "FY (composto se faltante)",
            f"FY {fy}": dps_cur if 'dps_cur' in locals() else np.nan,
            f"FY {fy-1}": dps_prev if 'dps_prev' in locals() else np.nan
        })

        tbl = pd.DataFrame(out)
        for c in tbl.columns:
            if c.startswith("FY "):
                tbl[c] = pd.to_numeric(tbl[c], errors="coerce").round(2)

        # Humaniza lista de tickers se vier como list
        if "Tickers" in tbl.columns:
            tbl["Tickers"] = tbl["Tickers"].apply(
                lambda v: ", ".join(v) if isinstance(v, (list, tuple)) else (str(v) if pd.notna(v) else "")
            )

        st.dataframe(tbl, hide_index=True, use_container_width=True)

        csv = tbl.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "Baixar dados utilizados (.CSV)",
            data=csv,
            file_name=f"dados_utilizados_{tck}_FY{fy}.csv",
            mime="text/csv",
            key="btn_download_dados_utilizados"
        )
