from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:  # pragma: no cover
    GSheetsConnection = None


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

DATASETS = {
    "lancamentos": {
        "worksheet": "lancamentos",
        "path": DATA_DIR / "lancamentos.csv",
        "date_columns": ["data"],
        "numeric_columns": ["valor"],
    },
    "receitas": {
        "worksheet": "receitas",
        "path": DATA_DIR / "receitas.csv",
        "date_columns": ["data"],
        "numeric_columns": ["valor"],
    },
    "aportes": {
        "worksheet": "aportes",
        "path": DATA_DIR / "aportes.csv",
        "date_columns": ["data"],
        "numeric_columns": ["valor"],
    },
    "metas": {
        "worksheet": "metas",
        "path": DATA_DIR / "metas.csv",
        "date_columns": ["data_limite"],
        "numeric_columns": ["valor_alvo", "saldo_inicial"],
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
    "Outros",
]
CATEGORIAS_RECEITA = ["Salario", "Freelance", "Bonus", "Renda extra", "Outros"]
TIPOS_APORTE = ["CDB", "LCI", "Tesouro", "Caixinha", "ETF", "Outro"]
RESPONSAVEL_PADRAO = "Romario"
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
COLOR_SCALE = ["#1D4ED8", "#0F766E", "#F59E0B", "#DC2626", "#7C3AED", "#2563EB", "#EA580C", "#475569"]


@dataclass
class DataStore:
    mode: str
    conn: Optional[object] = None

    def read(self, dataset_name: str) -> pd.DataFrame:
        config = DATASETS[dataset_name]
        if self.mode == "gsheets" and self.conn is not None:
            df = self.conn.read(worksheet=config["worksheet"], ttl=0)
        else:
            df = pd.read_csv(config["path"])
        return normalize_dataframe(df, config)

    def write(self, dataset_name: str, df: pd.DataFrame) -> None:
        config = DATASETS[dataset_name]
        serialized = serialize_dataframe(df, config)
        if self.mode == "gsheets" and self.conn is not None:
            self.conn.update(worksheet=config["worksheet"], data=serialized)
        else:
            serialized.to_csv(config["path"], index=False)

    def append(self, dataset_name: str, row: dict) -> None:
        current = self.read(dataset_name)
        updated = pd.concat([current, pd.DataFrame([row])], ignore_index=True)
        self.write(dataset_name, updated)


def normalize_dataframe(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    data = df.copy()
    for column in config.get("date_columns", []):
        if column in data.columns:
            data[column] = pd.to_datetime(data[column], errors="coerce")
    for column in config.get("numeric_columns", []):
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0.0)
    return data


def serialize_dataframe(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    data = df.copy()
    for column in config.get("date_columns", []):
        if column in data.columns:
            data[column] = pd.to_datetime(data[column], errors="coerce").dt.strftime("%Y-%m-%d")
    return data


def load_all_data(store: DataStore) -> dict[str, pd.DataFrame]:
    datasets = {name: store.read(name) for name in DATASETS}
    validate_dataframes(datasets)
    return datasets


def validate_dataframes(datasets: dict[str, pd.DataFrame]) -> None:
    required = {
        "lancamentos": {"data", "categoria", "descricao", "valor", "responsavel"},
        "receitas": {"data", "categoria", "descricao", "valor", "responsavel"},
        "aportes": {"data", "valor", "tipo"},
        "metas": {"nome_meta", "valor_alvo", "data_limite", "saldo_inicial"},
    }
    for dataset_name, columns in required.items():
        current = datasets[dataset_name]
        missing = columns.difference(current.columns)
        if missing:
            st.error(f"Dataset '{dataset_name}' esta sem colunas obrigatorias: {', '.join(sorted(missing))}")
            st.stop()


def format_currency(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_period(period: pd.Period) -> str:
    return f"{MESES_PT[period.month]}/{period.year}"


def derive_month_options(*frames: pd.DataFrame) -> list[pd.Period]:
    periods: list[pd.Period] = []
    for frame in frames:
        if "data" in frame.columns and not frame.empty:
            periods.extend(frame["data"].dropna().dt.to_period("M").tolist())
    if not periods:
        periods = [pd.Timestamp.today().to_period("M")]
    return sorted(set(periods), reverse=True)


def get_data_store() -> DataStore:
    use_gsheets = st.sidebar.toggle("Usar Google Sheets", value=False)
    if use_gsheets and GSheetsConnection is not None:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            return DataStore(mode="gsheets", conn=conn)
        except Exception as exc:  # pragma: no cover
            st.sidebar.warning(f"Falha ao conectar no Google Sheets: {exc}")
    elif use_gsheets:
        st.sidebar.warning("Conector de Google Sheets nao configurado.")
    return DataStore(mode="local")


def monthly_summary(
    receitas: pd.DataFrame,
    lancamentos: pd.DataFrame,
    aportes: pd.DataFrame,
    selected_period: pd.Period,
) -> dict:
    receitas_mes = receitas[receitas["data"].dt.to_period("M") == selected_period]
    gastos_mes = lancamentos[lancamentos["data"].dt.to_period("M") == selected_period]
    aportes_mes = aportes[aportes["data"].dt.to_period("M") == selected_period]

    receita_total = float(receitas_mes["valor"].sum())
    gasto_total = float(gastos_mes["valor"].sum())
    aporte_total = float(aportes_mes["valor"].sum())
    saldo_livre = receita_total - gasto_total
    savings_rate = (aporte_total / receita_total * 100) if receita_total > 0 else 0.0

    return {
        "receita_total": receita_total,
        "gasto_total": gasto_total,
        "aporte_total": aporte_total,
        "saldo_livre": saldo_livre,
        "savings_rate": savings_rate,
    }


def compute_health_score(summary: dict, budget: float) -> tuple[int, str]:
    score = 45
    receita_total = summary["receita_total"]
    gasto_total = summary["gasto_total"]
    aporte_total = summary["aporte_total"]

    if budget > 0:
        usage = gasto_total / budget
        if usage <= 0.8:
            score += 20
        elif usage <= 1.0:
            score += 8
        else:
            score -= 12

    if receita_total > 0:
        savings_rate = aporte_total / receita_total
        expense_ratio = gasto_total / receita_total
        if savings_rate >= 0.25:
            score += 22
        elif savings_rate >= 0.15:
            score += 14
        elif savings_rate >= 0.08:
            score += 8

        if expense_ratio <= 0.6:
            score += 12
        elif expense_ratio >= 0.9:
            score -= 10

    score = max(0, min(100, score))
    if score >= 80:
        label = "Excelente"
    elif score >= 65:
        label = "Boa"
    elif score >= 45:
        label = "Atencao"
    else:
        label = "Critica"
    return score, label


def build_month_insights(summary: dict, budget: float) -> str:
    messages = []
    if summary["receita_total"] <= 0:
        messages.append("Comece cadastrando suas receitas para liberar uma leitura financeira mais precisa.")
    elif summary["gasto_total"] == 0:
        messages.append("Voce ainda nao registrou gastos neste mes.")
    else:
        messages.append("Seu painel ja tem informacoes suficientes para acompanhar o ritmo do mes.")

    if budget > 0 and summary["gasto_total"] > budget:
        messages.append(f"Os gastos passaram do limite em {format_currency(summary['gasto_total'] - budget)}.")
    elif budget > 0 and summary["gasto_total"] >= budget * 0.85:
        messages.append("Os gastos ja estao perto do limite definido para o mes.")
    else:
        messages.append("O consumo segue dentro de uma faixa confortavel.")

    if summary["receita_total"] > 0:
        messages.append(f"Savings rate atual: {summary['savings_rate']:.1f}%.")

    return " ".join(messages)


def empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": "Sem dados ainda",
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 16, "color": "#64748B"},
            }
        ],
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    return fig


def style_figure(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 16, "r": 16, "t": 56, "b": 16},
        font={"family": "Manrope, sans-serif", "color": "#1E293B"},
        title={"font": {"size": 18, "color": "#0F172A"}},
        legend={"bgcolor": "rgba(0,0,0,0)", "title": {"text": ""}},
    )
    return fig


def build_expense_category_chart(lancamentos: pd.DataFrame, selected_period: pd.Period) -> go.Figure:
    filtered = lancamentos[lancamentos["data"].dt.to_period("M") == selected_period]
    grouped = filtered.groupby("categoria", as_index=False)["valor"].sum()
    if grouped.empty:
        return empty_figure("Distribuicao dos gastos")
    fig = px.pie(
        grouped,
        names="categoria",
        values="valor",
        hole=0.62,
        title="Distribuicao dos gastos",
        color_discrete_sequence=COLOR_SCALE,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return style_figure(fig)


def build_cashflow_chart(datasets: dict[str, pd.DataFrame], selected_period: pd.Period) -> go.Figure:
    receitas = datasets["receitas"][datasets["receitas"]["data"].dt.to_period("M") == selected_period]["valor"].sum()
    gastos = datasets["lancamentos"][datasets["lancamentos"]["data"].dt.to_period("M") == selected_period]["valor"].sum()
    aportes = datasets["aportes"][datasets["aportes"]["data"].dt.to_period("M") == selected_period]["valor"].sum()
    cashflow = pd.DataFrame({"tipo": ["Entradas", "Gastos", "Investimentos"], "valor": [receitas, gastos, aportes]})
    if cashflow["valor"].sum() == 0:
        return empty_figure("Fluxo do mes")
    fig = px.bar(
        cashflow,
        x="tipo",
        y="valor",
        color="tipo",
        title="Fluxo do mes",
        color_discrete_map={"Entradas": "#16A34A", "Gastos": "#DC2626", "Investimentos": "#2563EB"},
    )
    fig.update_layout(showlegend=False)
    return style_figure(fig)


def build_expense_trend_chart(lancamentos: pd.DataFrame) -> go.Figure:
    if lancamentos.empty:
        return empty_figure("Historico de gastos")
    trend = (
        lancamentos.assign(mes=lancamentos["data"].dt.to_period("M").astype(str))
        .groupby(["mes", "categoria"], as_index=False)["valor"]
        .sum()
    )
    fig = px.bar(
        trend,
        x="mes",
        y="valor",
        color="categoria",
        title="Historico de gastos por categoria",
        color_discrete_sequence=COLOR_SCALE,
    )
    return style_figure(fig)


def build_net_worth_chart(aportes: pd.DataFrame) -> go.Figure:
    if aportes.empty:
        return empty_figure("Patrimonio investido")
    patrimonio = aportes.sort_values("data").copy()
    patrimonio["patrimonio"] = patrimonio["valor"].cumsum()
    fig = px.line(
        patrimonio,
        x="data",
        y="patrimonio",
        markers=True,
        title="Patrimonio investido",
    )
    fig.update_traces(line_color="#1D4ED8", line_width=3)
    return style_figure(fig)


def project_goal(
    current_balance: float,
    monthly_contribution: float,
    target_value: float,
    annual_rate: float,
    extra_contribution: float,
    max_months: int = 240,
) -> pd.DataFrame:
    balance = current_balance
    monthly_rate = (1 + annual_rate) ** (1 / 12) - 1
    rows = []
    for month in range(max_months + 1):
        current_date = pd.Timestamp.today().normalize() + pd.DateOffset(months=month)
        rows.append({"data": current_date, "patrimonio": balance, "meses": month})
        if balance >= target_value:
            break
        balance = balance * (1 + monthly_rate) + monthly_contribution + extra_contribution
    return pd.DataFrame(rows)


def monte_carlo_goal(
    current_balance: float,
    monthly_contribution: float,
    target_value: float,
    annual_return: float,
    annual_volatility: float,
    extra_contribution: float,
    simulations: int,
    max_months: int = 240,
) -> pd.DataFrame:
    mean_monthly = annual_return / 12
    vol_monthly = annual_volatility / np.sqrt(12)
    rng = np.random.default_rng(42)
    reached_in = []
    for _ in range(simulations):
        balance = current_balance
        for month in range(1, max_months + 1):
            sampled_return = rng.normal(mean_monthly, vol_monthly)
            balance = balance * (1 + sampled_return) + monthly_contribution + extra_contribution
            if balance >= target_value:
                reached_in.append(month)
                break
        else:
            reached_in.append(max_months)
    dates = [pd.Timestamp.today().normalize() + pd.DateOffset(months=int(month)) for month in reached_in]
    return pd.DataFrame({"meses": reached_in, "data_estimada": dates})


def compute_goal_progress(meta_row: pd.Series, aportes: pd.DataFrame) -> dict:
    current_balance = float(aportes["valor"].sum()) + float(meta_row["saldo_inicial"])
    target = float(meta_row["valor_alvo"])
    progress = current_balance / target if target > 0 else 0.0
    return {"saldo_atual": current_balance, "faltante": target - current_balance, "progresso": progress}


def average_recent_aportes(aportes: pd.DataFrame) -> float:
    if aportes.empty:
        return 0.0
    recent = (
        aportes.sort_values("data")
        .assign(periodo=lambda frame: frame["data"].dt.to_period("M"))
        .groupby("periodo", as_index=False)["valor"]
        .sum()
        .tail(3)["valor"]
        .mean()
    )
    return float(0.0 if np.isnan(recent) else recent)

def prepare_editor_dataframe(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    editor_df = df.copy()
    for column in DATASETS[dataset_name].get("date_columns", []):
        if column in editor_df.columns:
            editor_df[column] = pd.to_datetime(editor_df[column], errors="coerce").dt.date
    return editor_df


def coerce_editor_dataframe(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    coerced = df.copy()
    for column in DATASETS[dataset_name].get("date_columns", []):
        if column in coerced.columns:
            coerced[column] = pd.to_datetime(coerced[column], errors="coerce")
    for column in DATASETS[dataset_name].get("numeric_columns", []):
        if column in coerced.columns:
            coerced[column] = pd.to_numeric(coerced[column], errors="coerce")
    return coerced


def validate_editor_dataframe(df: pd.DataFrame, dataset_name: str) -> tuple[bool, str]:
    required_columns = {
        "lancamentos": ["data", "categoria", "descricao", "valor", "responsavel"],
        "receitas": ["data", "categoria", "descricao", "valor", "responsavel"],
        "aportes": ["data", "valor", "tipo"],
        "metas": ["nome_meta", "valor_alvo", "data_limite", "saldo_inicial"],
    }
    cleaned = df.dropna(how="all").copy()
    for column in required_columns[dataset_name]:
        if column not in cleaned.columns:
            return False, f"Coluna obrigatoria ausente: {column}."
        if cleaned[column].isna().any():
            return False, f"Preencha todos os campos da coluna '{column}'."
        if cleaned[column].astype(str).str.strip().eq("").any():
            return False, f"Existem valores vazios na coluna '{column}'."
    for column in DATASETS[dataset_name].get("numeric_columns", []):
        if cleaned[column].isna().any():
            return False, f"A coluna '{column}' tem valores invalidos."
    return True, ""


def editor_column_config(dataset_name: str) -> dict:
    if dataset_name == "lancamentos":
        return {
            "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "categoria": st.column_config.SelectboxColumn("Categoria", options=CATEGORIAS_GASTO, required=True),
            "descricao": st.column_config.TextColumn("Descricao", required=True),
            "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", min_value=0.0, step=10.0),
            "responsavel": None,
        }
    if dataset_name == "receitas":
        return {
            "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "categoria": st.column_config.SelectboxColumn("Categoria", options=CATEGORIAS_RECEITA, required=True),
            "descricao": st.column_config.TextColumn("Descricao", required=True),
            "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", min_value=0.0, step=50.0),
            "responsavel": None,
        }
    if dataset_name == "aportes":
        return {
            "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", min_value=0.0, step=50.0),
            "tipo": st.column_config.SelectboxColumn("Tipo", options=TIPOS_APORTE, required=True),
        }
    return {
        "nome_meta": st.column_config.TextColumn("Nome da meta", required=True),
        "valor_alvo": st.column_config.NumberColumn("Valor alvo", format="R$ %.2f", min_value=0.0, step=500.0),
        "data_limite": st.column_config.DateColumn("Data limite", format="DD/MM/YYYY"),
        "saldo_inicial": st.column_config.NumberColumn("Saldo inicial", format="R$ %.2f", min_value=0.0, step=500.0),
    }


def attach_row_ids(df: pd.DataFrame) -> pd.DataFrame:
    identified = df.reset_index(drop=True).copy()
    identified["_row_id"] = [str(index) for index in identified.index]
    return identified


def filter_options_for_period(df: pd.DataFrame, date_column: str) -> list[str]:
    if date_column not in df.columns or df.empty:
        return ["Todos"]
    periods = sorted(df[date_column].dropna().dt.to_period("M").unique(), reverse=True)
    return ["Todos"] + [format_period(period) for period in periods]


def apply_editor_filters(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    filtered = df.copy()
    col1, col2 = st.columns([1, 1])

    if "data" in filtered.columns:
        month_options = filter_options_for_period(filtered, "data")
        selected_month = col1.selectbox("Mes", month_options, key=f"mes_{dataset_name}")
        if selected_month != "Todos":
            month_number = [number for number, name in MESES_PT.items() if selected_month.startswith(name)][0]
            year = int(selected_month.split("/")[1])
            selected_period = pd.Period(year=year, month=month_number, freq="M")
            filtered = filtered[filtered["data"].dt.to_period("M") == selected_period]
    elif "data_limite" in filtered.columns:
        month_options = filter_options_for_period(filtered.rename(columns={"data_limite": "data"}), "data")
        selected_month = col1.selectbox("Prazo", month_options, key=f"prazo_{dataset_name}")
        if selected_month != "Todos":
            month_number = [number for number, name in MESES_PT.items() if selected_month.startswith(name)][0]
            year = int(selected_month.split("/")[1])
            selected_period = pd.Period(year=year, month=month_number, freq="M")
            filtered = filtered[filtered["data_limite"].dt.to_period("M") == selected_period]

    search = col2.text_input("Buscar", key=f"busca_{dataset_name}", placeholder="Descricao, categoria ou nome")
    if search:
        mask = pd.Series(False, index=filtered.index)
        for column in filtered.columns:
            if filtered[column].dtype == "object":
                mask = mask | filtered[column].fillna("").str.contains(search, case=False, regex=False)
        filtered = filtered[mask]
    return filtered


def merge_edited_subset(original_df: pd.DataFrame, visible_df: pd.DataFrame, edited_df: pd.DataFrame) -> pd.DataFrame:
    visible_ids = set(visible_df["_row_id"].tolist())
    preserved = original_df[~original_df["_row_id"].isin(visible_ids)].copy()

    row_ids = edited_df["_row_id"].fillna("").astype(str).str.strip()
    edited_existing = edited_df[row_ids != ""].copy()
    new_rows = edited_df[row_ids == ""].copy()

    next_id = max([int(row_id) for row_id in original_df["_row_id"].tolist()] + [-1]) + 1
    if not new_rows.empty:
        new_rows.loc[:, "_row_id"] = [str(next_id + idx) for idx in range(len(new_rows))]

    final_df = pd.concat([preserved, edited_existing, new_rows], ignore_index=True)
    return final_df


def build_delete_options(df: pd.DataFrame, dataset_name: str) -> dict[str, str]:
    options: dict[str, str] = {}
    for _, row in df.iterrows():
        if dataset_name == "metas":
            label = f"{row['nome_meta']} | alvo {format_currency(float(row['valor_alvo']))}"
        elif dataset_name == "aportes":
            label = f"{pd.to_datetime(row['data']).strftime('%d/%m/%Y')} | {row['tipo']} | {format_currency(float(row['valor']))}"
        else:
            label = f"{pd.to_datetime(row['data']).strftime('%d/%m/%Y')} | {row['descricao']} | {format_currency(float(row['valor']))}"
        options[label] = row["_row_id"]
    return options


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"]  {
            font-family: 'Manrope', sans-serif;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(59, 130, 246, 0.08), transparent 28%),
                radial-gradient(circle at top right, rgba(16, 185, 129, 0.06), transparent 22%),
                linear-gradient(180deg, #F8FAFC 0%, #F1F5F9 100%);
        }
        .block-container {
            max-width: 1160px;
            padding-top: 1.2rem;
            padding-bottom: 3rem;
        }
        [data-testid="stSidebar"] {
            background: rgba(255,255,255,0.85);
            border-right: 1px solid #E2E8F0;
        }
        .hero {
            background: linear-gradient(135deg, #0F172A 0%, #1D4ED8 100%);
            border-radius: 28px;
            padding: 1.8rem;
            color: white;
            box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
            margin-bottom: 1rem;
        }
        .hero-kicker {
            text-transform: uppercase;
            letter-spacing: .14em;
            font-size: .78rem;
            color: rgba(255,255,255,.72);
            margin-bottom: .45rem;
        }
        .hero-title {
            font-size: 2.15rem;
            line-height: 1.05;
            font-weight: 800;
            margin-bottom: .55rem;
        }
        .hero-copy {
            max-width: 740px;
            color: rgba(255,255,255,.86);
            font-size: 1rem;
            margin: 0;
        }
        .section-shell {
            background: rgba(255,255,255,0.86);
            border: 1px solid #E2E8F0;
            border-radius: 24px;
            padding: 1rem 1rem .25rem 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 12px 32px rgba(15, 23, 42, 0.05);
        }
        .section-title {
            font-size: 1.08rem;
            font-weight: 800;
            color: #0F172A;
            margin-bottom: .2rem;
        }
        .section-copy {
            color: #64748B;
            font-size: .95rem;
            margin-bottom: .7rem;
        }
        .stat-card {
            background: rgba(255,255,255,0.92);
            border: 1px solid #E2E8F0;
            border-radius: 22px;
            padding: 1rem;
            min-height: 126px;
            box-shadow: 0 12px 26px rgba(15, 23, 42, 0.04);
        }
        .stat-label {
            color: #64748B;
            font-size: .82rem;
            margin-bottom: .55rem;
            text-transform: uppercase;
            letter-spacing: .08em;
        }
        .stat-value {
            color: #0F172A;
            font-size: 1.72rem;
            font-weight: 800;
            line-height: 1.05;
            margin-bottom: .25rem;
        }
        .stat-foot {
            color: #475569;
            font-size: .9rem;
        }
        .empty-state {
            background: rgba(255,255,255,0.9);
            border: 1px dashed #CBD5E1;
            border-radius: 24px;
            padding: 1.4rem;
            color: #334155;
            margin-bottom: 1rem;
        }
        .quick-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 1rem;
        }
        .quick-card {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 22px;
            padding: 1rem;
            box-shadow: 0 12px 24px rgba(15, 23, 42, 0.04);
        }
        .quick-index {
            display: inline-flex;
            width: 30px;
            height: 30px;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            background: #DBEAFE;
            color: #1D4ED8;
            font-weight: 800;
            margin-bottom: .8rem;
        }
        .quick-title {
            font-weight: 700;
            color: #0F172A;
            margin-bottom: .35rem;
        }
        .quick-copy {
            color: #64748B;
            font-size: .94rem;
            margin: 0;
        }
        .stButton > button {
            min-height: 2.9rem;
            border-radius: 999px;
            border: 1px solid #CBD5E1;
            background: white;
            font-weight: 700;
        }
        .stButton > button:hover {
            border-color: #1D4ED8;
            color: #1D4ED8;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 999px;
            padding-left: 1rem;
            padding-right: 1rem;
            background: #E2E8F0;
        }
        .stTabs [aria-selected="true"] {
            background: #0F172A !important;
            color: white !important;
        }
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        .stDateInput > div > div,
        .stNumberInput > div > div {
            background: rgba(255,255,255,0.92);
            border-radius: 16px;
        }
        div[data-testid="stDataFrame"] {
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid #E2E8F0;
        }
        .stAlert {
            border-radius: 18px;
        }
        @media (max-width: 900px) {
            .quick-grid {
                grid-template-columns: 1fr;
            }
            .hero-title {
                font-size: 1.75rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header() -> None:
    st.set_page_config(page_title="Painel Financeiro Pessoal", page_icon="PF", layout="wide")
    inject_styles()
    st.markdown(
        """
        <div class="hero">
            <div class="hero-kicker">Financeiro pessoal</div>
            <div class="hero-title">Um painel com cara de produto, nao de planilha.</div>
            <p class="hero-copy">Controle receitas, gastos, investimentos e metas com uma navegacao mais clara, visual mais premium e operacao toda feita dentro da propria plataforma.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="section-shell">
            <div class="section-title">{title}</div>
            <div class="section-copy">{copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stat_card(label: str, value: str, foot: str) -> None:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">{label}</div>
            <div class="stat-value">{value}</div>
            <div class="stat-foot">{foot}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_onboarding() -> None:
    st.markdown(
        """
        <div class="empty-state">
            <strong>Seu painel esta pronto para receber os primeiros dados.</strong><br>
            Comece pela area de registros e alimente a plataforma com sua rotina real.
        </div>
        <div class="quick-grid">
            <div class="quick-card">
                <div class="quick-index">1</div>
                <div class="quick-title">Cadastre suas receitas</div>
                <p class="quick-copy">Isso libera uma leitura mais fiel do saldo, do limite mensal e da sua taxa de poupanca.</p>
            </div>
            <div class="quick-card">
                <div class="quick-index">2</div>
                <div class="quick-title">Lance os gastos do mes</div>
                <p class="quick-copy">Com alguns registros voce ja passa a enxergar para onde o dinheiro esta indo.</p>
            </div>
            <div class="quick-card">
                <div class="quick-index">3</div>
                <div class="quick-title">Crie pelo menos uma meta</div>
                <p class="quick-copy">Assim o painel consegue projetar prazos, mostrar progresso e orientar aportes.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_sidebar(datasets: dict[str, pd.DataFrame]) -> dict:
    st.sidebar.markdown("### Navegacao")
    page = st.sidebar.radio(
        "Pagina",
        ["Visao geral", "Metas", "Registros"],
        label_visibility="collapsed",
    )

    month_options = derive_month_options(datasets["lancamentos"], datasets["aportes"], datasets["receitas"])
    selected_period = st.sidebar.selectbox("Mes analisado", month_options, format_func=format_period)
    budget = st.sidebar.number_input("Limite mensal", min_value=0.0, value=5000.0, step=100.0)

    meta_names = datasets["metas"]["nome_meta"].dropna().tolist()
    selected_goal = st.sidebar.selectbox("Meta principal", meta_names) if meta_names else None

    st.sidebar.markdown("### Simulacao")
    annual_rate = st.sidebar.slider("Rendimento anual", min_value=0.0, max_value=0.25, value=0.12, step=0.005)
    annual_volatility = st.sidebar.slider("Volatilidade", min_value=0.0, max_value=0.40, value=0.05, step=0.01)
    extra_contribution = st.sidebar.slider("Aporte extra mensal", min_value=0, max_value=10000, value=500, step=100)
    monte_carlo_runs = st.sidebar.slider("Rodadas Monte Carlo", min_value=200, max_value=5000, value=1000, step=200)

    return {
        "page": page,
        "selected_period": selected_period,
        "budget": budget,
        "selected_goal": selected_goal,
        "annual_rate": annual_rate,
        "annual_volatility": annual_volatility,
        "extra_contribution": float(extra_contribution),
        "monte_carlo_runs": monte_carlo_runs,
    }


def render_overview_page(datasets: dict[str, pd.DataFrame], controls: dict) -> None:
    render_section_header(
        "Visao geral",
        "Uma leitura executiva do mes com foco no que entrou, no que saiu e no que foi investido.",
    )
    if all(dataset.empty for dataset in datasets.values()):
        render_empty_onboarding()

    summary = monthly_summary(
        datasets["receitas"],
        datasets["lancamentos"],
        datasets["aportes"],
        controls["selected_period"],
    )
    score, score_label = compute_health_score(summary, controls["budget"])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_stat_card("Entradas", format_currency(summary["receita_total"]), "Tudo que entrou no periodo")
    with col2:
        render_stat_card("Gastos", format_currency(summary["gasto_total"]), "Saidas registradas no mes")
    with col3:
        render_stat_card("Investimentos", format_currency(summary["aporte_total"]), "Aportes feitos no periodo")
    with col4:
        render_stat_card("Saldo livre", format_currency(summary["saldo_livre"]), f"Saude financeira: {score}/100 | {score_label}")

    usage = summary["gasto_total"] / controls["budget"] if controls["budget"] > 0 else 0.0
    st.progress(min(max(usage, 0.0), 1.0), text=f"Uso do limite mensal: {usage:.1%}")
    st.info(build_month_insights(summary, controls["budget"]))

    left, right = st.columns([1, 1])
    with left:
        st.plotly_chart(build_expense_category_chart(datasets["lancamentos"], controls["selected_period"]), width="stretch")
    with right:
        st.plotly_chart(build_cashflow_chart(datasets, controls["selected_period"]), width="stretch")

    with st.expander("Abrir analise detalhada"):
        st.plotly_chart(build_expense_trend_chart(datasets["lancamentos"]), width="stretch")
        st.plotly_chart(build_net_worth_chart(datasets["aportes"]), width="stretch")


def render_goals_page(datasets: dict[str, pd.DataFrame], controls: dict) -> None:
    render_section_header(
        "Metas e simulacoes",
        "Acompanhe progresso, valor faltante e janela provavel de atingimento da sua meta principal.",
    )
    if datasets["metas"].empty or controls["selected_goal"] is None:
        st.info("Voce ainda nao cadastrou metas. Crie a primeira na pagina de registros.")
        return

    meta_row = datasets["metas"].loc[datasets["metas"]["nome_meta"] == controls["selected_goal"]].iloc[0]
    progress = compute_goal_progress(meta_row, datasets["aportes"])
    monthly_contribution = average_recent_aportes(datasets["aportes"])

    projection = project_goal(
        current_balance=progress["saldo_atual"],
        monthly_contribution=monthly_contribution,
        target_value=float(meta_row["valor_alvo"]),
        annual_rate=controls["annual_rate"],
        extra_contribution=controls["extra_contribution"],
    )
    simulations = monte_carlo_goal(
        current_balance=progress["saldo_atual"],
        monthly_contribution=monthly_contribution,
        target_value=float(meta_row["valor_alvo"]),
        annual_return=controls["annual_rate"],
        annual_volatility=controls["annual_volatility"],
        extra_contribution=controls["extra_contribution"],
        simulations=controls["monte_carlo_runs"],
    )

    median_months = int(simulations["meses"].quantile(0.50))
    best_case = int(simulations["meses"].quantile(0.10))
    worst_case = int(simulations["meses"].quantile(0.90))
    forecast_date = projection.iloc[-1]["data"].strftime("%m/%Y")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_stat_card("Meta", str(meta_row["nome_meta"]), "Objetivo principal selecionado")
    with col2:
        render_stat_card("Ja guardado", format_currency(progress["saldo_atual"]), "Saldo atual considerado")
    with col3:
        render_stat_card("Quanto falta", format_currency(progress["faltante"]), "Diferenca ate o alvo")
    with col4:
        render_stat_card("Previsao", forecast_date, f"Mediana da simulacao: {median_months} meses")

    st.progress(min(max(progress["progresso"], 0.0), 1.0), text=f"Progresso da meta: {progress['progresso']:.1%}")
    st.info(
        f"Na maior parte dos cenarios, a meta aparece entre {best_case} e {worst_case} meses, "
        f"considerando rendimento anual de {controls['annual_rate']:.1%}."
    )

    proj_chart = px.line(
        projection,
        x="data",
        y="patrimonio",
        markers=True,
        title=f"Evolucao projetada para {meta_row['nome_meta']}",
    )
    proj_chart.add_hline(y=float(meta_row["valor_alvo"]), line_dash="dash", line_color="#F59E0B")
    st.plotly_chart(style_figure(proj_chart), width="stretch")

    with st.expander("Abrir distribuicao da simulacao"):
        hist = px.histogram(simulations, x="meses", nbins=30, title="Distribuicao dos meses para atingir a meta")
        st.plotly_chart(style_figure(hist), width="stretch")

    metas_view = datasets["metas"].copy()
    metas_view["saldo_atual"] = metas_view.apply(
        lambda row: compute_goal_progress(row, datasets["aportes"])["saldo_atual"],
        axis=1,
    )
    metas_view["progresso"] = (metas_view["saldo_atual"] / metas_view["valor_alvo"]).clip(lower=0)
    st.dataframe(
        metas_view[["nome_meta", "valor_alvo", "saldo_atual", "progresso", "data_limite"]],
        width="stretch",
        hide_index=True,
    )


def render_add_forms(store: DataStore) -> None:
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("#### Novo gasto")
            with st.form("form_gasto", clear_on_submit=True):
                data_gasto = st.date_input("Data", value=date.today(), key="gasto_data")
                valor_gasto = st.number_input("Valor", min_value=0.0, step=10.0, key="gasto_valor")
                categoria = st.selectbox("Categoria", CATEGORIAS_GASTO, key="gasto_categoria")
                descricao = st.text_input("Descricao", key="gasto_descricao")
                if st.form_submit_button("Salvar gasto", width="stretch"):
                    store.append(
                        "lancamentos",
                        {
                            "data": pd.Timestamp(data_gasto),
                            "categoria": categoria,
                            "descricao": descricao,
                            "valor": valor_gasto,
                            "responsavel": RESPONSAVEL_PADRAO,
                        },
                    )
                    st.success("Gasto salvo com sucesso.")
                    st.rerun()

        with st.container(border=True):
            st.markdown("#### Nova meta")
            with st.form("form_meta", clear_on_submit=True):
                nome_meta = st.text_input("Nome da meta")
                valor_alvo = st.number_input("Valor alvo", min_value=0.0, step=500.0)
                data_limite = st.date_input("Data limite", value=date.today(), key="meta_data_limite")
                saldo_inicial = st.number_input("Saldo inicial", min_value=0.0, step=500.0)
                if st.form_submit_button("Salvar meta", width="stretch"):
                    if not nome_meta.strip():
                        st.warning("Informe um nome para a meta.")
                    else:
                        store.append(
                            "metas",
                            {
                                "nome_meta": nome_meta.strip(),
                                "valor_alvo": valor_alvo,
                                "data_limite": pd.Timestamp(data_limite),
                                "saldo_inicial": saldo_inicial,
                            },
                        )
                        st.success("Meta salva com sucesso.")
                        st.rerun()

    with col2:
        with st.container(border=True):
            st.markdown("#### Nova receita")
            with st.form("form_receita", clear_on_submit=True):
                data_receita = st.date_input("Data", value=date.today(), key="receita_data")
                valor_receita = st.number_input("Valor", min_value=0.0, step=100.0, key="receita_valor")
                categoria_receita = st.selectbox("Categoria", CATEGORIAS_RECEITA, key="receita_categoria")
                descricao_receita = st.text_input("Descricao", key="receita_descricao")
                if st.form_submit_button("Salvar receita", width="stretch"):
                    store.append(
                        "receitas",
                        {
                            "data": pd.Timestamp(data_receita),
                            "categoria": categoria_receita,
                            "descricao": descricao_receita,
                            "valor": valor_receita,
                            "responsavel": RESPONSAVEL_PADRAO,
                        },
                    )
                    st.success("Receita salva com sucesso.")
                    st.rerun()

        with st.container(border=True):
            st.markdown("#### Novo investimento")
            with st.form("form_aporte", clear_on_submit=True):
                data_aporte = st.date_input("Data", value=date.today(), key="aporte_data")
                valor_aporte = st.number_input("Valor", min_value=0.0, step=50.0, key="aporte_valor")
                tipo_aporte = st.selectbox("Tipo", TIPOS_APORTE, key="aporte_tipo")
                if st.form_submit_button("Salvar investimento", width="stretch"):
                    store.append(
                        "aportes",
                        {
                            "data": pd.Timestamp(data_aporte),
                            "valor": valor_aporte,
                            "tipo": tipo_aporte,
                        },
                    )
                    st.success("Investimento salvo com sucesso.")
                    st.rerun()


def render_dataset_editor(store: DataStore, dataset_name: str, df: pd.DataFrame, title: str) -> None:
    st.markdown(f"#### {title}")
    st.caption("Edite, adicione ou exclua registros com seguranca.")
    base_df = attach_row_ids(df)
    filtered_df = apply_editor_filters(base_df, dataset_name)
    editor_df = prepare_editor_dataframe(filtered_df, dataset_name)

    edited = st.data_editor(
        editor_df,
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        column_config={**editor_column_config(dataset_name), "_row_id": None},
        key=f"editor_{dataset_name}",
    )

    col1, col2 = st.columns([1, 1])
    if col1.button(f"Salvar {title}", key=f"save_{dataset_name}", width="stretch"):
        cleaned = coerce_editor_dataframe(edited.dropna(how="all"), dataset_name)
        if dataset_name in {"lancamentos", "receitas"} and "responsavel" in cleaned.columns:
            cleaned["responsavel"] = RESPONSAVEL_PADRAO
        is_valid, message = validate_editor_dataframe(cleaned, dataset_name)
        if not is_valid:
            st.error(message)
        else:
            final_df = merge_edited_subset(base_df, filtered_df, cleaned)
            final_df = final_df.drop(columns=["_row_id"], errors="ignore")
            if dataset_name in {"lancamentos", "receitas"} and "responsavel" in final_df.columns:
                final_df["responsavel"] = RESPONSAVEL_PADRAO
            store.write(dataset_name, final_df)
            st.success(f"{title} atualizado com sucesso.")
            st.rerun()

    delete_options = build_delete_options(filtered_df, dataset_name)
    if delete_options:
        selected_label = col2.selectbox("Excluir registro", list(delete_options.keys()), key=f"delete_label_{dataset_name}")
        confirm_delete = st.checkbox("Confirmo a exclusao", key=f"confirm_delete_{dataset_name}")
        if st.button(f"Excluir de {title}", key=f"delete_{dataset_name}", width="stretch"):
            if not confirm_delete:
                st.warning("Marque a confirmacao antes de excluir.")
            else:
                selected_id = delete_options[selected_label]
                final_df = base_df[base_df["_row_id"] != selected_id].drop(columns=["_row_id"], errors="ignore")
                store.write(dataset_name, final_df)
                st.success("Registro excluido.")
                st.rerun()


def render_records_page(store: DataStore, datasets: dict[str, pd.DataFrame]) -> None:
    render_section_header(
        "Registros e operacao",
        "A area operacional do painel. Aqui voce cadastra, revisa e corrige tudo o que alimenta a plataforma.",
    )
    subtab_add, subtab_manage = st.tabs(["Adicionar registros", "Gerenciar base"])

    with subtab_add:
        render_add_forms(store)

    with subtab_manage:
        selected_table = st.segmented_control(
            "Base selecionada",
            options=["Gastos", "Receitas", "Investimentos", "Metas"],
            default="Gastos",
        )
        if selected_table == "Gastos":
            render_dataset_editor(store, "lancamentos", datasets["lancamentos"].sort_values("data", ascending=False), "Gastos")
        elif selected_table == "Receitas":
            render_dataset_editor(store, "receitas", datasets["receitas"].sort_values("data", ascending=False), "Receitas")
        elif selected_table == "Investimentos":
            render_dataset_editor(store, "aportes", datasets["aportes"].sort_values("data", ascending=False), "Investimentos")
        else:
            render_dataset_editor(store, "metas", datasets["metas"].sort_values("data_limite"), "Metas")

        with st.expander("Qualidade dos dados e observacoes"):
            rows = []
            for name, frame in datasets.items():
                rows.append(
                    {
                        "dataset": name,
                        "linhas": len(frame),
                        "datas_vazias": int(frame.filter(regex="data").isna().sum().sum()),
                        "valores_negativos": int((frame.select_dtypes(include=["number"]) < 0).sum().sum()),
                    }
                )
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def main() -> None:
    render_page_header()
    store = get_data_store()
    datasets = load_all_data(store)
    controls = render_sidebar(datasets)

    if controls["page"] == "Visao geral":
        render_overview_page(datasets, controls)
    elif controls["page"] == "Metas":
        render_goals_page(datasets, controls)
    else:
        render_records_page(store, datasets)


if __name__ == "__main__":
    main()
