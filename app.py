from __future__ import annotations

from finance_app.analytics import derive_month_options
from finance_app.data import DataStore, load_all_data
from finance_app.styles import inject_styles
from finance_app.views import (
    render_budgets,
    render_goals,
    render_insights,
    render_overview,
    render_page_header,
    render_records,
    render_recurring,
    sidebar_controls,
)
import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Finance Service", page_icon="FS", layout="wide")
    inject_styles()
    render_page_header()
    store = DataStore.build()
    datasets = load_all_data(store)
    month_options = derive_month_options(datasets["lancamentos"], datasets["receitas"], datasets["aportes"])
    controls = sidebar_controls(datasets, month_options)

    page = controls["page"]
    if page == "Visao geral":
        render_overview(datasets, controls)
    elif page == "Orcamentos":
        render_budgets(datasets, controls)
    elif page == "Metas":
        render_goals(datasets, controls)
    elif page == "Recorrencias":
        render_recurring(datasets)
    elif page == "Insights":
        render_insights(datasets, controls)
    else:
        render_records(store, datasets)


if __name__ == "__main__":
    main()
