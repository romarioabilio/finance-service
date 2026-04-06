from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DATASETS = {
    "lancamentos": {
        "worksheet": "lancamentos",
        "path": DATA_DIR / "lancamentos.csv",
        "columns": ["data", "categoria", "descricao", "valor", "responsavel"],
        "date_columns": ["data"],
        "numeric_columns": ["valor"],
    },
    "receitas": {
        "worksheet": "receitas",
        "path": DATA_DIR / "receitas.csv",
        "columns": ["data", "categoria", "descricao", "valor", "responsavel"],
        "date_columns": ["data"],
        "numeric_columns": ["valor"],
    },
    "aportes": {
        "worksheet": "aportes",
        "path": DATA_DIR / "aportes.csv",
        "columns": ["data", "valor", "tipo"],
        "date_columns": ["data"],
        "numeric_columns": ["valor"],
    },
    "metas": {
        "worksheet": "metas",
        "path": DATA_DIR / "metas.csv",
        "columns": ["nome_meta", "valor_alvo", "data_limite", "saldo_inicial", "prioridade", "status"],
        "date_columns": ["data_limite"],
        "numeric_columns": ["valor_alvo", "saldo_inicial", "prioridade"],
    },
    "orcamentos": {
        "worksheet": "orcamentos",
        "path": DATA_DIR / "orcamentos.csv",
        "columns": ["mes", "categoria", "orcado", "alerta"],
        "date_columns": [],
        "numeric_columns": ["orcado", "alerta"],
    },
    "recorrencias": {
        "worksheet": "recorrencias",
        "path": DATA_DIR / "recorrencias.csv",
        "columns": ["tipo", "categoria", "descricao", "valor", "dia_vencimento", "status", "observacao"],
        "date_columns": [],
        "numeric_columns": ["valor", "dia_vencimento"],
    },
}

CATEGORIAS_GASTO = [
    "Moradia",
    "Mercado",
    "Transporte",
    "Saude",
    "Lazer",
    "Educacao",
    "Carro",
    "Assinaturas",
    "Impostos",
    "Outros",
]
CATEGORIAS_RECEITA = ["Salario", "Freelance", "Bonus", "Renda extra", "Investimentos", "Outros"]
TIPOS_APORTE = ["CDB", "LCI", "Tesouro", "ETF", "Acoes", "Caixinha", "Cripto", "Outro"]
TIPOS_RECORRENCIA = ["Gasto", "Receita", "Investimento"]
STATUS_META = ["Ativa", "Pausada", "Concluida"]
STATUS_RECORRENCIA = ["Ativa", "Pausada"]
RESPONSAVEL_PADRAO = "Romario"
COLOR_SCALE = ["#2563EB", "#0F766E", "#F59E0B", "#DC2626", "#7C3AED", "#0891B2", "#EA580C", "#64748B", "#84CC16", "#E11D48"]
MESES_PT = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}
