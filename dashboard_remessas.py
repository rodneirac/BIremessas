# 1) IMPORTS
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import locale
import sqlite3
from pathlib import Path
import unicodedata
import re
import io

# 2) CONFIGURAÇÕES INICIAIS
st.set_page_config(layout="wide")
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    st.warning("Localidade 'pt_BR.UTF-8' não encontrada...")

# 3) CONSTANTES
ID_ARQUIVO_DRIVE = "1wqnGdfpCE5Go7wlITqtfxrxpHxVpTzCT" # Mantido
URL_DOWNLOAD_DIRETO = f"https.drive.google.com/uc?export=download&id={ID_ARQUIVO_DRIVE}" # Mantido
LOGO_URL = "https.raw.githubusercontent.com/rodneirac/BIremessas/main/logo.png"

# 4) NORMALIZAÇÃO DE CHAVE DE CLIENTE
def normalize_cliente(s) -> str:
    """Gera chave estável: maiúsculas, sem acentos/pontuação, espaços colapsados."""
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    s = s.strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# 5) PERSISTÊNCIA (SQLite)
DB_PATH = Path("observacoes.db")

@st.cache_resource
def get_db_conn():
    conn = sqlite3.connect(DB_PATH.as_posix(), check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS obs_clientes_k (
            cliente_key    TEXT PRIMARY KEY,
            cliente_display TEXT,
            observacao     TEXT DEFAULT '',
            updated_at     TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_display ON obs_clientes_k (cliente_display)")
    conn.commit()
    return conn

def obs_listar(conn) -> pd.DataFrame:
    return pd.read_sql_query("SELECT cliente_key, cliente_display, observacao, updated_at FROM obs_clientes_k", conn)

def obs_dict(conn) -> dict:
    cur = conn.execute("SELECT cliente_key, observacao FROM obs_clientes_k")
    return {row[0]: (row[1] or "") for row in cur.fetchall()}

# >>> versão compatível de salvar (UPDATE e, se não afetou, INSERT)
def obs_salvar(conn, cliente_display: str, observacao: str):
    key = normalize_cliente(cliente_display)
    ts = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "UPDATE obs_clientes_k "
        "SET cliente_display = ?, observacao = ?, updated_at = ? "
        "WHERE cliente_key = ?",
        (cliente_display, observacao or "", ts, key)
    )
    if cur.rowcount == 0:
        conn.execute(
            "INSERT INTO obs_clientes_k (cliente_key, cliente_display, observacao, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (key, cliente_display, observacao or "", ts)
        )
    conn.commit()

def obs_importar_csv(conn, file_bytes: bytes):
    df = pd.read_csv(io.BytesIO(file_bytes), dtype=str).fillna("")
    req_cols = {"cliente_display", "observacao"}
    if not req_cols.issubset(set(map(str.lower, df.columns.str.lower()))):
        st.error("CSV deve conter as colunas: cliente_display, observacao")
        return
    cols = {c.lower(): c for c in df.columns}
    for _, row in df.iterrows():
        obs_salvar(conn, row[cols["cliente_display"]], row[cols["observacao"]])

def obs_exportar_csv(conn) -> bytes:
    df = obs_listar(conn)
    if df.empty:
        df = pd.DataFrame(columns=["cliente_display", "observacao", "updated_at"])
    out = io.StringIO()
    df[["cliente_display", "observacao", "updated_at"]].to_csv(out, index=False)
    return out.getvalue().encode("utf-8")

# 6) CARGA E PROCESSAMENTO DE DADOS
# <<< FUNÇÃO MODIFICADA PARA LER CSV DA URL >>>
@st.cache_data(ttl=300)
def load_data_from_url(url):
    try:
        # Tenta ler como UTF-8
        try:
            df = pd.read_csv(url)
        except UnicodeDecodeError:
            # Se falhar, tenta como Latin1 (comum no Brasil)
            df = pd.read_csv(url, encoding='latin1')
            
        update_time = f"**{datetime.now().strftime('%d/%m/%Y às %H:%M')}** (dados CSV do Google Drive)"
        return df, update_time
    except Exception as e:
        st.error(f"Erro ao carregar DADOS CSV da URL do Google Drive: {e}")
        st.info("Verifique se o link está correto e se o compartilhamento do arquivo está como 'Qualquer pessoa com o link'.")
        return pd.DataFrame(), "Erro na atualização"

# <<< FUNÇÃO MODIFICADA PARA PROCESSAR O NOVO FORMATO CSV >>>
def process_data(df_bruto):
    try:
        df = df_bruto.copy()

        # Mapeamento das colunas do NOVO CSV para as colunas ESPERADAS pelo dashboard
        colunas_mapeadas = {
            "BASE": "Base",
            "Descricao2": "Descricao",
            "Data_Ocorrencia2": "Data Ocorrencia",
            "VL_VALOR": "Valor",
            "NM_CLIENTE2": "Cliente",
            "Condicao_Pagto_SAP": "Cond Pagto SAP",
            "NU_DIA_CORTE_FATURAMENTO": "Dia Corte Fat."
        }
        
        # Verificar se todas as colunas necessárias existem
        colunas_necessarias_csv = list(colunas_mapeadas.keys())
        colunas_faltando = [col for col in colunas_necessarias_csv if col not in df.columns]
        
        if colunas_faltando:
            st.error(f"Erro no formato do CSV. Colunas não encontradas: {', '.join(colunas_faltando)}")
            st.info(f"Colunas encontradas: {', '.join(df.columns)}")
            return pd.DataFrame()

        # Renomear as colunas para o padrão do dashboard
        df = df.rename(columns=colunas_mapeadas)
        
        # Manter apenas as colunas que o dashboard realmente usa
        colunas_esperadas = list(colunas_mapeadas.values())
        df = df[colunas_esperadas]

        # --- Transformações (similares ao script original) ---

        # Converter Data Ocorrencia (formato MM/DD/YYYY do CSV)
        df["Data Ocorrencia"] = pd.to_datetime(df["Data Ocorrencia"], format='%m/%d/%Y', errors="coerce")
        
        # Converter Valor para numérico
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
        
        # Remover linhas com dados essenciais nulos
        df.dropna(subset=["Data Ocorrencia", "Valor", "Cliente"], inplace=True)
        
        # Criar coluna 'Mês'
        df["Mês"] = df["Data Ocorrencia"].dt.to_period("M").astype(str)
        
        # Aplicar regra de negócio específica (mantida do original)
        df.loc[df['Cond Pagto SAP'].astype(str) == 'V029', 'Cliente'] = 'GRUPO MRV ENGENHARIA SA'
        
        return df
    except Exception as e:
        st.error(f"Erro ao processar os dados do CSV: {e}")
        st.info("Ocorreu um erro inesperado durante o processamento dos dados.")
        return pd.DataFrame()

# 7) UI
st.image(LOGO_URL, width=200)
st.title("Dashboard Remessas a Faturar")

# A chamada da função é a mesma, mas ela agora baixa e processa o CSV
raw_df, update_info = load_data_from_url(URL_DOWNLOAD_DIRETO)
st.caption(f"Dados atualizados em: {update_info}")

if raw_df is not None and not raw_df.empty:
    df = process_data(raw_df)
    if not df.empty:
        # --------- Filtros ---------
        st.sidebar.header("Filtros")

        bases = sorted(df["Base"].dropna().unique())
        if 'base_selection' not in st.session_state:
            st.session_state['base_selection'] = []
        with st.sidebar.expander("✔️ Filtrar por Base", expanded=True):
            c1, c2 = st.columns(2)
            if c1.button("Selecionar Todas", key="btn_select_all_base", use_container_width=True):
                st.session_state['base_selection'] = bases
                st.rerun()
            if c2.button("Limpar Todas", key="btn_clear_all_base", use_container_width=True):
                st.session_state['base_selection'] = []
                st.rerun()
            st.session_state['base_selection'] = st.multiselect(
                "Selecione as Bases", options=bases, default=st.session_state['base_selection'], label_visibility="collapsed"
            )

        descricoes = sorted(df["Descricao"].dropna().unique())
        if 'desc_selection' not in st.session_state:
            st.session_state['desc_selection'] = []
        with st.sidebar.expander("✔️ Filtrar por Descrição", expanded=True):
            c3, c4 = st.columns(2)
            if c3.button("Selecionar Todas", key="btn_select_all_desc", use_container_width=True):
                st.session_state['desc_selection'] = descricoes
                st.rerun()
            if c4.button("Limpar Todas", key="btn_clear_all_desc", use_container_width=True):
                st.session_state['desc_selection'] = []
                st.rerun()
            st.session_state['desc_selection'] = st.multiselect(
                "Selecione as Descrições", options=descricoes, default=st.session_state['desc_selection'], label_visibility="collapsed"
            )

        meses = sorted(df["Mês"].dropna().unique(), reverse=True)
        if 'mes_selection' not in st.session_state:
            st.session_state['mes_selection'] = []
        with st.sidebar.expander("✔️ Filtrar por Mês", expanded=True):
            c5, c6 = st.columns(2)
            if c5.button("Selecionar Todos", key="btn_select_all_mes", use_container_width=True):
                st.session_state['mes_selection'] = meses
                st.rerun()
            if c6.button("Limpar Todas", key="btn_clear_all_mes", use_container_width=True):
                st.session_state['mes_selection'] = []
                st.rerun()
            st.session_state['mes_selection'] = st.multiselect(
                "Selecione os Meses", options=meses, default=st.session_state['mes_selection'], label_visibility="collapsed"
            )

        # --------- Utilitários de Observações ---------
        st.sidebar.header("Observações (backup)")
        conn = get_db_conn()
        up_file = st.sidebar.file_uploader("Restaurar observações (CSV)", type=["csv"])
        if up_file is not None:
            obs_importar_csv(conn, up_file.read())
            st.sidebar.success("Observações importadas com sucesso.")
        down_bytes = obs_exportar_csv(conn)
        st.sidebar.download_button("Baixar observações (CSV)", data=down_bytes, file_name="observacoes_clientes.csv", mime="text/csv")

        # --------- Aplicação dos filtros ---------
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
        cA, cB = st.columns(2)
        with cA:
            st.subheader("Evolução de Valores por Mês")
            agrupado_mes = df_filtrado.groupby("Mês").agg({"Valor": "sum"}).reset_index().sort_values("Mês")
            fig_bar = px.bar(agrupado_mes, x="Mês", y="Valor", text_auto='.2s', labels={"Valor": "Valor (R$)", "Mês": "Mês de Referência"})
            fig_bar.update_traces(textposition="outside")
            st.plotly_chart(fig_bar, use_container_width=True)

        with cB:
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

        # --------- RESUMO POR CLIENTE + OBSERVAÇÕES ---------
        with st.expander("Ver resumo por cliente", expanded=False):
            st.markdown("#### Somatório por Cliente (com base nos filtros aplicados)")
            resumo_cliente = df_filtrado.groupby("Cliente").agg(
                Valor_Total=('Valor', 'sum'),
                Qtde_Remessas=('Base', 'count')
            ).reset_index().sort_values("Valor_Total", ascending=False)

            resumo_cliente_exib = resumo_cliente.copy()
            resumo_cliente_exib['Valor_Total'] = resumo_cliente_exib['Valor_Total'].apply(
                lambda x: locale.format_string('R$ %.2f', x, grouping=True)
            )
            resumo_cliente_exib['Qtde_Remessas'] = resumo_cliente_exib['Qtde_Remessas'].apply(
                lambda x: locale.format_string('%d', x, grouping=True)
            )

            obs_map = obs_dict(conn)
            resumo_cliente_exib['Observação'] = resumo_cliente_exib['Cliente'].map(
                lambda c: obs_map.get(normalize_cliente(c), "")
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

            for rec in edited_df[['Cliente', 'Observação']].to_dict(orient='records'):
                cliente = rec.get('Cliente', '')
                obs = rec.get('Observação', '')
                if pd.isna(obs):
                    obs = ''
                obs_salvar(conn, cliente_display=cliente, observacao=obs)

else:
    st.warning("Não há dados disponíveis para exibição ou ocorreu um erro no carregamento.")
