"""Vista: Líderes & Jugadores."""
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
    st.markdown("## Rendimiento de Jugadores & Récords Históricos")
    st.caption("Rankings individuales, máximos anotadores y estadísticas acumuladas.")

    # Temporada filter
    seasons_avail = ["Histórico Completo (Todas)"] + sorted(df_partidos['temporada'].unique().tolist(), reverse=True)
    sel_player_season = st.selectbox("Seleccionar Temporada:", seasons_avail, index=0)

    if sel_player_season != "Histórico Completo (Todas)":
        beni_all = df_jugadores[(df_jugadores['temporada'] == sel_player_season) & (df_jugadores['es_benicarlo'] == 1)].copy()
    else:
        beni_all = df_jugadores[df_jugadores['es_benicarlo'] == 1].copy()

    if beni_all.empty:
        st.warning("No hay datos de jugadores para la selección.")
        st.stop()

    # Aggregate by player
    player_agg = beni_all.groupby('jugador').agg(
        Partidos=('partido_id', 'nunique'),
        Minutos=('minutos', 'sum'),
        Puntos=('puntos', 'sum'),
        Puntos_Media=('puntos', 'mean'),
        TC_Anotados=('tc_anotados', 'sum'),
        TC_Intentados=('tc_intentados', 'sum'),
        T3_Anotados=('t3_anotados', 'sum'),
        T3_Intentados=('t3_intentados', 'sum'),
        TL_Anotados=('tl_anotados', 'sum'),
        TL_Intentados=('tl_intentados', 'sum'),
        Rebotes=('rebotes_totales', 'sum'),
        Rebotes_Media=('rebotes_totales', 'mean'),
        Asistencias=('asistencias', 'sum'),
        Asistencias_Media=('asistencias', 'mean'),
        Robos=('recuperaciones', 'sum'),
        Valoracion=('valoracion', 'sum'),
        Valoracion_Media=('valoracion', 'mean'),
        Mas_Menos=('mas_menos', 'sum'),
        Max_Puntos=('puntos', 'max')
    ).reset_index()

    player_agg['T3_Pct'] = np.where(
        player_agg['T3_Intentados'] > 0,
        round(player_agg['T3_Anotados'] / player_agg['T3_Intentados'] * 100, 1),
        0.0
    )
    
    # Advanced: True Shooting % = PTS / (2 * (FGA + 0.44 * FTA)) * 100
    ts_denom = 2 * (player_agg['TC_Intentados'] + 0.44 * player_agg['TL_Intentados'])
    player_agg['TS_Pct'] = np.where(
        ts_denom > 0,
        (player_agg['Puntos'] / ts_denom * 100).round(1),
        0.0
    )

    # Advanced: Effective Field Goal % = (FGM + 0.5 * 3PM) / FGA * 100
    player_agg['eFG_Pct'] = np.where(
        player_agg['TC_Intentados'] > 0,
        ((player_agg['TC_Anotados'] + 0.5 * player_agg['T3_Anotados']) / player_agg['TC_Intentados'] * 100).round(1),
        0.0
    )

    # Advanced: Net Rating (per 100 possessions)
    player_agg['Net_Rating'] = np.where(
        player_agg['Minutos'] > 0,
        ((player_agg['Mas_Menos'] / player_agg['Minutos']) * 53.3).round(1),
        0.0
    )

    player_agg['Puntos_Media'] = player_agg['Puntos_Media'].round(1)
    player_agg['Rebotes_Media'] = player_agg['Rebotes_Media'].round(1)
    player_agg['Asistencias_Media'] = player_agg['Asistencias_Media'].round(1)
    player_agg['Valoracion_Media'] = player_agg['Valoracion_Media'].round(1)

    # FILTROS DE CORTE EN RANKINGS (P2 · umbrales mínimos)
    # Un jugador con 1 partido puede liderar un promedio por azar; el corte
    # limita quién entra en cards, gráfica y tabla.
    max_partidos_corte = int(player_agg['Partidos'].max()) if not player_agg.empty else 1
    max_minutos_corte = int(player_agg['Minutos'].max()) if not player_agg.empty else 1

    corte_col1, corte_col2, corte_col3 = st.columns([2, 2, 3])
    with corte_col1:
        sel_min_partidos = st.slider("Partidos mínimos", 0, max(max_partidos_corte, 1), 0)
    with corte_col2:
        sel_min_minutos = st.slider("Minutos mínimos", 0, max(max_minutos_corte, 1), 0, step=50)
    with corte_col3:
        st.markdown("<div style='height: 26px;'></div>", unsafe_allow_html=True)
        st.caption("Corte mínimo para entrar en los rankings: evita sesgos en promedios (Pts/p, TS%, eFG%, NetRtg).")

    player_rank = player_agg[
        (player_agg['Partidos'] >= sel_min_partidos) &
        (player_agg['Minutos'] >= sel_min_minutos)
    ]
    if sel_min_partidos > 0 or sel_min_minutos > 0:
        st.caption(f"{len(player_rank)} de {len(player_agg)} jugadores cumplen el corte.")
    if player_rank.empty:
        st.warning("Ningún jugador cumple el corte seleccionado. Reduce los umbrales.")
        st.stop()

    # Top Leaders Row
    top_scorer = player_rank.sort_values('Puntos', ascending=False).iloc[0]
    top_ast = player_rank.sort_values('Asistencias', ascending=False).iloc[0]
    top_reb = player_rank.sort_values('Rebotes', ascending=False).iloc[0]
    top_val = player_rank.sort_values('Valoracion', ascending=False).iloc[0]

    def _tarjeta_lider(etiqueta, valor, unidad, jugador, sub):
        return _html_plano(f"""
        <div class="metric-container">
            <div class="metric-label">{etiqueta}</div>
            <div class="metric-value">{valor} <span style="font-size: 1.1rem; color: #93C5FD;">{unidad}</span></div>
            <div style="font-weight: 800; color: #FFFFFF; font-size: 1rem; margin-top: 4px;">{jugador}</div>
            <div class="metric-sub">{sub}</div>
        </div>
        """)

    tarjetas_lideres = [
        _tarjeta_lider("Máximo Anotador", top_scorer['Puntos'], "PTS", top_scorer['jugador'],
                       f"{top_scorer['Puntos_Media']} Pts/p · {top_scorer['Partidos']} partidos"),
        _tarjeta_lider("Líder Asistencias", top_ast['Asistencias'], "AST", top_ast['jugador'],
                       f"{top_ast['Asistencias_Media']} APP · {top_ast['Partidos']} partidos"),
        _tarjeta_lider("Líder Rebotes", top_reb['Rebotes'], "REB", top_reb['jugador'],
                       f"{top_reb['Rebotes_Media']} RPP · {top_reb['Partidos']} partidos"),
        _tarjeta_lider("Líder Valoración", top_val['Valoracion'], "VAL", top_val['jugador'],
                       f"{top_val['Valoracion_Media']} VPP · {top_val['Partidos']} partidos"),
    ]
    st.markdown(_html_plano(f"""
    <div class="cards-row">
        {''.join(tarjetas_lideres)}
    </div>
    """), unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    col_chart_scorers, col_records = st.columns([3, 2])

    with col_chart_scorers:
        st.markdown("### Top 10 Anotadores")
        top10 = player_rank.sort_values('Puntos', ascending=False).head(10).copy()
        top10['jugador_corto'] = top10['jugador'].apply(truncar_nombre)
        fig_scorers = px.bar(
            top10,
            x='Puntos',
            y='jugador_corto',
            orientation='h',
            text='Puntos',
            color='Puntos',
            color_continuous_scale=['#1E40AF', '#38BDF8'],
            custom_data=['Puntos_Media', 'Partidos', 'jugador'],
        )
        fig_scorers.update_traces(
            textposition='outside',
            textfont=dict(color='#F8FAFC'),
            hovertemplate='%{customdata[2]}<br><b>%{x}</b> puntos · %{customdata[0]:.1f} Pts/p · %{customdata[1]} partidos<extra></extra>',
        )
        style_fig(fig_scorers, height=380)
        fig_scorers.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed", title=None, tickfont=dict(color="#FFFFFF", size=11)),
            xaxis=dict(showgrid=False, title=None, tickfont=dict(color="#E2E8F0"), range=[0, top10['Puntos'].max() * 1.22]),
        )
        st.plotly_chart(fig_scorers, **chart_kwargs())

    with col_records:
        st.markdown("### Récords en un Solo Partido")
        rec_pts = beni_all.sort_values('puntos', ascending=False).iloc[0]
        rec_val = beni_all.sort_values('valoracion', ascending=False).iloc[0]
        rec_triples = beni_all.sort_values('t3_anotados', ascending=False).iloc[0]
        rec_reb = beni_all.sort_values('rebotes_totales', ascending=False).iloc[0]

        records_data = pd.DataFrame([
            {"Récord": "Más Puntos", "Marca": f"{rec_pts['puntos']} pts", "Jugador": rec_pts['jugador'], "Temporada": rec_pts['temporada']},
            {"Récord": "Mayor Valoración", "Marca": f"{rec_val['valoracion']} val", "Jugador": rec_val['jugador'], "Temporada": rec_val['temporada']},
            {"Récord": "Más Triples", "Marca": f"{rec_triples['t3_anotados']} T3", "Jugador": rec_triples['jugador'], "Temporada": rec_triples['temporada']},
            {"Récord": "Más Rebotes", "Marca": f"{rec_reb['rebotes_totales']} reb", "Jugador": rec_reb['jugador'], "Temporada": rec_reb['temporada']},
        ])
        st.dataframe(records_data, hide_index=True, width="stretch")

    # Full Player Table with Direct Search (NO SLIDER)
    st.markdown("### Tabla Completa de Jugadores")
    st.caption("Incluye estadísticas tradicionales y analítica avanzada: **TS%** (True Shooting %), **eFG%** (Tiro efectivo) y **NetRtg** (Balance neto por 100 posesiones).")
    
    search_query = st.text_input("🔍 Buscar jugador por nombre:", placeholder="Escribe para filtrar (ej. Libroia, Ruesga, Orlov, Lafuente...)")
    
    table_src = player_rank.sort_values('Puntos', ascending=False).copy()
    if search_query:
        table_src = table_src[table_src['jugador'].str.contains(search_query, case=False, na=False)]

    table_src['TS%'] = table_src['TS_Pct'].apply(lambda x: f"{x:.1f}%")
    table_src['eFG%'] = table_src['eFG_Pct'].apply(lambda x: f"{x:.1f}%")
    table_src['NetRtg'] = table_src['Net_Rating'].apply(lambda x: f"{x:+.1f}")

    table_display = table_src[[
        'jugador', 'Partidos', 'Minutos', 'Puntos', 'Puntos_Media',
        'TS%', 'eFG%', 'NetRtg',
        'T3_Anotados', 'T3_Pct', 'Rebotes', 'Rebotes_Media',
        'Asistencias', 'Asistencias_Media', 'Valoracion', 'Max_Puntos'
    ]].copy()
    table_display.columns = [
        'Jugador', 'PJ', 'MIN', 'PTS', 'PPP',
        'TS%', 'eFG%', 'NetRtg',
        'T3 Conv', 'T3 %', 'REB', 'RPP',
        'AST', 'APP', 'VAL', 'Máx PTS'
    ]
    st.dataframe(table_display, hide_index=True, width="stretch")

    # EVOLUCIÓN INTERANUAL POR JUGADOR (P2 · vista temporal año a año)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("### Evolución Interanual por Jugador")
    st.caption("Trayectoria año a año con el CB Benicarló: producción, eficiencia y participación.")

    beni_hist = df_jugadores[df_jugadores['es_benicarlo'] == 1].copy()
    jugadores_hist = sorted(beni_hist['jugador'].dropna().unique())
    default_jugador = (player_rank.sort_values('Puntos', ascending=False).iloc[0]['jugador']
                       if not player_rank.empty else jugadores_hist[0])
    sel_jugador = st.selectbox(
        "Jugador",
        jugadores_hist,
        index=jugadores_hist.index(default_jugador) if default_jugador in jugadores_hist else 0,
        key="evo_jugador",
    )

    jrows = beni_hist[beni_hist['jugador'] == sel_jugador]
    g_j = jrows.groupby('temporada')
    evo = pd.DataFrame({
        'PJ': g_j['partido_id'].nunique(),
        'MIN': g_j['minutos'].sum(),
        'PTS': g_j['puntos'].sum(),
        'PPP': g_j['puntos'].mean().round(1),
        'REB': g_j['rebotes_totales'].sum(),
        'RPP': g_j['rebotes_totales'].mean().round(1),
        'AST': g_j['asistencias'].sum(),
        'APP': g_j['asistencias'].mean().round(1),
        'VAL': g_j['valoracion'].sum(),
        'VPP': g_j['valoracion'].mean().round(1),
    }).reset_index().sort_values('temporada').reset_index(drop=True)

    # Ratios por temporada (mismas fórmulas que los rankings históricos)
    ts_den = (2 * (g_j['tc_intentados'].sum() + 0.44 * g_j['tl_intentados'].sum())).values
    efg_den = g_j['tc_intentados'].sum().values
    min_den = g_j['minutos'].sum().values
    evo['TS%'] = np.where(ts_den > 0, np.round(evo['PTS'].values / np.where(ts_den == 0, 1, ts_den) * 100, 1), 0.0)
    evo['eFG%'] = np.where(efg_den > 0, np.round(
        (g_j['tc_anotados'].sum().values + 0.5 * g_j['t3_anotados'].sum().values) /
        np.where(efg_den == 0, 1, efg_den) * 100, 1), 0.0)
    evo['NetRtg'] = np.where(min_den > 0, np.round(
        g_j['mas_menos'].sum().values / np.where(min_den == 0, 1, min_den) * 53.3, 1), 0.0)

    if len(evo) < 2:
        # Un solo punto en líneas queda perdido: barras con las métricas de
        # esa temporada, que es lo que de verdad se quiere leer.
        metricas = [('PPP', '#38BDF8'), ('RPP', '#F43F5E'), ('APP', '#34D399')]
        fig_evo = go.Figure(go.Bar(
            x=[m for m, _ in metricas],
            y=[evo[m].iloc[0] for m, _ in metricas],
            marker_color=[c for _, c in metricas],
            text=[f"{evo[m].iloc[0]:.1f}" for m, _ in metricas],
            textposition='outside',
            textfont=dict(color='#F8FAFC'),
            hovertemplate='%{x}: <b>%{y:.1f}</b> por partido<extra>' + evo['temporada'].iloc[0] + '</extra>',
        ))
        style_fig(fig_evo, height=300)
        fig_evo.update_layout(
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(tickfont=dict(color="#E2E8F0"), showgrid=False),
            yaxis=dict(gridcolor="#1E293B", tickfont=dict(color="#E2E8F0"), title='Por partido',
                       range=[0, max(evo[m].iloc[0] for m, _ in metricas) * 1.25]),
        )
    else:
        fig_evo = go.Figure()
        nombres_evo = {'PPP': 'Pts/p', 'RPP': 'Reb/p', 'APP': 'As/p'}
        for serie, color, ancho in (('PPP', '#38BDF8', 3), ('RPP', '#F43F5E', 2), ('APP', '#34D399', 2)):
            fig_evo.add_trace(go.Scatter(
                x=evo['temporada'], y=evo[serie], name=nombres_evo[serie],
                mode='lines+markers',
                line=dict(color=color, width=ancho),
                hovertemplate='%{x}<br>' + nombres_evo[serie] + ': <b>%{y:.1f}</b> por partido<extra></extra>',
            ))
        style_fig(fig_evo, height=300, hovermode='x unified')
        fig_evo.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#F8FAFC", size=11)),
            xaxis=dict(tickfont=dict(color="#E2E8F0"), tickangle=0),
            yaxis=dict(gridcolor="#1E293B", tickfont=dict(color="#E2E8F0"), title='Por partido'),
        )
    st.plotly_chart(fig_evo, **chart_kwargs())

    if len(evo) >= 3:
        pendiente = np.polyfit(np.arange(len(evo)), evo['PPP'].values, 1)[0]
        tendencia = ("estable" if abs(pendiente) < 0.05
                     else f"{pendiente:+.1f} Pts/p por temporada")
        st.caption(f"{len(evo)} temporadas con el club · Tendencia de anotación: {tendencia}.")
    else:
        st.caption(f"{len(evo)} temporada(s) con el club.")

    tabla_evo = evo[['temporada', 'PJ', 'MIN', 'PTS', 'PPP', 'REB', 'RPP', 'AST', 'APP',
                     'VAL', 'TS%', 'eFG%', 'NetRtg']].copy()
    for col in ('PPP', 'RPP', 'APP'):
        tabla_evo[col] = tabla_evo[col].apply(lambda x: f"{x:.1f}")
    tabla_evo['TS%'] = tabla_evo['TS%'].apply(lambda x: f"{x:.1f}%")
    tabla_evo['eFG%'] = tabla_evo['eFG%'].apply(lambda x: f"{x:.1f}%")
    tabla_evo['NetRtg'] = tabla_evo['NetRtg'].apply(lambda x: f"{x:+.1f}")
    tabla_evo.columns = ['Temporada', 'PJ', 'MIN', 'PTS', 'Pts/p', 'REB', 'Reb/p', 'AST', 'As/p',
                         'VAL', 'TS%', 'eFG%', 'NetRtg']
    st.dataframe(tabla_evo, hide_index=True, width="stretch")

