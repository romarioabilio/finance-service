from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from finance_app.config import MESES_PT


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


def monthly_summary(datasets: dict[str, pd.DataFrame], period: pd.Period) -> dict:
    receitas = datasets["receitas"]
    lancamentos = datasets["lancamentos"]
    aportes = datasets["aportes"]
    receitas_mes = receitas[receitas["data"].dt.to_period("M") == period]
    gastos_mes = lancamentos[lancamentos["data"].dt.to_period("M") == period]
    aportes_mes = aportes[aportes["data"].dt.to_period("M") == period]

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
        "transacoes": len(receitas_mes) + len(gastos_mes) + len(aportes_mes),
    }


def compute_health_score(summary: dict, monthly_limit: float) -> tuple[int, str]:
    score = 42
    income = summary["receita_total"]
    expenses = summary["gasto_total"]
    investments = summary["aporte_total"]

    if monthly_limit > 0:
        usage = expenses / monthly_limit
        if usage <= 0.8:
            score += 20
        elif usage <= 1:
            score += 8
        else:
            score -= 14

    if income > 0:
        savings = investments / income
        expense_ratio = expenses / income
        if savings >= 0.25:
            score += 22
        elif savings >= 0.15:
            score += 14
        elif savings >= 0.08:
            score += 8

        if expense_ratio <= 0.6:
            score += 14
        elif expense_ratio >= 0.9:
            score -= 10

    score = max(0, min(100, score))
    if score >= 80:
        return score, "Excelente"
    if score >= 65:
        return score, "Boa"
    if score >= 45:
        return score, "Atencao"
    return score, "Critica"


def build_insights(datasets: dict[str, pd.DataFrame], period: pd.Period, monthly_limit: float) -> list[str]:
    summary = monthly_summary(datasets, period)
    messages: list[str] = []
    if summary["receita_total"] <= 0:
        messages.append("Cadastre suas receitas para liberar uma leitura financeira completa.")
    if summary["gasto_total"] <= 0:
        messages.append("Voce ainda nao registrou gastos neste mes.")
    if monthly_limit > 0 and summary["gasto_total"] > monthly_limit:
        messages.append(f"Seus gastos passaram do limite em {format_currency(summary['gasto_total'] - monthly_limit)}.")
    if summary["receita_total"] > 0:
        messages.append(f"Savings rate atual: {summary['savings_rate']:.1f}%.")

    gastos_mes = datasets["lancamentos"][datasets["lancamentos"]["data"].dt.to_period("M") == period]
    if not gastos_mes.empty:
        top_category = gastos_mes.groupby("categoria")["valor"].sum().sort_values(ascending=False).head(1)
        if not top_category.empty:
            messages.append(f"Maior peso do mes: {top_category.index[0]} com {format_currency(float(top_category.iloc[0]))}.")
    return messages


def budget_view(datasets: dict[str, pd.DataFrame], period: pd.Period) -> pd.DataFrame:
    budgets = datasets["orcamentos"].copy()
    spends = datasets["lancamentos"].copy()
    budgets = budgets[budgets["mes"].fillna("") == str(period)]
    spend_period = spends[spends["data"].dt.to_period("M") == period]
    spent_by_category = spend_period.groupby("categoria", as_index=False)["valor"].sum().rename(columns={"valor": "gasto"})
    merged = budgets.merge(spent_by_category, on="categoria", how="left")
    merged["gasto"] = merged["gasto"].fillna(0.0)
    merged["disponivel"] = merged["orcado"] - merged["gasto"]
    merged["uso"] = np.where(merged["orcado"] > 0, merged["gasto"] / merged["orcado"], 0.0)
    return merged.sort_values(["uso", "categoria"], ascending=[False, True])


def recurring_schedule(recorrencias: pd.DataFrame) -> pd.DataFrame:
    if recorrencias.empty:
        return recorrencias.copy()
    active = recorrencias[recorrencias["status"] == "Ativa"].copy()
    today = pd.Timestamp.today().normalize()
    current_month = today.month
    current_year = today.year
    next_dates = []
    for _, row in active.iterrows():
        day = int(max(1, min(28, row["dia_vencimento"])))
        next_dates.append(pd.Timestamp(year=current_year, month=current_month, day=day))
    active["proxima_execucao"] = next_dates
    active.loc[active["proxima_execucao"] < today, "proxima_execucao"] = active.loc[
        active["proxima_execucao"] < today, "proxima_execucao"
    ] + pd.offsets.MonthBegin(1)
    return active.sort_values("proxima_execucao")


def net_worth(datasets: dict[str, pd.DataFrame]) -> float:
    aportes = float(datasets["aportes"]["valor"].sum())
    metas = datasets["metas"]
    saldo_inicial = float(metas["saldo_inicial"].sum()) if not metas.empty else 0.0
    return aportes + saldo_inicial


def latest_transactions(datasets: dict[str, pd.DataFrame], limit: int = 8) -> pd.DataFrame:
    expenses = datasets["lancamentos"][["data", "categoria", "descricao", "valor"]].copy()
    expenses["tipo"] = "Gasto"
    income = datasets["receitas"][["data", "categoria", "descricao", "valor"]].copy()
    income["tipo"] = "Receita"
    invests = datasets["aportes"][["data", "tipo", "tipo", "valor"]].copy()
    invests.columns = ["data", "categoria", "descricao", "valor"]
    invests["tipo"] = "Investimento"
    combined = pd.concat([expenses, income, invests], ignore_index=True)
    if combined.empty:
        return combined
    return combined.sort_values("data", ascending=False).head(limit)


def project_goal(current_balance: float, monthly_contribution: float, target_value: float, annual_rate: float, extra_contribution: float, max_months: int = 240) -> pd.DataFrame:
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


def monte_carlo_goal(current_balance: float, monthly_contribution: float, target_value: float, annual_return: float, annual_volatility: float, extra_contribution: float, simulations: int, max_months: int = 240) -> pd.DataFrame:
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
    return {
        "saldo_atual": current_balance,
        "faltante": target - current_balance,
        "progresso": current_balance / target if target > 0 else 0.0,
    }


def average_recent_aportes(aportes: pd.DataFrame) -> float:
    if aportes.empty:
        return 0.0
    grouped = (
        aportes.sort_values("data")
        .assign(periodo=lambda frame: frame["data"].dt.to_period("M"))
        .groupby("periodo", as_index=False)["valor"]
        .sum()
        .tail(3)
    )
    if grouped.empty:
        return 0.0
    return float(grouped["valor"].mean())


def current_month_label() -> str:
    today = date.today()
    return f"{MESES_PT[today.month]}/{today.year}"
