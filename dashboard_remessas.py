# --- Barra Lateral com Filtros Otimizados ---
st.sidebar.header("Filtros")

# --- Filtro de Base dentro de um Expander ---
with st.sidebar.expander("✔️ Filtrar por Base", expanded=False):
    bases = sorted(df["Base"].dropna().unique())
    base_sel = st.multiselect(
        "Selecione as Bases", # Label dentro do multiselect
        options=bases,
        default=bases,
        label_visibility="collapsed" # Oculta o label principal para não repetir
    )

# Adiciona um resumo da seleção fora do expander para o usuário saber o que está filtrado
if len(base_sel) == len(bases):
    st.sidebar.caption("Mostrando todas as bases.")
else:
    st.sidebar.caption(f"Bases selecionadas: {len(base_sel)} de {len(bases)}")

# --- Replique para os outros filtros ---
with st.sidebar.expander("✔️ Filtrar por Descrição", expanded=False):
    descricoes = sorted(df["Descricao"].dropna().unique())
    descricao_sel = st.multiselect(
        "Selecione as Descrições",
        options=descricoes,
        default=descricoes,
        label_visibility="collapsed"
    )

if len(descricao_sel) == len(descricoes):
    st.sidebar.caption("Mostrando todas as descrições.")
else:
    st.sidebar.caption(f"Descrições selecionadas: {len(descricao_sel)} de {len(descricoes)}")

# Continue o padrão para os filtros de Cliente e Mês...

# Lembre-se de usar as variáveis corretas (base_sel, descricao_sel, etc.) no seu filtro de DataFrame
df_filtrado = df[
    df["Base"].isin(base_sel) &
    df["Descricao"].isin(descricao_sel) # & etc...
]
