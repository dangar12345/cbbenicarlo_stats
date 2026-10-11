"""Vista: Análisis de Cuartos."""
import os
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from charts import style_fig, chart_kwargs
from components import _html_plano, miles, truncar_nombre, hito_badge


def render(ctx):
    # Datos compartidos (inyectados por app.py)
    df_partidos = ctx['df_partidos']
    df_cuartos = ctx['df_cuartos']
    df_jugadores = ctx['df_jugadores']
    cat_jugadores = ctx['cat_jugadores']
    cat_equipos = ctx['cat_equipos']
    df_temporadas = ctx['df_temporadas']
    st.markdown("## Análisis de Rendimiento por Cuarto")
    st.caption("Desglose táctico de fortaleza y vulnerabilidad en 1Q, 2Q, 3Q y 4Q.")

    temporadas_q = ["Todas las temporadas"] + sorted(df_partidos['temporada'].unique().tolist(), reverse=True)
    sel_q_season = st.selectbox("Temporada", temporadas_q, index=0)

    if sel_q_season != "Todas las temporadas":
        partidos_q_ids = df_partidos.loc[df_partidos['temporada'] == sel_q_season, 'partido_id']
    else:
        partidos_q_ids = df_partidos['partido_id']

    cuartos_beni = df_cuartos[(df_cuartos['es_benicarlo'] == 1) & (df_cuartos['partido_id'].isin(partidos_q_ids))].copy()
    cuartos_rival = df_cuartos[(df_cuartos['es_benicarlo'] == 0) & (df_cuartos['partido_id'].isin(partidos_q_ids))].copy()

    merged_q = pd.merge(
        cuartos_beni,
        cuartos_rival,
        on='partido_id',
        suffixes=('_beni', '_rival')
    )

    if merged_q.empty:
        scope = f"la temporada {sel_q_season}" if sel_q_season != "Todas las temporadas" else "la selección actual"
        st.warning(f"No hay datos de parciales para {scope}.")
        st.stop()

    st.caption(f"Basado en {len(merged_q)} partidos con parciales disponibles.")

    merged_q['diff_q1'] = merged_q['q1_beni'] - merged_q['q1_rival']
    merged_q['diff_q2'] = merged_q['q2_beni'] - merged_q['q2_rival']
    merged_q['diff_q3'] = merged_q['q3_beni'] - merged_q['q3_rival']
    merged_q['diff_q4'] = merged_q['q4_beni'] - merged_q['q4_rival']

    avg_q1_beni = merged_q['q1_beni'].mean()
    avg_q1_rival = merged_q['q1_rival'].mean()
    avg_q2_beni = merged_q['q2_beni'].mean()
    avg_q2_rival = merged_q['q2_rival'].mean()
    avg_q3_beni = merged_q['q3_beni'].mean()
    avg_q3_rival = merged_q['q3_rival'].mean()
    avg_q4_beni = merged_q['q4_beni'].mean()
    avg_q4_rival = merged_q['q4_rival'].mean()

    def _tarjeta_cuarto(nombre, num, beni, rival):
        dif = beni - rival
        color = "#34D399" if dif >= 0 else "#F87171"
        return _html_plano(f"""
        <div class="metric-container">
            <div class="metric-label">{nombre} ({num})</div>
            <div class="metric-value">{beni:.1f} <span style="font-size: 1.1rem; color: #93C5FD;">vs {rival:.1f}</span></div>
            <div class="metric-sub" style="color: {color}; font-weight: 700;">Diferencial: {dif:+.2f} pts</div>
        </div>
        """)

    tarjetas_cuartos = [
        _tarjeta_cuarto("Primer Cuarto", "1Q", avg_q1_beni, avg_q1_rival),
        _tarjeta_cuarto("Segundo Cuarto", "2Q", avg_q2_beni, avg_q2_rival),
        _tarjeta_cuarto("Tercer Cuarto", "3Q", avg_q3_beni, avg_q3_rival),
        _tarjeta_cuarto("Último Cuarto", "4Q", avg_q4_beni, avg_q4_rival),
    ]
    st.markdown(_html_plano(f"""
    <div class="cards-row">
        {''.join(tarjetas_cuartos)}
    </div>
    """), unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    col_q_chart_main, col_q_wins = st.columns([3, 2])

    with col_q_chart_main:
        st.markdown("### Promedio de Puntos por Periodo")
        fig_q_comp = go.Figure()
        fig_q_comp.add_trace(go.Bar(
            name='CB Benicarló',
            x=['1Q', '2Q', '3Q', '4Q'],
            y=[avg_q1_beni, avg_q2_beni, avg_q3_beni, avg_q4_beni],
            marker_color='#2563EB',
            text=[f"{v:.1f}" for v in [avg_q1_beni, avg_q2_beni, avg_q3_beni, avg_q4_beni]],
            textposition='auto',
            textfont=dict(color='#FFFFFF'),
            hovertemplate='%{x}<br>CB Benicarló: <b>%{y:.1f}</b> pts<extra></extra>',
        ))
        fig_q_comp.add_trace(go.Bar(
            name='Rivales',
            x=['1Q', '2Q', '3Q', '4Q'],
            y=[avg_q1_rival, avg_q2_rival, avg_q3_rival, avg_q4_rival],
            marker_color='#64748B',
            text=[f"{v:.1f}" for v in [avg_q1_rival, avg_q2_rival, avg_q3_rival, avg_q4_rival]],
            textposition='auto',
            textfont=dict(color='#FFFFFF'),
            hovertemplate='%{x}<br>Rivales: <b>%{y:.1f}</b> pts<extra></extra>',
        ))
        style_fig(fig_q_comp)
        fig_q_comp.update_layout(
            barmode='group',
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#F8FAFC", size=11)),
            xaxis=dict(tickfont=dict(color="#E2E8F0")),
            yaxis=dict(gridcolor="#1E293B", tickfont=dict(color="#E2E8F0"), title='Puntos promedio'),
        )
        st.plotly_chart(fig_q_comp, **chart_kwargs())

    with col_q_wins:
        st.markdown("### Balance de Cuartos")
        q_wins = [
            (merged_q['diff_q1'] > 0).sum(),
            (merged_q['diff_q2'] > 0).sum(),
            (merged_q['diff_q3'] > 0).sum(),
            (merged_q['diff_q4'] > 0).sum()
        ]
        q_losses = [
            (merged_q['diff_q1'] < 0).sum(),
            (merged_q['diff_q2'] < 0).sum(),
            (merged_q['diff_q3'] < 0).sum(),
            (merged_q['diff_q4'] < 0).sum()
        ]
        q_ties = [
            (merged_q['diff_q1'] == 0).sum(),
            (merged_q['diff_q2'] == 0).sum(),
            (merged_q['diff_q3'] == 0).sum(),
            (merged_q['diff_q4'] == 0).sum()
        ]
        df_q_stats = pd.DataFrame({
            'Cuarto': ['1Q', '2Q', '3Q', '4Q'],
            'Ganados': q_wins,
            'Perdidos': q_losses,
            'Empatados': q_ties,
            '% Victoria': [f"{(w / len(merged_q) * 100):.1f}%" for w in q_wins]
        })
        st.dataframe(df_q_stats, hide_index=True, width="stretch")
