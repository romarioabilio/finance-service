from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from finance_app.analytics import (
    average_recent_aportes,
    build_insights,
    budget_view,
    compute_goal_progress,
    compute_health_score,
    current_month_label,
    format_currency,
    latest_transactions,
    monthly_summary,
    monte_carlo_goal,
    net_worth,
    project_goal,
    recurring_schedule,
)
from finance_app.charts import budget_bullet, cashflow_bars, expense_donut, expense_history, goal_distribution, goal_projection, net_worth_line
from finance_app.config import (
    CATEGORIAS_GASTO,
    CATEGORIAS_RECEITA,
    DATASETS,
    RESPONSAVEL_PADRAO,
    STATUS_META,
    STATUS_RECORRENCIA,
    TIPOS_APORTE,
    TIPOS_RECORRENCIA,
)
from finance_app.data import DataStore


def render_page_header() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-kicker">Financeiro pessoal premium</div>
            <div class="hero-title">Um cockpit financeiro completo, operável e bonito.</div>
            <p class="hero-copy">Inspirado na clareza de produto que apps financeiros modernos buscam: foco no agora, no que vem pela frente e em decisões práticas.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="section-shell">
            <div class="section-title">{title}</div>
            <div class="section-copy">{copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_card(label: str, value: str, foot: str) -> None:
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


def empty_onboarding() -> None:
    st.markdown(
        """
        <div class="feature-grid">
            <div class="feature-card">
                <div class="feature-badge">1</div>
                <div class="feature-title">Cadastre entradas e saídas</div>
                <p class="feature-copy">Sem isso, o painel não consegue refletir seu fluxo real de caixa nem seus padrões de consumo.</p>
            </div>
            <div class="feature-card">
                <div class="feature-badge">2</div>
                <div class="feature-title">Defina orçamentos por categoria</div>
                <p class="feature-copy">Isso ativa comparações relevantes, alertas por categoria e um painel de uso muito mais inteligente.</p>
            </div>
            <div class="feature-card">
                <div class="feature-badge">3</div>
                <div class="feature-title">Crie metas e recorrências</div>
                <p class="feature-copy">Metas tornam o painel estratégico; recorrências transformam sua visão mensal em algo realmente previsível.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_controls(datasets: dict[str, pd.DataFrame], month_options: list[pd.Period]) -> dict:
    st.sidebar.markdown("### Navegacao")
    page = st.sidebar.radio("Pagina", ["Visao geral", "Orcamentos", "Metas", "Recorrencias", "Insights", "Registros"], label_visibility="collapsed")

    st.sidebar.markdown("### Filtros")
    selected_period = st.sidebar.selectbox("Mes analisado", month_options)
    monthly_limit = st.sidebar.number_input("Limite mensal geral", min_value=0.0, value=5000.0, step=100.0)

    meta_names = datasets["metas"]["nome_meta"].dropna().tolist()
    selected_goal = st.sidebar.selectbox("Meta principal", meta_names) if meta_names else None

    st.sidebar.markdown("### Simulacao")
    annual_rate = st.sidebar.slider("Rendimento anual", min_value=0.0, max_value=0.30, value=0.12, step=0.005)
    annual_volatility = st.sidebar.slider("Volatilidade", min_value=0.0, max_value=0.50, value=0.05, step=0.01)
    extra_contribution = st.sidebar.slider("Aporte extra mensal", min_value=0, max_value=10000, value=500, step=100)
    monte_carlo_runs = st.sidebar.slider("Rodadas Monte Carlo", min_value=200, max_value=5000, value=1200, step=200)

    return {
        "page": page,
        "selected_period": selected_period,
        "monthly_limit": monthly_limit,
        "selected_goal": selected_goal,
        "annual_rate": annual_rate,
        "annual_volatility": annual_volatility,
        "extra_contribution": float(extra_contribution),
        "monte_carlo_runs": monte_carlo_runs,
    }


def render_overview(datasets: dict[str, pd.DataFrame], controls: dict) -> None:
    section_header("Visão geral executiva", "Acompanhamento claro do mês, leitura do patrimônio e atividade recente em um só lugar.")
    if all(dataset.empty for dataset in datasets.values()):
        empty_onboarding()

    summary = monthly_summary(datasets, controls["selected_period"])
    score, score_label = compute_health_score(summary, controls["monthly_limit"])
    patrimony = net_worth(datasets)
    recent = latest_transactions(datasets)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        stat_card("Entradas", format_currency(summary["receita_total"]), "Receitas registradas no mês")
    with col2:
        stat_card("Saídas", format_currency(summary["gasto_total"]), "Gastos lançados no mês")
    with col3:
        stat_card("Investido", format_currency(summary["aporte_total"]), "Aportes feitos no período")
    with col4:
        stat_card("Patrimônio", format_currency(patrimony), f"Saúde financeira: {score}/100 | {score_label}")

    if controls["monthly_limit"] > 0:
        usage = summary["gasto_total"] / controls["monthly_limit"]
        st.progress(min(max(usage, 0.0), 1.0), text=f"Uso do limite mensal: {usage:.1%}")

    for message in build_insights(datasets, controls["selected_period"], controls["monthly_limit"]):
        st.info(message)

    left, right = st.columns(2)
    with left:
        st.plotly_chart(expense_donut(datasets["lancamentos"], controls["selected_period"]), width="stretch")
    with right:
        st.plotly_chart(cashflow_bars(datasets["receitas"], datasets["lancamentos"], datasets["aportes"], controls["selected_period"]), width="stretch")

    left, right = st.columns([1.5, 1])
    with left:
        st.plotly_chart(expense_history(datasets["lancamentos"]), width="stretch")
    with right:
        st.plotly_chart(net_worth_line(datasets["aportes"], datasets["metas"]), width="stretch")

    section_header("Atividade recente", "Os últimos movimentos do sistema para você revisar rapidamente.")
    st.dataframe(recent, width="stretch", hide_index=True)


def render_budgets(datasets: dict[str, pd.DataFrame], controls: dict) -> None:
    section_header("Planejamento de orçamento", "Controle o limite por categoria e acompanhe a execução do mês.")
    budget_df = budget_view(datasets, controls["selected_period"])
    top1, top2 = st.columns([1.2, 1])
    with top1:
        st.plotly_chart(budget_bullet(budget_df), width="stretch")
    with top2:
        over = budget_df[budget_df["disponivel"] < 0]
        near = budget_df[(budget_df["disponivel"] >= 0) & (budget_df["uso"] >= 0.85)]
        st.metric("Categorias orçadas", str(len(budget_df)))
        st.metric("Estouradas", str(len(over)))
        st.metric("Em alerta", str(len(near)))
        st.caption("Use a área de registros para criar ou ajustar o orçamento por categoria.")

    st.dataframe(budget_df, width="stretch", hide_index=True)


def render_goals(datasets: dict[str, pd.DataFrame], controls: dict) -> None:
    section_header("Metas e projeções", "Veja quanto já foi construído, quanto falta e quando a meta tende a ser atingida.")
    if datasets["metas"].empty or controls["selected_goal"] is None:
        st.info("Você ainda não cadastrou metas. Crie a primeira na área de registros.")
        return

    meta_row = datasets["metas"].loc[datasets["metas"]["nome_meta"] == controls["selected_goal"]].iloc[0]
    progress = compute_goal_progress(meta_row, datasets["aportes"])
    monthly_contribution = average_recent_aportes(datasets["aportes"])
    projection = project_goal(progress["saldo_atual"], monthly_contribution, float(meta_row["valor_alvo"]), controls["annual_rate"], controls["extra_contribution"])
    sims = monte_carlo_goal(progress["saldo_atual"], monthly_contribution, float(meta_row["valor_alvo"]), controls["annual_rate"], controls["annual_volatility"], controls["extra_contribution"], controls["monte_carlo_runs"])

    median_months = int(sims["meses"].quantile(0.50))
    best_case = int(sims["meses"].quantile(0.10))
    worst_case = int(sims["meses"].quantile(0.90))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        stat_card("Meta", str(meta_row["nome_meta"]), f"Status: {meta_row['status']}")
    with col2:
        stat_card("Saldo atual", format_currency(progress["saldo_atual"]), "Somando saldo inicial e aportes")
    with col3:
        stat_card("Faltante", format_currency(progress["faltante"]), "Distância até o alvo")
    with col4:
        stat_card("Faixa provável", f"{best_case}-{worst_case} meses", f"Mediana: {median_months} meses")

    st.progress(min(max(progress["progresso"], 0.0), 1.0), text=f"Progresso da meta: {progress['progresso']:.1%}")
    st.plotly_chart(goal_projection(projection, float(meta_row["valor_alvo"]), f"Projeção para {meta_row['nome_meta']}"), width="stretch")
    st.plotly_chart(goal_distribution(sims), width="stretch")

    metas_view = datasets["metas"].copy()
    metas_view["saldo_atual"] = metas_view.apply(lambda row: compute_goal_progress(row, datasets["aportes"])["saldo_atual"], axis=1)
    metas_view["progresso"] = (metas_view["saldo_atual"] / metas_view["valor_alvo"]).clip(lower=0)
    st.dataframe(metas_view, width="stretch", hide_index=True)


def render_recurring(datasets: dict[str, pd.DataFrame]) -> None:
    section_header("Recorrências e previsibilidade", "Mantenha assinaturas, despesas fixas e entradas previstas sob controle.")
    recurring = recurring_schedule(datasets["recorrencias"])
    col1, col2, col3 = st.columns(3)
    with col1:
        stat_card("Recorrências ativas", str(len(recurring)), "Itens com execução futura prevista")
    with col2:
        total_out = recurring[recurring["tipo"] == "Gasto"]["valor"].sum() if not recurring.empty else 0.0
        stat_card("Saídas recorrentes", format_currency(float(total_out)), "Base mensal previsível")
    with col3:
        total_in = recurring[recurring["tipo"] == "Receita"]["valor"].sum() if not recurring.empty else 0.0
        stat_card("Entradas recorrentes", format_currency(float(total_in)), "Receitas regulares mapeadas")
    st.dataframe(recurring, width="stretch", hide_index=True)


def render_insights(datasets: dict[str, pd.DataFrame], controls: dict) -> None:
    section_header("Insights e reflexão", "Uma leitura mais analítica inspirada nas experiências modernas de gestão financeira.")
    summary = monthly_summary(datasets, controls["selected_period"])
    score, score_label = compute_health_score(summary, controls["monthly_limit"])
    st.metric("Índice de saúde financeira", f"{score}/100", score_label)

    spend = datasets["lancamentos"].copy()
    if not spend.empty:
        ranking = spend.groupby("categoria", as_index=False)["valor"].sum().sort_values("valor", ascending=False).head(10)
        st.dataframe(ranking, width="stretch", hide_index=True)
    else:
        st.info("Cadastre movimentações para liberar rankings e comparativos.")

    st.markdown("#### Reflexões sugeridas")
    for line in build_insights(datasets, controls["selected_period"], controls["monthly_limit"]):
        st.write(f"- {line}")


def editor_config(dataset_name: str) -> dict:
    if dataset_name == "lancamentos":
        return {
            "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "categoria": st.column_config.SelectboxColumn("Categoria", options=CATEGORIAS_GASTO),
            "descricao": st.column_config.TextColumn("Descricao"),
            "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "responsavel": None,
        }
    if dataset_name == "receitas":
        return {
            "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "categoria": st.column_config.SelectboxColumn("Categoria", options=CATEGORIAS_RECEITA),
            "descricao": st.column_config.TextColumn("Descricao"),
            "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "responsavel": None,
        }
    if dataset_name == "aportes":
        return {
            "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "tipo": st.column_config.SelectboxColumn("Tipo", options=TIPOS_APORTE),
        }
    if dataset_name == "metas":
        return {
            "nome_meta": st.column_config.TextColumn("Nome da meta"),
            "valor_alvo": st.column_config.NumberColumn("Valor alvo", format="R$ %.2f"),
            "data_limite": st.column_config.DateColumn("Data limite", format="DD/MM/YYYY"),
            "saldo_inicial": st.column_config.NumberColumn("Saldo inicial", format="R$ %.2f"),
            "prioridade": st.column_config.NumberColumn("Prioridade"),
            "status": st.column_config.SelectboxColumn("Status", options=STATUS_META),
        }
    if dataset_name == "orcamentos":
        return {
            "mes": st.column_config.TextColumn("Mes", help="Use o formato YYYY-MM"),
            "categoria": st.column_config.SelectboxColumn("Categoria", options=CATEGORIAS_GASTO),
            "orcado": st.column_config.NumberColumn("Orçado", format="R$ %.2f"),
            "alerta": st.column_config.NumberColumn("Alerta %", format="%.0f"),
        }
    return {
        "tipo": st.column_config.SelectboxColumn("Tipo", options=TIPOS_RECORRENCIA),
        "categoria": st.column_config.TextColumn("Categoria"),
        "descricao": st.column_config.TextColumn("Descricao"),
        "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        "dia_vencimento": st.column_config.NumberColumn("Dia", min_value=1, max_value=28),
        "status": st.column_config.SelectboxColumn("Status", options=STATUS_RECORRENCIA),
        "observacao": st.column_config.TextColumn("Observacao"),
    }


def save_dataset(store: DataStore, dataset_name: str, edited_df: pd.DataFrame) -> tuple[bool, str]:
    config = DATASETS[dataset_name]
    cleaned = edited_df.dropna(how="all").copy()
    for column in config.get("date_columns", []):
        cleaned[column] = pd.to_datetime(cleaned[column], errors="coerce")
    for column in config.get("numeric_columns", []):
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    if dataset_name in {"lancamentos", "receitas"}:
        cleaned["responsavel"] = RESPONSAVEL_PADRAO
    for column in config["columns"]:
        if column not in cleaned.columns:
            cleaned[column] = None
    if cleaned[config["columns"]].isna().any().any():
        return False, "Há campos inválidos ou vazios. Revise antes de salvar."
    store.write(dataset_name, cleaned[config["columns"]])
    return True, "Base atualizada com sucesso."


def render_records(store: DataStore, datasets: dict[str, pd.DataFrame]) -> None:
    section_header("Registros e operação", "Tudo o que alimenta o sistema pode ser criado, revisado e ajustado dentro da própria aplicação.")
    add_tab, manage_tab = st.tabs(["Adicionar", "Gerenciar"])

    with add_tab:
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.markdown("#### Novo gasto")
                with st.form("add_gasto", clear_on_submit=True):
                    data = st.date_input("Data", value=date.today(), key="add_gasto_data")
                    categoria = st.selectbox("Categoria", CATEGORIAS_GASTO)
                    descricao = st.text_input("Descricao", key="add_gasto_desc")
                    valor = st.number_input("Valor", min_value=0.0, step=10.0, key="add_gasto_valor")
                    if st.form_submit_button("Salvar gasto", width="stretch"):
                        store.append("lancamentos", {"data": pd.Timestamp(data), "categoria": categoria, "descricao": descricao, "valor": valor, "responsavel": RESPONSAVEL_PADRAO})
                        st.success("Gasto salvo.")
                        st.rerun()

            with st.container(border=True):
                st.markdown("#### Orçamento por categoria")
                with st.form("add_budget", clear_on_submit=True):
                    mes = st.text_input("Mes (YYYY-MM)", value=pd.Timestamp.today().to_period("M").strftime("%Y-%m"))
                    categoria = st.selectbox("Categoria do orçamento", CATEGORIAS_GASTO, key="budget_cat")
                    orcado = st.number_input("Valor orçado", min_value=0.0, step=100.0)
                    alerta = st.number_input("Alerta em %", min_value=1.0, max_value=100.0, value=85.0)
                    if st.form_submit_button("Salvar orçamento", width="stretch"):
                        store.append("orcamentos", {"mes": mes, "categoria": categoria, "orcado": orcado, "alerta": alerta})
                        st.success("Orçamento salvo.")
                        st.rerun()

            with st.container(border=True):
                st.markdown("#### Nova meta")
                with st.form("add_goal", clear_on_submit=True):
                    nome = st.text_input("Nome da meta")
                    valor_alvo = st.number_input("Valor alvo", min_value=0.0, step=500.0)
                    data_limite = st.date_input("Data limite", value=date.today())
                    saldo_inicial = st.number_input("Saldo inicial", min_value=0.0, step=100.0)
                    prioridade = st.number_input("Prioridade", min_value=1.0, max_value=5.0, value=3.0)
                    status = st.selectbox("Status", STATUS_META)
                    if st.form_submit_button("Salvar meta", width="stretch"):
                        store.append("metas", {"nome_meta": nome, "valor_alvo": valor_alvo, "data_limite": pd.Timestamp(data_limite), "saldo_inicial": saldo_inicial, "prioridade": prioridade, "status": status})
                        st.success("Meta salva.")
                        st.rerun()
        with col2:
            with st.container(border=True):
                st.markdown("#### Nova receita")
                with st.form("add_receita", clear_on_submit=True):
                    data = st.date_input("Data", value=date.today(), key="add_receita_data")
                    categoria = st.selectbox("Categoria", CATEGORIAS_RECEITA)
                    descricao = st.text_input("Descricao", key="add_receita_desc")
                    valor = st.number_input("Valor", min_value=0.0, step=100.0, key="add_receita_valor")
                    if st.form_submit_button("Salvar receita", width="stretch"):
                        store.append("receitas", {"data": pd.Timestamp(data), "categoria": categoria, "descricao": descricao, "valor": valor, "responsavel": RESPONSAVEL_PADRAO})
                        st.success("Receita salva.")
                        st.rerun()

            with st.container(border=True):
                st.markdown("#### Novo investimento")
                with st.form("add_aporte", clear_on_submit=True):
                    data = st.date_input("Data", value=date.today(), key="add_aporte_data")
                    tipo = st.selectbox("Tipo", TIPOS_APORTE)
                    valor = st.number_input("Valor", min_value=0.0, step=50.0, key="add_aporte_valor")
                    if st.form_submit_button("Salvar investimento", width="stretch"):
                        store.append("aportes", {"data": pd.Timestamp(data), "valor": valor, "tipo": tipo})
                        st.success("Investimento salvo.")
                        st.rerun()

            with st.container(border=True):
                st.markdown("#### Nova recorrência")
                with st.form("add_recorrencia", clear_on_submit=True):
                    tipo = st.selectbox("Tipo", TIPOS_RECORRENCIA)
                    categoria = st.text_input("Categoria")
                    descricao = st.text_input("Descricao", key="rec_desc")
                    valor = st.number_input("Valor", min_value=0.0, step=10.0, key="rec_valor")
                    dia = st.number_input("Dia do mês", min_value=1, max_value=28, value=5)
                    status = st.selectbox("Status", STATUS_RECORRENCIA)
                    observacao = st.text_area("Observacao")
                    if st.form_submit_button("Salvar recorrência", width="stretch"):
                        store.append("recorrencias", {"tipo": tipo, "categoria": categoria, "descricao": descricao, "valor": valor, "dia_vencimento": dia, "status": status, "observacao": observacao})
                        st.success("Recorrência salva.")
                        st.rerun()

    with manage_tab:
        dataset_labels = {
            "Gastos": "lancamentos",
            "Receitas": "receitas",
            "Investimentos": "aportes",
            "Metas": "metas",
            "Orçamentos": "orcamentos",
            "Recorrências": "recorrencias",
        }
        selected = st.segmented_control("Base selecionada", options=list(dataset_labels.keys()), default="Gastos")
        dataset_name = dataset_labels[selected]
        df = datasets[dataset_name].copy()
        if dataset_name in {"lancamentos", "receitas", "aportes"} and not df.empty:
            df = df.sort_values("data", ascending=False)
        edited = st.data_editor(df, width="stretch", hide_index=True, num_rows="dynamic", column_config=editor_config(dataset_name))
        if st.button(f"Salvar alterações em {selected}", width="stretch"):
            ok, message = save_dataset(store, dataset_name, edited)
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
