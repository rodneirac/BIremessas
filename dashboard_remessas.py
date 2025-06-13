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

LOGO_URL = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/logo.png"

@st.cache_data(ttl=300)
def get_latest_commit_info(owner, repo, file_path):
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits?path={file_path}&page=1&per_page=1"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        commit_data = response.json()
        if commit_data:
            commit_sha = commit_data[0]['sha']
            date_str = commit_data[0]['commit']['committer']['date']
            local_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            formatted_date = f"**{local_date.astimezone().strftime('%d/%m/%Y às %H:%M')}**"
            return formatted_date, commit_sha
    except requests.exceptions.RequestException:
        return "Erro ao obter data.", None
    return "Data não disponível.", None

# --- FUNÇÃO load_data MODIFICADA PARA INCLUIR VOLUME ---
@st.cache_data
def load_data(owner, repo, file_path, commit_sha):
    if not commit_sha:
        st.error("Não foi possível obter a versão do arquivo do GitHub.")
        return pd.DataFrame()

    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{commit_sha}/{
