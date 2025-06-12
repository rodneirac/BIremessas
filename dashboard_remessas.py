import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
from io import BytesIO
import locale

# --- CONFIGURAÇÃO DA PÁGINA ---
# ESTA LINHA DEVE SER O PRIMEIRO COMANDO STREAMLIT DO SCRIPT.
st.set_page_config(layout="wide")

# --- CONFIGURAÇÃO DA LOCALIDADE PARA FORMATAÇÃO PT-BR ---
# Tenta definir a localidade. Se falhar, exibe um aviso.
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    st.warning("Localidade 'pt_BR.UTF-8' não encontrada. A formatação de números pode não ser a ideal. Para corrigir em deploy, adicione 'locales-all' ao seu arquivo packages.txt.")

# --- URLs E CONSTANTES DO GITHUB ---
ARQUIVO_DADOS_REMESSAS = "DADOSREMESSA.XLSX"
OWNER = "rodneirac"
REPO = "BIremessas"

URL_DADOS_REMESSAS = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/{ARQUIVO_DADOS_REMESSAS}"
LOGO_URL = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/logo.png"

@st.cache_data(ttl=3600)
def get_latest_update_info(owner, repo, file_path):
    """Busca a data do último commit de um arquivo específico no GitHub."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits?path={file_path}&page=1&per_page=1"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        commit_data = response.json()
        if commit_data:
            date_str = commit_data[0]['commit']['committer']['date']
            local_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return f"**{local_date.astimezone().strftime('%d/%m/%Y às %H:%M')}**"
        return "Data não disponível."
    except requests.exceptions.RequestException as e:
        st.warning(f"Não foi possível buscar a data de atualização: {e}")
        return "Erro ao obter data."

@st.cache_data
def load_data(url):
    """Carrega e processa os dados de uma URL de um arquivo Excel."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_excel(BytesIO(response.content), engine="openpyxl", skiprows=3)
        
        colunas_esperadas = ["Base", "Ignorar", "Descricao", "Data Ocorrencia", "Valor", "Cliente", "Cond Pagto SAP", "Dia Corte Fat"]
        if len(df.columns) == len(colunas_esperadas):
            df.columns = colunas_esperadas
            df = df.drop(columns=["Ignorar"])
        else:
            st.error("O número de colunas no arquivo Excel não corresponde ao esperado.")
            return pd.DataFrame()
        
        df["Data Ocorrencia"] = pd.to_datetime(df["Data Ocorrencia"], errors="coerce")
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
        df.dropna(subset=["Data Ocorrencia", "Valor"], inplace=True)
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
    meses = sorted(df["Mês"].dropna().unique(), reverse=True)

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

    total_remessas = len(df_filtrado)
    valor_total = df_filtrado["Valor"].sum()
    valor_medio = df_filtrado["Valor"].mean() if total_remessas > 0 else 0

    st.markdown("### Indicadores Gerais")
    col1, col2, col3 = st.columns(3)
    
    col1.metric("Qtde. Remessas", f"{total_remessas:n}")
    col2.metric("Valor Total (R$)", locale.format_string('%.2f', valor_total, grouping=True))
    col3.metric("Valor Médio (R$)", locale.format_string('%.2f', valor_medio, grouping=True))

    st.markdown("---")
    st.subheader("Evolução de Valores por Mês")

    agrupado = df_filtrado.groupby("Mês").agg({"Valor": "sum"}).reset_index().sort_values("Mês")
    fig = px.bar(agrupado, x="Mês", y="Valor", text_auto='.2s',
                 title="Valor Total por Mês", labels={"Valor": "Valor (R$)", "Mês": "Mês de Referência"})
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("Ver dados detalhados"):
        st.dataframe(df_filtrado)

else:
    st.warning("Não há dados disponíveis para exibição ou ocorreu um erro no carregamento.")
