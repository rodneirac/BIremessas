# 1. IMPORTS
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import locale
import requests
from io import BytesIO, StringIO

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

# --- FUNÇÃO DE PROCESSAMENTO COM MODO DE DIAGNÓSTICO DETALHADO ---
def process_data(df_bruto):
    df = df_bruto.copy()
    
    with st.expander("🔍 Diagnóstico de Processamento de Dados (Clique para expandir)"):
        try:
            colunas_corretas = ["Base", "Descricao", "Data Ocorrencia", "Valor", "Volume", "Cliente", "Cond Pagto SAP", "Dia Corte Fat."]
            if len(df.columns) == len(colunas_corretas):
                df.columns = colunas_corretas
            else:
                st.error(f"O arquivo lido tem {len(df.columns)} colunas, mas o programa esperava {len(colunas_corretas)}.")
                return pd.DataFrame()

            st.subheader("1. Dados Após Renomear Colunas")
            st.write("Verifique se as colunas foram nomeadas corretamente e se os dados parecem corretos.")
            st.dataframe(df.head(10))

            # --- Tentativa de Conversão ---
            df_convertido = df.copy()
            df_convertido["Data Ocorrencia"] = pd.to_datetime(df_convertido["Data Ocorrencia"], errors='coerce')
            df_convertido["Valor"] = pd.to_numeric(df_convertido["Valor"], errors='coerce')

            st.subheader("2. Dados Após Conversão de Tipos")
            st.write("Verifique as colunas 'Data Ocorrencia' e 'Valor'. Se estiverem como 'NaT' ou 'NaN', a conversão falhou.")
            st.dataframe(df_convertido.head(10))

            st.subheader("3. Informações Técnicas (df.info)")
            buffer = StringIO()
            df_convertido.info(buf=buffer)
            s = buffer.getvalue()
            st.text("Observe o Dtype e a contagem de Non-Null das colunas 'Data Ocorrencia' e 'Valor'.", help="Dtype deve ser datetime64 e float64. Non-Null Count deve ser alto.")
            st.text_area("df.info():", s, height=350)
        except Exception as e:
            st.error(f"Um erro ocorreu dentro do bloco de diagnóstico: {e}")

    # O processamento original para retornar o dataframe vazio (causando a tela em branco)
    try:
        df_original = df_bruto.copy()
        colunas_corretas = ["Base", "Descricao", "Data Ocorrencia", "Valor", "Volume", "Cliente", "Cond Pagto SAP", "Dia Corte Fat."]
        if len(df_original.columns) == len(colunas_corretas):
            df_original.columns = colunas_corretas
        else:
            return pd.DataFrame() # Retorna vazio se as colunas não baterem

        df_original["Data Ocorrencia"] = pd.to_datetime(df_original["Data Ocorrencia"], errors="coerce")
        df_original["Valor"] = pd.to_numeric(df_original["Valor"], errors="coerce")
        df_original.dropna(subset=["Data Ocorrencia", "Valor", "Cliente"], inplace=True)
        
        # Se chegou aqui e o df está vazio, ele retorna vazio, causando a tela em branco.
        return df_original
    except:
        return pd.DataFrame() # Retorna vazio em caso de qualquer erro.

# 4. LÓGICA PRINCIPAL E CONSTRUÇÃO DA INTERFACE
st.image(LOGO_URL, width=200)
st.title("Dashboard Remessas a Faturar")

raw_df, update_info = load_data_from_url(URL_DOWNLOAD_DIRETO)
st.caption(f"Dados atualizados em: {update_info}")

if raw_df is not None and not raw_df.empty:
    # A função de processo é chamada, mas o diagnóstico será exibido primeiro.
    df = process_data(raw_df) 

    # Como 'df' retorna vazio, o código abaixo não é executado, resultando na tela em branco.
    if not df.empty:
        st.write("Processamento parece ter funcionado, exibindo dashboard...")
        # ... (código do dashboard)
else:
    st.warning("Não há dados disponíveis para exibição ou ocorreu um erro no carregamento.")
