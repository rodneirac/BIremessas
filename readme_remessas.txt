# Dashboard Remessas a Faturar

Este projeto exibe um dashboard interativo para acompanhamento de remessas a faturar, com base em uma planilha Excel hospedada no GitHub.

## 📊 Funcionalidades
- KPIs: Quantidade total de remessas, valor total e valor médio
- Filtros laterais: Base, Descrição, Cliente e Mês
- Gráfico interativo: Evolução mensal dos valores
- Leitura automática do Excel direto do repositório GitHub

## 🚀 Como executar localmente

```bash
# Clone o repositório
git clone https://github.com/rodneirac/BIremessas.git
cd BIremessas

# (Opcional) Crie um ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Instale as dependências
pip install -r requirements.txt

# Execute o app
streamlit run dashboard_remessas.py
```

## ☁️ Deploy com Streamlit Cloud
1. Acesse: [https://streamlit.io/cloud](https://streamlit.io/cloud)
2. Clique em **"New app"**
3. Conecte sua conta GitHub e selecione este repositório
4. Escolha o arquivo `dashboard_remessas.py`
5. Clique em **Deploy**

## 🗂 Estrutura esperada
```
├── dashboard_remessas.py       # Código principal
├── DADOSREMESSA.XLSX           # Planilha de remessas
├── logo.png                    # Logo institucional
├── requirements.txt            # Dependências do projeto
└── README.md                   # Este arquivo
```

---

Para sugestões, melhorias ou colaborações, abra uma *issue* ou envie um *pull request*.

> Este dashboard foi desenvolvido com foco em agilidade na tomada de decisão com base em dados financeiros operacionais.
