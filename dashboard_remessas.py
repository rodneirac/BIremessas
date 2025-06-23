# 1. IMPORTS
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import locale
import requests
from io import BytesIO

# 2. CONFIGURAÇÕES INICIAIS DA PÁGINA E LOCALIDADE
st.set_page_config(layout="wide")
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    st.warning("Localidade 'pt_BR.UTF-8' não encontrada...")

# 3. CONSTANTES E FUNÇÕES
ID_ARQUIVO_DRIVE = "111jEo-wgeRKdXY7nq9laKeXRfifovHRR"
URL_DOWNLOAD_DIRETO = f"https://drive.google.com/uc?export=download&id={ID_ARQUIVO_DRIVE}"
LOGO_URL = "https://raw.githubusercontent.com/rodneirac/BIremessas/main/logo.png"

@st.cache_data(ttl=300)
def load_data_from_url(url):
    try:
        df = pd.read_excel(url, engine="openpyxl", skiprows=3, header=None)
        update_time = f"**{datetime.now().strftime('%d/%m/%Y às %H:%M')}** (dados do Google Drive)"
        return df, update_time
    except Exception as e:
        st.error(f"Erro ao carregar dados da URL do Google Drive: {e}")
        st.info("Verifique se o link está correto e se o compartilhamento do arquivo está como 'Qualquer pessoa com o link'.")
        return pd.DataFrame(), "Erro na atualização"

def process_data(df_bruto):
    try:
        df = df_bruto.copy()
        df = df.drop(columns=[1])
        colunas_corretas = ["Base", "Descricao", "Data Ocorrencia", "Valor", "Cliente", "Cond Pagto SAP", "Dia Corte Fat."]
        if len(df.columns) == len(colunas_corretas):
            df.columns = colunas_corretas
        else:
            st.error(f"O arquivo lido, após remover colunas em branco, tem {len(df.columns)} colunas, mas o programa esperava {len(colunas_corretas)}.")
            return pd.DataFrame()
        df["Data Ocorrencia"] = pd.to_datetime(df["Data Ocorrencia"], errors="coerce")
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
        df.dropna(subset=["Data Ocorrencia", "Valor", "Cliente"], inplace=True)
        df["Mês"] = df["Data Ocorrencia"].dt.to_period("M").astype(str)
        df.loc[df['Cond Pagto SAP'].astype(str) == 'V029', 'Cliente'] = 'Grupo MRV Engenharia'
        # Adicionando uma coluna de volume dummy, já que ela não existe mais no arquivo
        df['Volume'] = 0 
        return df
    except Exception as e:
        st.error(f"Erro ao processar os dados: {e}")
        st.info("Ocorreu um erro inesperado durante o processamento dos dados.")
        return pd.DataFrame()

# 4. LÓGICA PRINCIPAL E CONSTRUÇÃO DA INTERFACE
st.image(LOGO_URL, width=200)
st.title("Dashboard Remessas a Faturar")

raw_df, update_info = load_data_from_url(URL_DOWNLOAD_DIRETO)
st.caption(f"Dados atualizados em: {update_info}")

if raw_df is not None and not raw_df.empty:
    df = process_data(raw_df)
    if not df.empty:
        st.sidebar.header("Filtros")
        
        # (Filtros permanecem inalterados)
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
            base_sel = st.multiselect("Selecione as Bases", options=bases, default=st.session_state['base_selection'], label_visibility="collapsed")
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
            descricao_sel = st.multiselect("Selecione as Descrições", options=descricoes, default=st.session_state['desc_selection'], label_visibility="collapsed")
            st.session_state['desc_selection'] = descricao_sel

        meses = sorted(df["Mês"].dropna().unique(), reverse=True)
        if 'mes_selection' not in st.session_state:
            st.session_state['mes_selection'] = []
        with st.sidebar.expander("✔️ Filtrar por Mês", expanded=True):
            col5, col6 = st.columns(2)
            if col5.button("Selecionar Todas", key='select_all_meses', use_container_width=True):
                st.session_state['mes_selection'] = meses
                st.rerun()
            if col6.button("Limpar Todas", key='clear_all_meses', use_container_width=True):
                st.session_state['mes_selection'] = []
                st.rerun()
            mes_sel = st.multiselect("Selecione os Meses", options=meses, default=st.session_state['mes_selection'], label_visibility="collapsed")
            st.session_state['mes_selection'] = mes_sel

        df_filtrado = df.copy()
        if st.session_state['base_selection']:
            df_filtrado = df_filtrado[df_filtrado['Base'].isin(st.session_state['base_selection'])]
        if st.session_state['desc_selection']:
            df_filtrado = df_filtrado[df_filtrado['Descricao'].isin(st.session_state['desc_selection'])]
        if st.session_state['mes_selection']:
            df_filtrado = df_filtrado[df_filtrado['Mês'].isin(st.session_state['mes_selection'])]
        
        # (KPIs permanecem inalterados)
        total_remessas = len(df_filtrado)
        valor_total = df_filtrado["Valor"].sum()
        volume_total = df_filtrado["Volume"].sum()
        valor_medio = df_filtrado["Valor"].mean() if total_remessas > 0 else 0

        st.markdown("### Indicadores Gerais")
        kpi_cols = st.columns(3) 
        kpi_cols[0].metric("Qtde. Remessas", f"{total_remessas:n}")
        kpi_cols[1].metric("Valor Total (R$)", locale.format_string('%.2f', valor_total, grouping=True))
        kpi_cols[2].metric("Valor Médio (R$)", locale.format_string('%.2f', valor_medio, grouping=True))
        st.markdown("---")
        
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.subheader("Evolução de Valores por Mês")
            agrupado_mes = df_filtrado.groupby("Mês").agg({"Valor": "sum"}).reset_index().sort_values("Mês")
            fig_bar = px.bar(agrupado_mes, x="Mês", y="Valor", text_auto='.2s', labels={"Valor": "Valor (R$)", "Mês": "Mês de Referência"})
            fig_bar.update_traces(textposition="outside")
            st.plotly_chart(fig_bar, use_container_width=True)

        with chart_col2:
            st.subheader("Distribuição por Descrição")
            agrupado_desc = df_filtrado.groupby("Descricao").agg({"Valor": "sum"}).reset_index()
            top_n = 10
            if len(agrupado_desc) > top_n:
                agrupado_desc = agrupado_desc.sort_values("Valor", ascending=False)
                outros = pd.DataFrame({'Descricao': ['Outros'], 'Valor': [agrupado_desc.iloc[top_n:]['Valor'].sum()]})
                agrupado_desc = pd.concat([agrupado_desc.iloc[:top_n], outros], ignore_index=True)
            fig_pie = px.pie(agrupado_desc, names="Descricao", values="Valor", hole=.3)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        st.markdown("---")

        # --- GRÁFICO DE BARRAS ANIMADO ---
        st.subheader("Evolução do Valor por Base ao Longo dos Meses")
        # Agrupa os dados por Mês e Base para a animação
        agrupado_anim = df_filtrado.groupby(['Mês', 'Base'])['Valor'].sum().reset_index().sort_values(by='Mês')
        
        if not agrupado_anim.empty:
            # Cria o gráfico de barras animado
            fig_animada = px.bar(
                agrupado_anim,
                x="Base",
                y="Valor",
                color="Base",
                animation_frame="Mês",
                animation_group="Base",
                range_y=[0, agrupado_anim['Valor'].max() * 1.1], # Eixo Y fixo para melhor comparação
                labels={"Valor": "Valor Acumulado (R$)"}
            )
            fig_animada.update_layout(xaxis={'categoryorder':'total descending'})
            st.plotly_chart(fig_animada, use_container_width=True)
        else:
            st.info("Não há dados para o gráfico animado com os filtros selecionados.")
        

        with st.expander("Ver resumo por cliente"):
            st.markdown("#### Somatório por Cliente (com base nos filtros aplicados)")
            resumo_cliente = df_filtrado.groupby("Cliente").agg(Valor_Total=('Valor', 'sum'), Qtde_Remessas=('Base', 'count')).reset_index()
            resumo_cliente = resumo_cliente.sort_values("Valor_Total", ascending=False)
            resumo_cliente['Valor_Total'] = resumo_cliente['Valor_Total'].apply(lambda x: locale.format_string('R$ %.2f', x, grouping=True))
            resumo_cliente['Qtde_Remessas'] = resumo_cliente['Qtde_Remessas'].apply(lambda x: locale.format_string('%d', x, grouping=True))
            st.dataframe(resumo_cliente, use_container_width=True, hide_index=True)

    else:
        st.warning("Dados carregados, mas o processamento resultou em uma tabela vazia.")
else:
    st.warning("Não há dados disponíveis para exibição ou ocorreu um erro no carregamento.")
