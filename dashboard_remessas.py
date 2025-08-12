# 1. IMPORTS
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import locale
import sqlite3
from pathlib import Path
import unicodedata
import re

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

# ---------- Normalização de chaves ----------
def normalize_cliente(s) -> str:
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    s = s.strip().upper()
    # remove acentos
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # remove pontuação estranha, mantém letras, números e espaço
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    # colapsa espaços
    s = re.sub(r"\s+", " ", s).strip()
    return s

# ---------- Persistência das observações (SQLite) ----------
DB_PATH = Path("observacoes.db")

@st.cache_resource
def get_db_conn():
    conn = sqlite3.connect(DB_PATH.as_posix(), check_same_thread=False)
    # Tabela nova baseada em chave normalizada
    conn.execute("""
        CREATE TABLE IF NOT EXISTS obs_clientes_k (
            cliente_key TEXT PRIMARY KEY,
            cliente_display TEXT,
            observacao TEXT DEFAULT '',
            updated_at TEXT
        )
    """)
    # Migração simples da tabela antiga, se existir
    try:
        cur = conn.execute("SELECT cliente, observacao FROM obs_clientes")
        rows = cur.fetchall()
        for cli, obs in rows:
            key = normalize_cliente(cli)
            conn.execute(
                "INSERT INTO obs_clientes_k (cliente_key, cliente_display, observacao, updated_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(cliente_key) DO NOTHING",
                (key, cli, obs or "", datetime.now().isoformat(timespec="seconds"))
            )
        conn.commit()
    except sqlite3.OperationalError:
        # tabela antiga não existe — segue o jogo
        pass
    return conn

def carregar_observacoes(conn) -> dict:
    cur = conn.execute("SELECT cliente_key, observacao FROM obs_clientes_k")
    return {row[0]: (row[1] or "") for row in cur.fetchall()}

def salvar_observacao(conn, cliente_display: str, observacao: str):
    key = normalize_cliente(cliente_display)
    conn.execute(
        "INSERT INTO obs_clientes_k (cliente_key, cliente_display, observacao, updated_at) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(cliente_key) DO UPDATE SET "
        "cliente_display=excluded.cliente_display, "
        "observacao=excluded.observacao, "
        "updated_at=excluded.updated_at",
        (key, cliente_display, observacao, datetime.now().isoformat(timespec="seconds"))
    )
    conn.commit()

# ---------- Carga de dados ----------
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

# --- Processamento ---
def process_data(df_bruto):
    try:
        df = df_bruto.copy()
        # 1) Remove a coluna em branco (índice 1)
        df = df.drop(columns=[1])
        # 2) Define colunas
        colunas_corretas = ["Base", "Descricao", "Data Ocorrencia", "Valor", "Cliente", "Cond Pagto SAP", "Dia Corte Fat."]
        if len(df.columns) == len(colunas_corretas):
            df.columns = colunas_corretas
        else:
            st.error(f"O arquivo lido, após remover colunas em branco, tem {len(df.columns)} colunas, mas o programa esperava {len(colunas_corretas)}.")
            return pd.DataFrame()
        # 3) Conversões
        df["Data Ocorrencia"] = pd.to_datetime(df["Data Ocorrencia"], errors="coerce")
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
        df.dropna(subset=["Data Ocorrencia", "Valor", "Cliente"], inplace=True)
        df["Mês"] = df["Data Ocorrencia"].dt.to_period("M").astype(str)
        # 4) Regra de cliente para cond. pagto V029
        df.loc[df['Cond Pagto SAP'].astype(str) == 'V029', 'Cliente'] = 'GRUPO MRV ENGENHARIA SA'
        return df
    except Exception as e:
        st.error(f"Erro ao processar os dados: {e}")
        st.info("Ocorreu um erro inesperado durante o processamento dos dados.")
        return pd.DataFrame()

# 4. UI
st.image(LOGO_URL, width=200)
st.title("Dashboard Remessas a Faturar")

raw_df, update_info = load_data_from_url(URL_DOWNLOAD_DIRETO)
st.caption(f"Dados atualizados em: {update_info}")

if raw_df is not None and not raw_df.empty:
    df = process_data(raw_df)

    if not df.empty:
        # --------- FILTROS ---------
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
            if col5.button("Selecionar Todos", key='select_all_meses', use_container_width=True):
                st.session_state['mes_selection'] = meses
                st.rerun()
            if col6.button("Limpar Todas", key='clear_all_meses', use_container_width=True):
                st.session_state['mes_selection'] = []
                st.rerun()
            mes_sel = st.multiselect("Selecione os Meses", options=meses, default=st.session_state['mes_selection'], label_visibility="collapsed")
            st.session_state['mes_selection'] = mes_sel

        # --------- APLICAÇÃO DOS FILTROS ---------
        df_filtrado = df.copy()
        if st.session_state['base_selection']:
            df_filtrado = df_filtrado[df_filtrado['Base'].isin(st.session_state['base_selection'])]
        if st.session_state['desc_selection']:
            df_filtrado = df_filtrado[df_filtrado['Descricao'].isin(st.session_state['desc_selection'])]
        if st.session_state['mes_selection']:
            df_filtrado = df_filtrado[df_filtrado['Mês'].isin(st.session_state['mes_selection'])]

        # --------- KPIs ---------
        total_remessas = len(df_filtrado)
        valor_total = df_filtrado["Valor"].sum()
        valor_medio = df_filtrado["Valor"].mean() if total_remessas > 0 else 0

        st.markdown("### Indicadores Gerais")
        kpi_cols = st.columns(3)
        kpi_cols[0].metric("Qtde. Remessas", f"{total_remessas:n}")
        kpi_cols[1].metric("Valor Total (R$)", locale.format_string('%.2f', valor_total, grouping=True))
        kpi_cols[2].metric("Valor Médio (R$)", locale.format_string('%.2f', valor_medio, grouping=True))

        st.markdown("---")

        # --------- GRÁFICOS ---------
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

        st.subheader("Valor Total por Base")
        agrupado_base = df_filtrado.groupby("Base").agg({"Valor": "sum"}).reset_index().sort_values("Valor", ascending=False)
        fig_base = px.bar(agrupado_base, x="Base", y="Valor", title="Faturamento por Base", text_auto='.2s')
        fig_base.update_layout(xaxis={'categoryorder': 'total descending'})
        st.plotly_chart(fig_base, use_container_width=True)

        # --------- RESUMO POR CLIENTE + OBSERVAÇÕES (CHAVE NORMALIZADA) ---------
        with st.expander("Ver resumo por cliente", expanded=False):
            st.markdown("#### Somatório por Cliente (com base nos filtros aplicados)")

            resumo_cliente = df_filtrado.groupby("Cliente").agg(
                Valor_Total=('Valor', 'sum'),
                Qtde_Remessas=('Base', 'count')
            ).reset_index().sort_values("Valor_Total", ascending=False)

            # tabela exibida (formatação)
            resumo_cliente_exib = resumo_cliente.copy()
            resumo_cliente_exib['Valor_Total'] = resumo_cliente_exib['Valor_Total'].apply(
                lambda x: locale.format_string('R$ %.2f', x, grouping=True)
            )
            resumo_cliente_exib['Qtde_Remessas'] = resumo_cliente_exib['Qtde_Remessas'].apply(
                lambda x: locale.format_string('%d', x, grouping=True)
            )

            conn = get_db_conn()
            obs_dict = carregar_observacoes(conn)

            # Observação vinda do banco por chave normalizada
            resumo_cliente_exib['Observação'] = resumo_cliente_exib['Cliente'].map(
                lambda c: obs_dict.get(normalize_cliente(c), "")
            )

            edited_df = st.data_editor(
                resumo_cliente_exib,
                key="resumo_cliente_editor",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Cliente": st.column_config.TextColumn(disabled=True),
                    "Valor_Total": st.column_config.TextColumn(disabled=True),
                    "Qtde_Remessas": st.column_config.TextColumn(disabled=True),
                    "Observação": st.column_config.TextColumn(
                        help="Anotações livres vinculadas ao cliente (salvas automaticamente)",
                        width="medium"
                    ),
                },
            )

            # salvar alterações no banco (usa cliente_display atual + chave normalizada)
for rec in edited_df[['Cliente', 'Observação']].to_dict(orient='records'):
    cliente = rec.get('Cliente', '')
    obs = rec.get('Observação', '')
    if pd.isna(obs):
        obs = ''
    salvar_observacao(conn, cliente_display=cliente, observacao=obs)


else:
    st.warning("Não há dados disponíveis para exibição ou ocorreu um erro no carregamento.")
