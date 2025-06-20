import streamlit as st
import pandas as pd
from io import BytesIO

# --- Constantes ---
ID_ARQUIVO_DRIVE = "111jEo-wgeRKdXY7nq9laKeXRfifovHRR"
URL_DOWNLOAD_DIRETO = f"https://drive.google.com/uc?export=download&id={ID_ARQUIVO_DRIVE}"

st.set_page_config(layout="wide")
st.title("Diagnóstico de Colunas da Planilha")
st.info("Este é um modo de diagnóstico para verificar os nomes das colunas da sua planilha.")

try:
    # Tenta ler o arquivo, assumindo que o cabeçalho está na terceira linha (header=2)
    # Se isso falhar, tentaremos ler a partir da primeira linha (header=0)
    try:
        df = pd.read_excel(URL_DOWNLOAD_DIRETO, engine="openpyxl", header=2)
    except Exception:
        st.warning("Não foi possível ler com cabeçalho na linha 3, tentando ler a partir da linha 1...")
        df = pd.read_excel(URL_DOWNLOAD_DIRETO, engine="openpyxl", header=0)

    st.success("Arquivo lido com sucesso! Abaixo estão os nomes das colunas encontrados:")
    st.write("Por favor, compare esta lista com a lista esperada e procure por qualquer diferença (acentos, espaços, etc.)")
    
    st.subheader("Nomes de Coluna Encontrados no Arquivo:")
    st.code(list(df.columns))
    
    colunas_esperadas = ["Base", "Descricao", "Data Ocorrencia", "Valor", "Volume", "Cliente", "Cond Pagto SAP", "Dia Corte Fat."]
    st.subheader("Nomes de Coluna Esperados pelo Código:")
    st.code(colunas_esperadas)

    st.subheader("Amostra dos Dados (5 primeiras linhas):")
    st.dataframe(df.head())

except Exception as e:
    st.error(f"Ocorreu um erro crítico ao tentar ler o arquivo Excel: {e}")
    st.warning("Verifique se a permissão de compartilhamento está como 'Qualquer pessoa com o link' e se o arquivo é um .xlsx válido.")
