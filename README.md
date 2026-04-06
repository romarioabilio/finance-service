# Painel Financeiro Pessoal

Aplicacao em Streamlit com visual mais limpo e foco em uso pessoal para acompanhar receitas, gastos, aportes e metas financeiras.

## O que esta pronto

- Painel mensal com receitas, gastos, aportes e saldo livre
- Score de saude financeira do mes
- Visual mais minimalista e profissional
- Historico de gastos por categoria
- Evolucao do patrimonio investido
- Simulador de metas com retorno esperado, volatilidade e aporte extra
- Formularios para cadastrar gasto, receita e aporte
- Cadastro de metas dentro do proprio app
- Edicao direta de dados com filtros e exclusao com confirmacao
- Suporte a `CSV` local e estrutura pronta para `Google Sheets`

## Estrutura

```text
.
|-- app.py
|-- requirements.txt
|-- data/
|   |-- lancamentos.csv
|   |-- receitas.csv
|   |-- aportes.csv
|   `-- metas.csv
`-- .streamlit/
    `-- secrets.toml.example
```

## Como rodar

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Estrutura dos datasets

### `data/lancamentos.csv`

Colunas: `data,categoria,descricao,valor,responsavel`

### `data/receitas.csv`

Colunas: `data,categoria,descricao,valor,responsavel`

### `data/aportes.csv`

Colunas: `data,valor,tipo`

### `data/metas.csv`

Colunas: `nome_meta,valor_alvo,data_limite,saldo_inicial`

## Google Sheets

1. Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`.
2. Crie uma planilha com as abas `Lancamentos`, `Receitas`, `Aportes` e `Metas`.
3. Use exatamente os mesmos nomes de colunas dos arquivos CSV.
4. Compartilhe a planilha com o e-mail da service account.
5. Ative a chave `Usar Google Sheets` no app.

## Experiencia

O app foi ajustado para funcionar como um site pessoal local:

- interface mais limpa
- resumo rapido na abertura
- metas com leitura mais facil
- movimentacoes editadas dentro do proprio app
