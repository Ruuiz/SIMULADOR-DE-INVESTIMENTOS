import streamlit as st
import pandas as pd
import numpy as np
import controller.utils as utils
import altair as alt



# =======================
# Pagina 2
# =======================

def render_simulacao():
    if st.button("← Voltar para a lista", key="sim_btn_voltar_lista"):
        st.session_state["portfolio"] = {}
        st.session_state["_periodo_lock_portfolio"] = (None, None)
        st.session_state.pop("_portfolio_reset_message", None)
        utils.goto("lista")

    st.header("Simulação histórica da carteira")


    portfolio = st.session_state.get("portfolio", {})
    if not portfolio:
        st.info("Sua carteira está vazia. Adicione ações na Página 1.")
        return

    # pega período dos filtros; se '(Todos)', cai no lock
    ano_base  = st.session_state.get("filtro_ano")
    tri_base  = st.session_state.get("filtro_tri")
    lock = st.session_state.get("_periodo_lock_portfolio", (None, None))
    if ano_base in (None, "Selecione"):
        ano_base = lock[0]
    if tri_base in (None, "Selecione"):
        tri_base = lock[1]

    if ano_base in (None, "Selecione") or tri_base in (None, "Selecione"):
        st.warning("Selecione **Ano (FY)** e **Trimestre (FQ)** na Página 1 para iniciar a simulação.")
        return

    try:
        ano_base, tri_base = int(ano_base), int(tri_base)
    except Exception:
        st.warning("Período base inválido. Ajuste os filtros na Página 1.")
        return

    # painel trimestral a partir da base COMPLETA
    df_qy = utils.build_qy_panel("src/base_para_simulador_indicadores_refatorado.csv")

    timeline, kpis, excluidos, details = utils.simulate_historical_quarterly(portfolio, df_qy, ano_base, tri_base)
    


    if excluidos:
        st.warning(f"Sem preço médio no trimestre-base ({ano_base}T{tri_base}) para: {', '.join(excluidos)}. Removidos da simulação.")

    if timeline.empty:
        st.info("Sem trimestres posteriores suficientes para simular com os dados históricos disponíveis.")
        return

    

    # ==== VISUALIZAÇÕES ====
    tl = utils._prep_timeline_quarterly(timeline)

    csv = tl[["Ano", "Trimestre", "Periodo", "Valor_Sem_Dividendos", "Dividendos_Trimestre", "Div_Acumulado", "Valor_Total", "Drawdown"]].to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "Baixar Resultado (.CSV)",
        data=csv,
        file_name=f"simulacao_trimestral_{ano_base}T{tri_base}.csv",
        mime="text/csv",
        key="btn_download_simulacao_quarterly"
    )


    # KPIs
    # ===== Retornos e risco (insights rápidos) =====
    tl_metrics, vol_anual, hit_ratio, max_dd = utils._prep_metrics_quarterly(timeline, kpis["valor_inicial"])

    # salva/atualiza histórico desta execução (com dedupe por run_key)
    utils.save_simulation_run(
        portfolio=portfolio,
        base_fy=ano_base, base_fq=tri_base,
        timeline=timeline,
        kpis=kpis,
        vol_anual=vol_anual, hit_ratio=hit_ratio, max_dd=max_dd
    )
    # ===== Resumo do período: início → fim =====
    st.subheader("Do início ao fim do período")

    valor_inicial = float(kpis.get("valor_inicial", 0.0))
    valor_final   = float(kpis.get("valor_final", 0.0))
    div_acum      = float(kpis.get("div_acum", 0.0))

    ganho_com_div  = (valor_final + div_acum) - valor_inicial
    ganho_sem_div  = (valor_final) - valor_inicial

    ret_com_div = (ganho_com_div / valor_inicial) if valor_inicial > 0 else np.nan
    ret_sem_div = (ganho_sem_div / valor_inicial) if valor_inicial > 0 else np.nan

    cA, cB, cC, cD, cE = st.columns(5)
    cA.metric("Ganho COM dividendos (R$)", f"R$ {(valor_final + div_acum):.2f}", delta = round(ganho_com_div,2))
    # cA.metric("Ganho COM dividendos (R$)", f"R$ {ganho_com_div:,.2f}")
    cB.metric("dividendos (R$)", f"R$ {div_acum:.2f}" )
    cC.metric("% COM dividendos", f"{ret_com_div*100:.2f}%" if np.isfinite(ret_com_div) else "n/d")
    # cD.metric("Ganho SEM dividendos (R$)", f"R$ {ganho_sem_div:,.2f}")
    cD.metric("Ganho SEM dividendos (R$)", f"R$ {(valor_final):.2f}", delta = round(ganho_sem_div,2))
    cE.metric("% SEM dividendos", f"{ret_sem_div*100:.2f}%" if np.isfinite(ret_sem_div) else "n/d")

    st.caption(
        f"Base: R$ {valor_inicial:,.2f} → Final (s/ div.): R$ {valor_final:,.2f} | Dividendos acum.: R$ {div_acum:,.2f}"
    )


    st.subheader("Evolução da carteira (trimestral)")
    col_line, col_bar = st.columns(2)
 
    with col_line:
        st.markdown("**Valor da carteira**")
        show_total = st.checkbox("Mostrar também Valor Total (Carteira + Dividendos acumulados)", value=True, key="chk_total_quarterly")
        if show_total:
            st.line_chart(
                tl.set_index("Periodo")[["Valor_Sem_Dividendos", "Valor_Total"]].round(2),
                height=300
            )
        else:
            st.line_chart(
                tl.set_index("Periodo")[["Valor_Sem_Dividendos"]].round(2),
                height=300
            )

    with col_bar:
        st.markdown("**Dividendos por trimestre**")
        st.bar_chart(
            tl.set_index("Periodo")[["Dividendos_Trimestre"]].round(2),
            height=300
        )

    
    st.caption("Notas: Preço trimestral = média de `Preco_Atual` no trimestre. Dividendos trimestrais = (Dividendos_QY + JCP_QY)/Ações, sem reinvestimento.")

    st.markdown("Desempenho por ticker")

    if details is None or details.empty:
        st.info("Sem detalhe por ticker disponível para este período.")
    else:
        det = details.copy()
        # cria coluna de período (fim do trimestre) para o eixo X temporal
        det["Periodo"] = pd.PeriodIndex(year=det["Ano"].astype(int),
                                        quarter=det["Trimestre"].astype(int),
                                        freq="Q").to_timestamp(how="end")

        tickers_disp = sorted(det["Ticker"].dropna().unique().tolist())
        sel = st.multiselect("Selecione os tickers para visualizar",
                            options=tickers_disp,
                            default=tickers_disp,
                            key="ms_det_tickers")
        det = det[det["Ticker"].isin(sel)]

        st.markdown("**Valor por ticker (R$)**")

        base = alt.Chart(det).encode(
            x=alt.X("Periodo:T", title=None),
            y=alt.Y("Valor_Ticker:Q", title="R$"),
            color=alt.Color("Ticker:N", legend=alt.Legend(orient="bottom", title=None)),
            tooltip=[
                alt.Tooltip("Ticker:N", title="Ticker"),
                alt.Tooltip("Periodo:T", title="Período"),
                alt.Tooltip("Valor_Ticker:Q", title="Valor (R$)", format=",.2f"),
            ],
        )

        # seleção de hover: trava por (Periodo, Ticker)
        hover = alt.selection_point(
            fields=["Periodo", "Ticker"],
            nearest=True,
            on="mouseover",
            empty="none",
        )

        line = base.mark_line().encode(
            opacity=alt.condition(hover, alt.value(1.0), alt.value(0.85))
        )

        points = base.mark_circle(size=60, filled=True).add_params(hover)

        # rótulo do valor exibido APENAS no ponto em foco
        labels = base.mark_text(
            align="left", dx=6, dy=-6, fontSize=12, fontWeight="bold"
        ).encode(
            text=alt.Text("Valor_Ticker:Q", format=",.2f")
        ).transform_filter(hover)

        # linha vertical no período focado
        rule = alt.Chart(det).mark_rule(color="#888", strokeDash=[4, 4]).encode(
            x="Periodo:T"
        ).transform_filter(hover)

        chart_val = (line + points + labels + rule).properties(height=300).interactive()
        st.altair_chart(chart_val, use_container_width=True)

        # (Opcional) Retorno trimestral por ticker vs. trimestre anterior
        det = det.sort_values(["Ticker", "Ano", "Trimestre"]).copy()
        det["Ret_Ticker_Trimestre"] = np.nan
        for tck in det["Ticker"].unique():
            g = det[det["Ticker"] == tck].copy()
            v = g["Valor_Ticker"].astype(float)
            ret = ((v + g["Dividendos_Ticker"].astype(float)) / v.shift(1)) - 1.0
            det.loc[g.index, "Ret_Ticker_Trimestre"] = ret.values

        st.markdown("**Retorno por ticker (trimestre)**")
        det_ret = det.dropna(subset=["Ret_Ticker_Trimestre"]).copy()
        chart_ret = alt.Chart(det_ret).mark_bar().encode(
            x="Periodo:T",
            y=alt.Y("Ret_Ticker_Trimestre:Q", axis=alt.Axis(format="%"), title="Retorno"),
            color=alt.Color("Ticker:N", legend=None),
            tooltip=[alt.Tooltip("Ticker:N"),
                    alt.Tooltip("Periodo:T"),
                    alt.Tooltip("Ret_Ticker_Trimestre:Q", format=".2%")]
        ).properties(height=220)
        st.altair_chart(chart_ret, use_container_width=True)

    # ===== Ranking de contribuição por ticker =====
    st.subheader("composição do resuTickers que mais renderam no período")

    # Mapas auxiliares (quantidade e preço-base)
    qty_map = {str(k).strip().upper(): int(v.get("quantidade", 0)) for k, v in portfolio.items()}
    base_df = df_qy[(df_qy["FY"] == ano_base) & (df_qy["FQ"] == tri_base)][["Ticker", "Preco_QY"]].dropna()
    base_prices = dict(zip(base_df["Ticker"].astype(str).str.upper(), base_df["Preco_QY"]))

    rank_rows, excl_tickers = [], []

    # período final (última linha do timeline)
    end_ano = int(tl_metrics["Ano"].iloc[-1])
    end_tri = int(tl_metrics["Trimestre"].iloc[-1])

    if details is None or details.empty:
        st.info("Sem detalhe por ticker disponível; não é possível montar o ranking.")
    else:
        det_all = details.copy()
        det_all["Ticker"] = det_all["Ticker"].astype(str).str.upper()

        for tck, qtd in qty_map.items():
            preco_base = base_prices.get(tck, np.nan)
            if not np.isfinite(preco_base) or qtd <= 0:
                excl_tickers.append(tck)
                continue

            valor_inicial = float(qtd * preco_base)

            # pega o último valor disponível até o fim do período; se faltar no fim, usa o último válido
            det_t = det_all[(det_all["Ticker"] == tck) &
                            ((det_all["Ano"] < end_ano) | ((det_all["Ano"] == end_ano) & (det_all["Trimestre"] <= end_tri)))]
            if det_t.empty:
                excl_tickers.append(tck)
                continue

            det_t = det_t.sort_values(["Ano", "Trimestre"])
            valor_final = float(det_t["Valor_Ticker"].dropna().iloc[-1]) if det_t["Valor_Ticker"].notna().any() else np.nan
            div_periodo = float(det_t["Dividendos_Ticker"].fillna(0).sum())

            if not np.isfinite(valor_final):
                excl_tickers.append(tck)
                continue

            ganho_total = valor_final + div_periodo - valor_inicial
            ret_pct = ganho_total / valor_inicial if valor_inicial > 0 else np.nan

            rank_rows.append({
                "Ticker": tck,
                "Qtd": int(qtd),
                "Preço base (QY)": float(preco_base),
                "Valor inicial (R$)": valor_inicial,
                "Valor final (R$)": valor_final,
                "Dividendos (R$)": div_periodo,
                "Ganho total (R$)": ganho_total,
                "Retorno (%)": ret_pct * 100 if np.isfinite(ret_pct) else np.nan,
            })

        if rank_rows:
            rank_df = pd.DataFrame(rank_rows).sort_values("Ganho total (R$)", ascending=False).reset_index(drop=True)

            # formatação leve
            fmt_cols = ["Valor inicial (R$)", "Valor final (R$)", "Dividendos (R$)", "Ganho total (R$)"]
            for c in fmt_cols:
                rank_df[c] = rank_df[c].round(2)
            if rank_df["Retorno (%)"].notna().any():
                rank_df["Retorno (%)"] = rank_df["Retorno (%)"].round(2)

            st.dataframe(rank_df, use_container_width=True, hide_index=True)

            # gráfico rápido: top 10 por ganho em R$
            topN = min(10, len(rank_df))
            g = (
                rank_df.nlargest(topN, "Ganho total (R$)")[["Ticker", "Ganho total (R$)"]]
                    .copy()
            )
            g["Ganho total (R$)"] = pd.to_numeric(g["Ganho total (R$)"], errors="coerce")
            g = g.dropna(subset=["Ganho total (R$)"])

            st.markdown(f"**Top {topN} por ganho (R$)**")

            # seleção (opcional): clicar na legenda destaca a barra
            sel = alt.selection_point(fields=["Ticker"], bind="legend")

            base = alt.Chart(g).encode(
                x=alt.X("Ticker:N", title=None, sort="-y"),
                y=alt.Y("Ganho total (R$):Q",
                        title="R$",
                        axis=alt.Axis(format=",.2f", grid=True)),
                color=alt.condition(sel, alt.value("#4C78A8"), alt.value("#A3C4DC")),
                tooltip=[
                    alt.Tooltip("Ticker:N"),
                    alt.Tooltip("Ganho total (R$):Q", format=",.2f")
                ],
            )

            # barras
            bars = base.mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).add_params(sel)

            # rótulos SEM hover (sempre visíveis)
            # usamos uma transformação para prefixar "R$ " no texto
            labels = (
                base.transform_calculate(label="format(datum['Ganho total (R$)'], ',.2f')")
                    .mark_text(
                        align="center",
                        baseline="bottom",
                        dy=-4,            # desloca para cima da barra
                        fontSize=12,
                        fontWeight="bold"
                    )
                    .encode(text="label:N")
            )

            # linha no zero (caso haja negativos)
            rule0 = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(strokeDash=[4,4], color="#666").encode(y="y:Q")

            chart = (bars + labels + rule0).properties(height=340).configure_axis(labelFontSize=12, titleFontSize=12)

            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Nenhum ticker com dados suficientes para ranquear.")

        if excl_tickers:
            st.caption(f"⚠️ Sem dados suficientes no período para: {', '.join(sorted(set(excl_tickers)))}.")


    # === Waterfall: Início → contribuições por ticker (Δ preço) → Dividendos → Fim ===
    st.markdown("Decomposição do resultado (waterfall)")

    try:
        if details is None or details.empty:
            st.info("Sem detalhe por ticker para montar a decomposição.")
        else:
            # Mapas de quantidade e preço-base (mesmo conceito do ranking)
            qty_map = {str(k).strip().upper(): int(v.get("quantidade", 0)) for k, v in portfolio.items()}
            base_df = df_qy[(df_qy["FY"] == ano_base) & (df_qy["FQ"] == tri_base)][["Ticker", "Preco_QY"]].dropna()
            base_prices = dict(zip(base_df["Ticker"].astype(str).str.upper(), base_df["Preco_QY"]))

            # período final (último trimestre simulado)
            end_ano = int(tl["Ano"].iloc[-1])
            end_tri = int(tl["Trimestre"].iloc[-1])

            det_all = details.copy()
            det_all["Ticker"] = det_all["Ticker"].astype(str).str.upper()

            # totais de início/fim e contribuições
            total_inicio = 0.0
            total_div    = 0.0
            contribs = []  # lista de {"label": tck, "value": delta_preco}

            for tck, qtd in qty_map.items():
                preco_base = base_prices.get(tck, np.nan)
                if not np.isfinite(preco_base) or qtd <= 0:
                    continue

                valor_inicial = float(qtd * preco_base)
                total_inicio += valor_inicial

                det_t = det_all[(det_all["Ticker"] == tck) &
                                ((det_all["Ano"] < end_ano) | ((det_all["Ano"] == end_ano) & (det_all["Trimestre"] <= end_tri)))]
                if det_t.empty:
                    continue

                det_t = det_t.sort_values(["Ano", "Trimestre"])
                valor_final = float(det_t["Valor_Ticker"].dropna().iloc[-1]) if det_t["Valor_Ticker"].notna().any() else np.nan
                div_periodo = float(det_t["Dividendos_Ticker"].fillna(0).sum())
                total_div += div_periodo

                if np.isfinite(valor_final):
                    delta_preco = valor_final - valor_inicial
                    contribs.append({"label": tck, "value": float(delta_preco)})

            total_fim_com_div = float((kpis.get("valor_final", 0.0) or 0.0) + (kpis.get("div_acum", 0.0) or 0.0))

            # constrói tabela waterfall com y/y2 prontos
            wf_rows = []
            cum = 0.0

            # Início (barra total)
            wf_rows.append({"label": "Início", "y": 0.0, "y2": total_inicio, "tipo": "Inicio"})

            # Δ preço por ticker (ordene por contribuição desc.)
            contribs = sorted(contribs, key=lambda d: d["value"], reverse=True)
            for c in contribs:
                start = cum + total_inicio
                end = start + c["value"]
                wf_rows.append({
                    "label": c["label"],
                    "y": start,
                    "y2": end,
                    "tipo": "Delta+" if c["value"] >= 0 else "Delta-"
                })
                cum += c["value"]

            # Dividendos (um bloco único)
            start = cum + total_inicio
            end = start + total_div
            wf_rows.append({"label": "Dividendos", "y": start, "y2": end, "tipo": "Dividendos"})
            cum += total_div

            # Fim (com dividendos)
            wf_rows.append({"label": "Fim (c/ div.)", "y": 0.0, "y2": total_fim_com_div, "tipo": "Fim"})

            wf = pd.DataFrame(wf_rows)
            if not wf.empty:
                scale = alt.Scale(domain=["Inicio", "Delta+", "Delta-", "Dividendos", "Fim"],
                                range=["#4c78a8", "#8ec07c", "#e76f51", "#f4a261", "#7b9acc"])

                chart_wf = (
                    alt.Chart(wf)
                    .mark_bar()
                    .encode(
                        x=alt.X("label:N", sort=None, title=None),
                        y=alt.Y("y:Q", title="R$"),
                        y2="y2:Q",
                        color=alt.Color("tipo:N", scale=scale, legend=alt.Legend(orient="bottom", title=None)),
                        tooltip=[
                            alt.Tooltip("label:N", title="Etapa"),
                            alt.Tooltip("y2:Q", title="Nível", format=",.2f"),
                        ],
                    )
                    .properties(height=300)
                )
                st.altair_chart(chart_wf, use_container_width=True)
            else:
                st.info("Sem contribuições suficientes para o waterfall.")
    except Exception as _e:
        st.info("Não foi possível montar o gráfico de decomposição.")


    # === Scatter risco × retorno por ticker ===
    st.markdown("**Risco × Retorno por ticker (período simulado)**")

    try:
        if details is None or details.empty:
            st.info("Sem detalhe por ticker para estimar risco/retorno.")
        else:
            det = details.copy().sort_values(["Ticker", "Ano", "Trimestre"])
            # retorno trimestral do ticker: (preço*qtd + dividendos) / (preço*qtd anterior) - 1
            det["ret_ticker"] = det.groupby("Ticker").apply(
                lambda g: ((g["Valor_Ticker"].astype(float) + g["Dividendos_Ticker"].fillna(0.0).astype(float))
                        / g["Valor_Ticker"].astype(float).shift(1) - 1.0)
            ).reset_index(level=0, drop=True)

            agg = det.groupby("Ticker").agg(
                ret_total_ticker=("ret_ticker", lambda s: (np.prod(1 + s.dropna()) - 1) if s.dropna().size > 0 else np.nan),
                vol_ticker=("ret_ticker", lambda s: (s.dropna().std(ddof=0) * np.sqrt(4)) if s.dropna().size > 1 else np.nan),
                valor_final=("Valor_Ticker", "last")
            ).reset_index()

            # peso final na carteira (normaliza pelos que têm valor_final)
            tot_final = agg["valor_final"].sum()
            agg["peso_final"] = agg["valor_final"] / tot_final if tot_final > 0 else np.nan

            data_sc = agg.dropna(subset=["ret_total_ticker", "vol_ticker"]).copy()
            if data_sc.empty:
                st.info("Sem dados suficientes para o scatter.")
            else:
                chart_sc = (
                    alt.Chart(data_sc)
                    .mark_circle()
                    .encode(
                        x=alt.X("vol_ticker:Q", title="Vol anualizada (ticker)"),
                        y=alt.Y("ret_total_ticker:Q", axis=alt.Axis(format="%"), title="Retorno total do período"),
                        size=alt.Size("peso_final:Q", title="Peso final", legend=None),
                        color=alt.Color("Ticker:N", legend=alt.Legend(orient="bottom", title=None)),
                        tooltip=[
                            alt.Tooltip("Ticker:N"),
                            alt.Tooltip("ret_total_ticker:Q", title="Retorno", format=".2%"),
                            alt.Tooltip("vol_ticker:Q", title="Vol anualizada", format=".2f"),
                            alt.Tooltip("peso_final:Q", title="Peso final", format=".2%"),
                        ],
                    )
                    .properties(height=320)
                )
                st.altair_chart(chart_sc, use_container_width=True)

        st.caption("Notas: Vol anualizada = Mede risco como desvio-padrão dos retornos.")
        st.caption("Leitura: maior vol = mais instável/arriscado. Vol não diz direção (ganho/perda), só o quanto oscila.")

    except Exception as _e:
        st.info("Não foi possível montar o scatter de risco × retorno.")

    


    st.markdown("Tabela de resultados (detalhada)")
    tbl = tl_metrics.copy()
    tbl["Div_Acumulado"] = tbl["Dividendos_Trimestre"].fillna(0).cumsum()
    tbl["Valor_Total"] = tbl["Valor_Sem_Dividendos"].fillna(0) + tbl["Div_Acumulado"]
    tbl["Ret_Acumulado"] = (tbl["Valor_Total"] / float(kpis["valor_inicial"])) - 1.0

    fmt = tbl.copy()
    fmt["Retorno_Trimestre"] = (fmt["Retorno_Trimestre"] * 100).round(2)
    fmt["Drawdown"] = (fmt["Drawdown"] * 100).round(2)
    fmt["Ret_Acumulado"] = (fmt["Ret_Acumulado"] * 100).round(2)
    fmt["Valor_Sem_Dividendos"] = fmt["Valor_Sem_Dividendos"].round(2)
    fmt["Valor_Total"] = fmt["Valor_Total"].round(2)
    fmt["Dividendos_Trimestre"] = fmt["Dividendos_Trimestre"].round(2)
    fmt["Div_Acumulado"] = fmt["Div_Acumulado"].round(2)

    fmt = fmt[["Ano", "Trimestre",
            "Valor_Sem_Dividendos", "Dividendos_Trimestre", "Div_Acumulado",
            "Retorno_Trimestre", "Ret_Acumulado", "Drawdown"]].rename(columns={
                "Valor_Sem_Dividendos": "Valor Carteira (R$)",
                "Dividendos_Trimestre": "Dividendos Trim. (R$)",
                "Div_Acumulado": "Dividendos Acum. (R$)",
                "Retorno_Trimestre": "Retorno Trim. (%)",
                "Ret_Acumulado": "Ret. Acum. (%)",
                "Drawdown": "Drawdown (%)",
            })

    st.dataframe(fmt, hide_index=True, use_container_width=True)


