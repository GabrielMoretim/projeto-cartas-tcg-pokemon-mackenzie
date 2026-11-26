"""Dashboard Streamlit: cinco perguntas em reais (chave para dólar) + desafio da carteira."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from tcg import analytics, carteira, config, gold  # noqa: E402
from tcg.store import get_store  # noqa: E402

st.set_page_config(page_title="Cartas Pokémon como ativo", layout="wide")
GID = config.group_id()
SIGLA = config.COLECOES[GID][1]


@st.cache_data(show_spinner="Lendo o gold...")
def dados():
    con = gold.abrir_gold()
    try:
        return gold.carregar_fato(con), gold.carregar_cambio(con)
    finally:
        con.close()


@st.cache_data(show_spinner="Lendo as carteiras da turma...")
def carteiras_turma():
    try:
        store = get_store()
        import duckdb

        con = duckdb.connect()
        store.setup_duckdb(con)
        df = con.execute(f"SELECT * FROM read_parquet('{store.uri('gold_turma/carteira/*/carteira.parquet')}', "
                         "union_by_name=true, hive_partitioning=false)").df()
        df["data"] = pd.to_datetime(df["data"])
        return df
    except Exception:
        return None


def pct(s):  # fração -> pontos percentuais, para as colunas formatadas
    return s * 100


img = st.column_config.ImageColumn("Carta", width="small")
lnk = st.column_config.LinkColumn("TCGplayer", display_text="abrir")

with st.sidebar:
    st.title("Cartas como ativo")
    moeda = st.radio("Moeda", ["Reais (BRL)", "Dólar (USD)"])
    brl = moeda.startswith("Reais")
    taxa = st.radio("Taxa de venda (carteira)", [config.TAXA_VENDA, 0.0],
                    format_func=lambda x: f"{x:.0%}" if x else "sem taxa")
    if st.button("Reconstruir gold a partir do lake"):
        gold.build_gold(get_store(), GID, exportar=False)
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Coleção: {config.COLECOES[GID][0]} ({SIGLA})")

try:
    fato, cambio = dados()
except Exception as e:
    st.error(f"Gold não encontrado ({e}). Rode `python -m tcg rebuild` primeiro.")
    st.stop()

dmin, dmax = fato[fato.group_id == GID].data.min(), fato[fato.group_id == GID].data.max()
st.caption(f"Série da sua coleção: {dmin:%d/%m/%Y} a {dmax:%d/%m/%Y} · {fato.group_id.nunique()} coleções na turma · "
           "valores em " + ("R$ pela PTAX de venda (última cotação conhecida)" if brl else "US$"))
if (dmax - dmin).days < 2:
    st.warning("Poucos dias de histórico: rankings e índices ainda não dizem nada.")

t1, t2, t3, t4, t5, t6, t7 = st.tabs(["1 · Valorização", "2 · Selado × cartas", "3 · Coleções", "4 · Concentração",
                                      "5 · Risco × retorno", "Desafio da carteira", "Limites do dado"])

with t1:
    st.subheader("Quais cartas mais valorizaram e desvalorizaram desde o início da coleta?")
    st.caption("Só cartas acima de US$ 1 no 1º dia (filtro sempre em dólar). Variação em R$ = carta + câmbio + cruzado.")
    top, bottom = analytics.pergunta1(fato, GID, brl)
    cols = ["image_url", "nome", "raridade", "acabamento", "preco_ini_brl", "preco_fim_brl",
            "variacao_brl", "efeito_carta", "efeito_cambio", "efeito_cruzado", "url"]
    cfg = {"image_url": img, "url": lnk, **{c: st.column_config.NumberColumn(format="%.1f%%") for c in
           ["variacao_brl", "efeito_carta", "efeito_cambio", "efeito_cruzado"]},
           **{c: st.column_config.NumberColumn(format="R$ %.2f") for c in ["preco_ini_brl", "preco_fim_brl"]}}
    for titulo, t in (("Mais valorizaram", top), ("Mais desvalorizaram", bottom)):
        st.markdown(f"**{titulo}**")
        v = t[cols].copy()
        for c in ["variacao_brl", "efeito_carta", "efeito_cambio", "efeito_cruzado"]:
            v[c] = pct(v[c])
        st.dataframe(v, column_config=cfg, hide_index=True, use_container_width=True, row_height=80)

with t2:
    st.subheader("O selado guardou valor melhor que as cartas avulsas?")
    d = analytics.pergunta2(fato, GID, brl)
    if d.shape[1] > 1:
        st.plotly_chart(px.line(d.melt("data", var_name="Índice", value_name="Base 100"),
                                x="data", y="Base 100", color="Índice"), use_container_width=True)
    else:
        st.info("Sem dados suficientes de selados ou de cartas de raridade alta (revise RARIDADES_ALTAS).")

with t3:
    st.subheader("Qual coleção da turma valorizou mais no período?")
    v, ptax = analytics.pergunta3(fato, brl)
    fig = px.line(v, x="data", y="indice", color="sigla")
    fig.update_traces(line_width=5, selector=dict(name=SIGLA))
    if brl:
        fig.add_trace(go.Scatter(x=ptax.data, y=ptax.indice, name="PTAX", line=dict(color="gray", dash="dot")))
    fig.update_yaxes(title="Índice (base 100 no 1º dia em comum)")
    st.plotly_chart(fig, use_container_width=True)

with t4:
    st.subheader("Onde está concentrado o valor de cada coleção?")
    share, n80 = analytics.pergunta4(fato, brl)
    a, b = st.columns([3, 1])
    a.plotly_chart(px.bar(share, x="sigla", y="participacao", color="raridade").update_yaxes(tickformat=".0%"),
                   use_container_width=True)
    b.markdown("**Cartas que somam 80% do valor**")
    b.dataframe(n80, hide_index=True)

with t5:
    st.subheader("Quais cartas deram mais retorno para o risco?")
    r = analytics.pergunta5(fato, brl)
    if r.empty:
        st.info("Precisa de pelo menos 3 dias na janela comum da turma.")
    else:
        st.plotly_chart(px.scatter(r, x="volatilidade", y="retorno", color="sigla", hover_name="nome",
                                   hover_data=["raridade"]).update_layout(xaxis_tickformat=".1%",
                                                                           yaxis_tickformat=".0%"),
                        use_container_width=True)
        sel = st.selectbox("Ver carta", r.sort_values("retorno", ascending=False).nome.unique())
        linha = r[r.nome == sel].iloc[0]
        c1, c2 = st.columns([1, 3])
        c1.image(linha.image_url, width=200)
        c2.markdown(f"**{sel}** · {linha.sigla} · retorno {linha.retorno:.1%} · vol. diária {linha.volatilidade:.2%}  \n"
                    f"[abrir no TCGplayer]({linha.url})")

with t6:
    st.subheader("R$ 1.000 em cartas e selados × dólar × CDI")
    own = fato[fato.group_id == GID]
    try:
        cart, comp = carteira.calcular(own, cambio, GID, taxa_venda=config.TAXA_VENDA)
    except Exception as e:
        st.error(f"Não foi possível calcular a carteira: {e}")
        st.stop()
    c = cart[cart.taxa_venda == taxa]
    st.plotly_chart(px.line(c, x="data", y="valor_brl", color="carteira").update_yaxes(title="Valor de liquidação (R$)"),
                    use_container_width=True)
    m = carteira.metricas(cart, taxa)
    for col in ("retorno_acumulado", "perda_maxima", "excesso_sobre_cdi"):
        m[col] = m[col] * 100
    st.dataframe(m, hide_index=True, column_config={
        c_: st.column_config.NumberColumn(format="%.2f%%") for c_ in ("retorno_acumulado", "perda_maxima", "excesso_sobre_cdi")})
    if (c.groupby("carteira").preco_carregado.sum() > 0).any():
        st.caption("Dias com preço carregado = dias em que algum item usou o último preço observado.")
    with st.expander("Composição das carteiras no 1º dia"):
        for nome, info in comp.items():
            st.markdown(f"**{nome}** — {info['regra']} · caixa inicial R$ {info['caixa_inicial']:.2f}")
            st.dataframe(pd.DataFrame(info["itens"]), hide_index=True)
    st.markdown("### Placar da turma")
    turma = carteiras_turma()
    if turma is None or turma.empty:
        st.info("Ainda não há carteiras da turma em gold_turma/carteira/.")
    else:
        p = analytics.placar(turma, taxa)
        k1, k2, k3 = st.columns(3)
        k1.metric("Coleções em que o selado ganhou do CDI", f"{p['selado_ganhou_do_cdi']} de {p['colecoes']}")
        k2.metric("Coleções em que a cesta ganhou do dólar", f"{p['cesta_ganhou_do_dolar']} de {p['colecoes']}")
        k3.metric("Menor perda máxima (coleção, carteira)", str(p["menor_perda_maxima"]))
        st.dataframe((p["retornos"] * 100).round(2).reset_index())

with t7:
    st.markdown("""
- O `market_price` do TCGplayer vem de vendas recentes nos EUA, em dólar, sem separar a condição da carta;
  não inclui frete, taxas nem o preço praticado no Brasil.
- A PTAX é taxa de referência. Cartão internacional paga outra cotação (spread + IOF).
- O CDI entra sem imposto de renda e sem taxas de corretora.
- A série tem poucas semanas: descreve o que aconteceu, **não prevê** nem recomenda compra.
- Dias sem coleta são lacunas explicadas no README; nada é inventado.
""")
