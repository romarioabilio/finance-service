from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from finance_app.config import COLOR_SCALE


def empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[{"text": "Sem dados ainda", "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5, "showarrow": False, "font": {"size": 16, "color": "#64748B"}}],
        margin={"l": 20, "r": 20, "t": 56, "b": 20},
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


def expense_donut(lancamentos: pd.DataFrame, period: pd.Period) -> go.Figure:
    filtered = lancamentos[lancamentos["data"].dt.to_period("M") == period]
    grouped = filtered.groupby("categoria", as_index=False)["valor"].sum()
    if grouped.empty:
        return empty_figure("Distribuicao dos gastos")
    fig = px.pie(grouped, names="categoria", values="valor", hole=0.62, title="Distribuicao dos gastos", color_discrete_sequence=COLOR_SCALE)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return style_figure(fig)


def cashflow_bars(receitas: pd.DataFrame, lancamentos: pd.DataFrame, aportes: pd.DataFrame, period: pd.Period) -> go.Figure:
    receipts = receitas[receitas["data"].dt.to_period("M") == period]["valor"].sum()
    expenses = lancamentos[lancamentos["data"].dt.to_period("M") == period]["valor"].sum()
    invests = aportes[aportes["data"].dt.to_period("M") == period]["valor"].sum()
    df = pd.DataFrame({"tipo": ["Entradas", "Gastos", "Investimentos"], "valor": [receipts, expenses, invests]})
    if df["valor"].sum() == 0:
        return empty_figure("Fluxo do mes")
    fig = px.bar(
        df,
        x="tipo",
        y="valor",
        color="tipo",
        title="Fluxo do mes",
        color_discrete_map={"Entradas": "#16A34A", "Gastos": "#DC2626", "Investimentos": "#2563EB"},
    )
    fig.update_layout(showlegend=False)
    return style_figure(fig)


def expense_history(lancamentos: pd.DataFrame) -> go.Figure:
    if lancamentos.empty:
        return empty_figure("Historico de gastos")
    trend = (
        lancamentos.assign(mes=lancamentos["data"].dt.to_period("M").astype(str))
        .groupby(["mes", "categoria"], as_index=False)["valor"]
        .sum()
    )
    fig = px.bar(trend, x="mes", y="valor", color="categoria", title="Historico de gastos por categoria", color_discrete_sequence=COLOR_SCALE)
    return style_figure(fig)


def net_worth_line(aportes: pd.DataFrame, metas: pd.DataFrame) -> go.Figure:
    if aportes.empty and metas.empty:
        return empty_figure("Patrimonio investido")
    patrimonio = aportes.sort_values("data").copy()
    patrimonio["patrimonio"] = patrimonio["valor"].cumsum() + float(metas["saldo_inicial"].sum() if not metas.empty else 0.0)
    if patrimonio.empty:
        patrimonio = pd.DataFrame({"data": [pd.Timestamp.today().normalize()], "patrimonio": [float(metas["saldo_inicial"].sum())]})
    fig = px.line(patrimonio, x="data", y="patrimonio", markers=True, title="Patrimonio investido")
    fig.update_traces(line_color="#1D4ED8", line_width=3)
    return style_figure(fig)


def budget_bullet(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return empty_figure("Uso dos orcamentos")
    fig = px.bar(df, x="uso", y="categoria", orientation="h", title="Uso dos orcamentos por categoria", color="uso", color_continuous_scale=["#16A34A", "#F59E0B", "#DC2626"])
    fig.update_layout(coloraxis_showscale=False)
    return style_figure(fig)


def goal_projection(projection: pd.DataFrame, target_value: float, title: str) -> go.Figure:
    if projection.empty:
        return empty_figure(title)
    fig = px.line(projection, x="data", y="patrimonio", markers=True, title=title)
    fig.add_hline(y=target_value, line_dash="dash", line_color="#F59E0B")
    return style_figure(fig)


def goal_distribution(simulations: pd.DataFrame) -> go.Figure:
    if simulations.empty:
        return empty_figure("Distribuicao da simulacao")
    fig = px.histogram(simulations, x="meses", nbins=30, title="Distribuicao dos meses para atingir a meta", color_discrete_sequence=["#2563EB"])
    return style_figure(fig)
