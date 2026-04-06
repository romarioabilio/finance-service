# Finance Service

Aplicação em Streamlit com experiência de produto mais forte para gestão financeira pessoal, com dashboards, orçamentos, metas, recorrências e operação completa dentro do próprio app.

## O que esta pronto

- Visão geral executiva do mês
- Score de saúde financeira
- Orçamentos por categoria
- Gestão de metas com projeção determinística e Monte Carlo
- Recorrências mensais
- Insights e reflexão sobre consumo
- Cadastro e edição completa de gastos, receitas, investimentos, metas, orçamentos e recorrências
- Suporte a CSV local e Google Sheets

## Estrutura

```text
.
|-- app.py
|-- requirements.txt
|-- data/
|   |-- lancamentos.csv
|   |-- receitas.csv
|   |-- aportes.csv
|   |-- metas.csv
|   |-- orcamentos.csv
|   `-- recorrencias.csv
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

Colunas: `nome_meta,valor_alvo,data_limite,saldo_inicial,prioridade,status`

### `data/orcamentos.csv`

Colunas: `mes,categoria,orcado,alerta`

### `data/recorrencias.csv`

Colunas: `tipo,categoria,descricao,valor,dia_vencimento,status,observacao`

## Google Sheets

1. Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`.
2. Crie uma planilha com as abas `Lancamentos`, `Receitas`, `Aportes` e `Metas`.
3. Use exatamente os mesmos nomes de colunas dos arquivos CSV.
4. Compartilhe a planilha com o e-mail da service account.
5. Ative a chave `Usar Google Sheets` no app.

## Modo de uso

- `Visão geral`: leitura executiva do mês
- `Orçamentos`: comparação entre orçado e realizado
- `Metas`: progresso, projeções e simulações
- `Recorrências`: compromissos fixos previstos
- `Insights`: leitura analítica do comportamento financeiro
- `Registros`: área operacional para cadastrar e editar tudo
