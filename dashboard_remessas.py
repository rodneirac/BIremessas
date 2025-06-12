# 1. IMPORTS
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
from io import BytesIO
import locale

# 2. CONFIGURAÇÕES INICIAIS DA PÁGINA E LOCALIDADE
st.set_page_config(layout="wide")

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    st.warning("Localidade 'pt_BR.UTF-8' não encontrada. A formatação de números pode não ser a ideal.")

# 3. CONSTANTES E FUNÇÕES
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
        return "Data não disponível."
    except requests.exceptions.RequestException:
        return "Erro ao obter data."

@st.cache_data
def load_data(url):
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

# 4. LÓGICA PRINCIPAL E CONSTRUÇÃO DA INTERFACE
st.image(LOGO_URL, width=200)
st.title("Dashboard Remessas a Faturar")
st.caption(f"Dados atualizados em: {get_latest_update_info(OWNER, REPO, ARQUIVO_DADOS_REMESSAS)}")

df = load_data(URL_DADOS_REMESSAS)

if not df.empty:
    st.sidebar.header("Filtros")

    bases = sorted(df["Base"].dropna().unique())
    if 'base_selection' not in st.session_state:
        st.session_state['base_selection'] = []

    with st.sidebar.expander("✔️ Filtrar por Base", expanded=True):
        col1, col2 = st.columns(2)
        if col1.button("Selecionar Todas", key='select_all_bases', use_container_width=True):
            st.session_state['base_selection'] = bases
            st.rerun()
        if col2.button("Limpar Todas", key='clear_all_bases', use_container_width=True):
            st.session_state['base_selection'] = []
            st.rerun()
        base_sel = st.multiselect(
            "Selecione as Bases", options=bases, default=st.session_state['base_selection'],
            label_visibility="collapsed"
        )
        st.session_state['base_selection'] = base_sel

    descricoes = sorted(df["Descricao"].dropna().unique())
    if 'desc_selection' not in st.session_state:
        st.session_state['desc_selection'] = []

    with st.sidebar.expander("✔️ Filtrar por Descrição", expanded=True):
        col3, col4 = st.columns(2)
        if col3.button("Selecionar Todas", key='select_all_desc', use_container_width=True):
            st.session_state['desc_selection'] = descricoes
            st.rerun()
        if col4.button("Limpar Todas", key='clear_all_desc', use_container_width=True):
            st.session_state['desc_selection'] = []
            st.rerun()
        descricao_sel = st.multiselect(
            "Selecione as Descrições", options=descricoes, default=st.session_state['desc_selection'],
            label_visibility="collapsed"
        )
        st.session_state['desc_selection'] = descricao_sel

    df_filtrado = df.copy()
    if st.session_state['base_selection']:
        df_filtrado = df_filtrado[df_filtrado['Base'].isin(st.session_state['base_selection'])]
    if st.session_state['desc_selection']:
        df_filtrado = df_filtrado[df_filtrado['Descricao'].isin(st.session_state['desc_selection'])]

    total_remessas = len(df_filtrado)
    valor_total = df_filtrado["Valor"].sum()
    valor_medio = df_filtrado["Valor"].mean() if total_remessas > 0 else 0

    st.markdown("### Indicadores Gerais")
    kpi_cols = st.columns(3)
    kpi_cols[0].metric("Qtde. Remessas", f"{total_remessas:n}")
    kpi_cols[1].metric("Valor Total (R$)", locale.format_string('%.2f', valor_total, grouping=True))
    kpi_cols[2].metric("Valor Médio (R$)", locale.format_string('%.2f', valor_medio, grouping=True))

    st.markdown("---")
    
    # --- NOVA SEÇÃO: GRÁFICOS LADO A LADO ---
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Evolução de Valores por Mês")
        agrupado_mes = df_filtrado.groupby("Mês").agg({"Valor": "sum"}).reset_index().sort_values("Mês")
        fig_bar = px.bar(agrupado_mes, x="Mês", y="Valor", text_auto='.2s',
                     labels={"Valor": "Valor (R$)", "Mês": "Mês de Referência"})
        fig_bar.update_traces(textposition="outside")
        st.plotly_chart(fig_bar, use_container_width=True)

    with chart_col2:
        st.subheader("Distribuição por Descrição")
        agrupado_desc = df_filtrado.groupby("Descricao").agg({"Valor": "sum"}).reset_index()
        # Para o gráfico de pizza não ficar poluído, podemos mostrar apenas os X maiores
        # e agrupar o resto em "Outros". Aqui, vamos mostrar os 10 maiores.
        top_n = 10
        if len(agrupado_desc) > top_n:
            agrupado_desc = agrupado_desc.sort_values("Valor", ascending=False)
            outros = pd.DataFrame({
                'Descricao': ['Outros'],
                'Valor': [agrupado_desc.iloc[top_n:]['Valor'].sum()]
            })
            agrupado_desc = pd.concat([agrupado_desc.iloc[:top_n], outros], ignore_index=True)

        fig_pie = px.pie(agrupado_desc, names="Descricao", values="Valor",
                         hole=.3) # O parâmetro 'hole' cria um gráfico de rosca (donut chart), mais moderno
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)


    with st.expander("Ver dados detalhados"):
        st.dataframe(df_filtrado)

else:
    st.warning("Não há dados disponíveis para exibição ou ocorreu um erro no carregamento.")
