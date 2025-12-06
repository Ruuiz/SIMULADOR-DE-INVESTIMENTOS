import streamlit as st
import controller.utils as utils


# =======================
# Sidebar (carteira + simular)
# =======================
def render_sidebar():
    st.sidebar.title("Carteira")

    # mostra aviso de reset (se existir), depois limpa para não repetir
    msg = st.session_state.pop("_portfolio_reset_message", None)
    if msg:
        st.sidebar.info(msg)

    carteira = st.session_state.get("portfolio", {})

    if carteira:
        total_geral = 0.0
        for ticker, dados in carteira.items():
            preco = float(dados.get("preco_unitario", 0.0))
            quantidade = int(dados.get("quantidade", 0))
            total = quantidade * preco
            total_geral += total

            with st.sidebar.expander(f"📈 {ticker} — Qtd: {quantidade} — Total: R$ {total:.2f}"):
                nova_qtd = st.number_input(
                    "Quantidade", min_value=1, step=1,
                    value=quantidade, key=f"edit_qtd_{ticker}"
                )
                col1, col2 = st.columns([2, 2])
                if col1.button("💾 Atualizar", key=f"btn_atualiza_{ticker}"):
                    st.session_state.portfolio[ticker]["quantidade"] = int(nova_qtd)
                    st.rerun()
                if col2.button("Retirar ❌", key=f"del_{ticker}"):
                    del st.session_state.portfolio[ticker]
                    st.rerun()

                st.markdown(f"**Total desta ação:** {int(nova_qtd)} × R$ {preco:.2f} = R$ {int(nova_qtd) * preco:.2f}")

        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**💼 Total da carteira: R$ {total_geral:,.2f}**")

        if st.sidebar.button("Simular carteira ➔"):
            utils.goto("simulacao")

    else:
        st.sidebar.info("Adicione ações à sua carteira.")

    if st.sidebar.button("Histórico de simulações", key="btn_hist_sim"):
            utils.goto("historico")
