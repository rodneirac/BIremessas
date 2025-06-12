
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
from io import BytesIO

# --- URLs E CONSTANTES DO GITHUB ---
ARQUIVO_DADOS_REMESSAS = "DADOSREMESSA.XLSX"
OWNER = "rodneirac"
REPO = "BIremessas"

URL_DADOS_REMESSAS = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/{ARQUIVO_DADOS_REMESSAS}"
LOGO_URL = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/logo.png"

@st.cache_data(ttl=3600)
def get_latest_update_info(owner, repo, file_path):
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits?path={file_path}&page=1&per_page=1"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        commit_data = response.json()
        if commit_data:
            date_str = commit_data[0]['commit']['committer']['date']
            local_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return f"**{local_date.astimezone().strftime('%d/%m/%Y às %H:%M')}**"
    except:
        return "Erro ao obter data."
    return "Data não disponível."

@st.cache_data
def load_data(url):
    try:
        response = requests.get(url)
        df = pd.read_excel(BytesIO(response.content), engine="openpyxl", skiprows=3)
        df.columns = ["Base", "Ignorar", "Descricao", "Data Ocorrencia", "Valor", "Cliente", "Cond Pagto SAP", "Dia Corte Fat"]
        df = df.drop(columns=["Ignorar"])
        df["Data Ocorrencia"] = pd.to_datetime(df["Data Ocorrencia"], errors="coerce")
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
        df["Mês"] = df["Data Ocorrencia"].dt.to_period("M").astype(str)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return pd.DataFrame()

# --- INTERFACE ---
st.image(LOGO_URL, width=200)
st.title("Dashboard Remessas a Faturar")
st.caption(f"Dados atualizados em: {get_latest_update_info(OWNER, REPO, ARQUIVO_DADOS_REMESSAS)}")

# --- DADOS ---
df = load_data(URL_DADOS_REMESSAS)

if not df.empty:
    st.sidebar.header("Filtros")
    bases = sorted(df["Base"].dropna().unique())
    descricoes = sorted(df["Descricao"].dropna().unique())
    clientes = sorted(df["Cliente"].dropna().unique())
    meses = sorted(df["Mês"].dropna().unique())

    base_sel = st.sidebar.multiselect("Filtrar por Base", bases, default=bases)
    descricao_sel = st.sidebar.multiselect("Filtrar por Descrição", descricoes, default=descricoes)
    cliente_sel = st.sidebar.multiselect("Filtrar por Cliente", clientes, default=clientes)
    mes_sel = st.sidebar.multiselect("Filtrar por Mês", meses, default=meses)

    df_filtrado = df[
        df["Base"].isin(base_sel) &
        df["Descricao"].isin(descricao_sel) &
        df["Cliente"].isin(cliente_sel) &
        df["Mês"].isin(mes_sel)
    ]

    # KPIs
    total_remessas = len(df_filtrado)
    valor_total = df_filtrado["Valor"].sum()
    valor_medio = df_filtrado["Valor"].mean()

    st.markdown("### Indicadores Gerais")
    col1, col2, col3 = st.columns(3)
    col1.metric("Qtde. Remessas", f"{total_remessas:,}".replace(",", "."))
    col2.metric("Valor Total (R$)", f"{valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col3.metric("Valor Médio (R$)", f"{valor_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown("---")
    st.subheader("Evolução de Valores por Mês")

    agrupado = df_filtrado.groupby("Mês").agg({"Valor": "sum"}).reset_index()
    fig = px.bar(agrupado, x="Mês", y="Valor", text_auto=True,
                 title="Valor Total por Mês", labels={"Valor": "Valor (R$)"})
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Não há dados disponíveis para exibição.")
