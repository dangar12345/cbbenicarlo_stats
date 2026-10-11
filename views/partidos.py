"""Vista: Partidos & Boxscores."""
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
    st.markdown("## Explorador de Partidos & Boxscores")
    st.caption("Consulta cualquier partido de la historia del club desde 2019/2020 hasta hoy con su acta completa.")

    partidos_disponibles = df_partidos[df_partidos['estado'] == 'jugado'].sort_values('fecha', ascending=False).copy()
    
    # Filter Controls
    f_col1, f_col2, f_col3 = st.columns([2, 2, 2])
    
    with f_col1:
        temporadas_list = ["Todas las temporadas"] + sorted(partidos_disponibles['temporada'].unique().tolist(), reverse=True)
        sel_temporada = st.selectbox("Temporada", temporadas_list, index=0)

    if sel_temporada != "Todas las temporadas":
        partidos_disponibles = partidos_disponibles[partidos_disponibles['temporada'] == sel_temporada]

    with f_col2:
        fases_list = ["Todas las fases"] + sorted(partidos_disponibles['fase_tipo'].unique().tolist())
        sel_fase = st.selectbox("Fase / Competición", fases_list, index=0)
        if sel_fase != "Todas las fases":
            partidos_disponibles = partidos_disponibles[partidos_disponibles['fase_tipo'] == sel_fase]

    with f_col3:
        filtro_resultado = st.selectbox("Resultado", ["Todos", "Solo Victorias", "Solo Derrotas", "Cerrados (±5)"])
        if filtro_resultado == "Solo Victorias":
            partidos_disponibles = partidos_disponibles[partidos_disponibles['resultado_benicarlo'] == 'Victoria']
        elif filtro_resultado == "Solo Derrotas":
            partidos_disponibles = partidos_disponibles[partidos_disponibles['resultado_benicarlo'] == 'Derrota']
        elif filtro_resultado == "Cerrados (±5)":
            partidos_disponibles = partidos_disponibles[partidos_disponibles['diferencia_puntos'].abs() <= 5]

    if partidos_disponibles.empty:
        st.warning("No hay partidos con los filtros seleccionados.")
        st.stop()

    # Selector por tabla: todas las opciones con su marcador a la vista, en
    # lugar de un select de 199 etiquetas truncadas donde V/D solo se leía
    # por el color de un emoji.
    tabla_sel = partidos_disponibles.assign(
        Fecha=partidos_disponibles['fecha'].dt.strftime('%d/%m/%y').fillna('S/F'),
        Rival=partidos_disponibles['equipo_rival'],
        Sede=np.where(partidos_disponibles['es_benicarlo_local'] == 1, 'Casa', 'Fuera'),
        Marcador=(partidos_disponibles['puntos_benicarlo'].astype(str) + ' - '
                  + partidos_disponibles['puntos_rival'].astype(str)),
        Res=partidos_disponibles['resultado_benicarlo'].str[0],
        Jornada=partidos_disponibles['jornada_nombre'].str.split('(').str[0].str.strip(),
        Datos=np.where(partidos_disponibles['qa_estado'] == 'ok', 'OK',
                       '⚠ ' + partidos_disponibles['qa_estado']),
    )[['Fecha', 'Rival', 'Sede', 'Marcador', 'Res', 'Jornada', 'Datos']]

    st.caption(f"Selecciona un partido de la tabla ({len(partidos_disponibles)} encontrados; "
               "por defecto, el más reciente). «Datos» avisa cuando el acta o los parciales "
               "no cuadran con el marcador oficial.")
    evento = st.dataframe(
        tabla_sel, hide_index=True, width="stretch", height=340,
        on_select="rerun", selection_mode="single-row",
        column_config={
            "Rival": st.column_config.TextColumn(width="medium"),
            "Jornada": st.column_config.TextColumn(width="small"),
        },
    )
    filas_sel = evento.selection.rows
    idx_sel = filas_sel[0] if filas_sel else 0
    sel_partido_id = int(partidos_disponibles.iloc[idx_sel]['partido_id'])
    match_row = df_partidos[df_partidos['partido_id'] == sel_partido_id].iloc[0]
    
    # Scoreboard
    is_win = match_row['resultado_benicarlo'] == 'Victoria'
    badge_class = "badge-win" if is_win else "badge-loss"
    
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="scoreboard">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px 12px; margin-bottom: 14px;">
            <div style="font-size: 0.95rem; color: #93C5FD; font-weight: 700; text-transform: uppercase; min-width: 0;">
                {match_row['temporada']}\u00A0·\u00A0{match_row['grupo_nombre']}\u00A0·\u00A0{match_row['jornada_nombre']}
            </div>
            <span class="{badge_class}">{match_row['resultado_benicarlo']}</span>
        </div>
        <div class="sb-grid">
            <div class="team-name sb-name-l" style="color: {'#38BDF8' if match_row['es_benicarlo_local'] else '#FFFFFF'};">
                {match_row['equipo_local']}
            </div>
            <div class="team-score sb-score-l">{match_row['puntos_local']}</div>
            <div class="sb-dash">-</div>
            <div class="team-name sb-name-r" style="color: {'#38BDF8' if not match_row['es_benicarlo_local'] else '#FFFFFF'};">
                {match_row['equipo_visitante']}
            </div>
            <div class="team-score sb-score-r">{match_row['puntos_visitante']}</div>
        </div>
        <div style="text-align: center; margin-top: 18px; font-size: 0.9rem; color: #E2E8F0;">
            📍 <b>Campo:</b> {match_row['cancha'] or 'Pabellón Municipal de Benicarló'}&nbsp;| 👨‍⚖️&nbsp;<b>Árbitros:</b> {match_row['arbitros'] or 'N/D'}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Franja de contexto de liga bajo el marcador (P2 · punto 5)
    jornada_txt = match_row['jornada_nombre'].split('(')[0].strip()
    if match_row['fase_tipo'] == 'Playoff':
        fase_txt = f"Playoff de ascenso\u00A0·\u00A0{jornada_txt}"
    else:
        fase_txt = f"{jornada_txt}\u00A0·\u00A0{match_row['grupo_nombre']}"
    partes_ctx = [f'<span class="ctx-fase">{fase_txt}</span>',
                  f"Temporada {match_row['temporada']}"]
    if df_temporadas is not None and not df_temporadas.empty:
        ctx = df_temporadas[df_temporadas['temporada'] == match_row['temporada']]
        if not ctx.empty:
            t = ctx.iloc[0]
            if pd.notnull(t.get('posicion_grupo')):
                etiqueta_pos = 'Clasificación actual' if t.get('resultado_hito') == 'en_curso' else 'Clasificación final'
                partes_ctx.append(f"{etiqueta_pos}: {int(t['posicion_grupo'])}º ({int(t['balance_v'])}-{int(t['balance_d'])})")
            clase_ctx, texto_ctx = hito_badge(t.get('resultado_hito'), t.get('fase_alcanzada', ''))
            if clase_ctx:
                partes_ctx.append(f'<span class="hito-badge {clase_ctx}">{texto_ctx}</span>')
    # Separador como sufijo irrompible de cada parte: al envolver en móvil el
    # "·" queda al final de línea y nunca la empieza.
    sep_ctx = '\u00A0·'
    ctx_html = ''.join(f'<span class="ctx-item">{p}{sep_ctx}</span>' for p in partes_ctx[:-1])
    ctx_html += f'<span class="ctx-item">{partes_ctx[-1]}</span>'
    st.markdown(f'<div class="match-context">{ctx_html}</div>', unsafe_allow_html=True)

    # Aviso de calidad de datos (bloque P1): el marcador oficial es fiable,
    # pero los parciales o el acta pueden venir incompletos de origen.
    avisos_qa = {
        'descuadre_jugadores': "El acta de jugadores no suma el marcador oficial (datos incompletos de origen).",
        'descuadre_cuartos': "Los parciales por cuarto no suman el marcador oficial.",
        'sin_acta': "Faltan parciales o acta de jugadores para este partido.",
    }
    qa_estado = match_row.get('qa_estado', 'ok')
    if qa_estado in avisos_qa:
        st.caption(f"⚠ Datos con reservas: {avisos_qa[qa_estado]}")

    # Quarters
    match_cuartos = df_cuartos[df_cuartos['partido_id'] == sel_partido_id]
    if not match_cuartos.empty:
        col_q_table, col_q_chart = st.columns([1, 1])
        with col_q_table:
            st.markdown("### Parciales por Cuarto")
            q_display = match_cuartos[['equipo', 'q1', 'q2', 'q3', 'q4', 'ot1', 'ot2', 'puntos_total']].copy()
            q_display.columns = ['Equipo', '1Q', '2Q', '3Q', '4Q', '1OT', '2OT', 'Total']
            if q_display['1OT'].sum() == 0:
                q_display = q_display.drop(columns=['1OT', '2OT'])
            st.dataframe(q_display, hide_index=True, width="stretch")

        with col_q_chart:
            st.markdown("### Evolución de Anotación")
            q_cols = ['1Q', '2Q', '3Q', '4Q']
            if '1OT' in q_display.columns:
                q_cols.append('1OT')
            
            fig_q = go.Figure()
            for _, r_eq in match_cuartos.iterrows():
                eq_color = '#2563EB' if r_eq['es_benicarlo'] == 1 else '#94A3B8'
                y_vals = [r_eq['q1'], r_eq['q2'], r_eq['q3'], r_eq['q4']]
                if r_eq['ot1'] > 0:
                    y_vals.append(r_eq['ot1'])
                fig_q.add_trace(go.Bar(
                    name=r_eq['equipo'],
                    x=q_cols[:len(y_vals)],
                    y=y_vals,
                    marker_color=eq_color,
                    text=y_vals,
                    textposition='auto',
                    textfont=dict(color='#FFFFFF'),
                    hovertemplate='%{x}<br>' + r_eq['equipo'] + ': <b>%{y}</b> pts<extra></extra>',
                ))
            style_fig(fig_q, height=210)
            fig_q.update_layout(
                barmode='group',
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#F8FAFC", size=11)),
                yaxis=dict(showgrid=False, tickfont=dict(color="#E2E8F0")),
                xaxis=dict(tickfont=dict(color="#E2E8F0")),
            )
            st.plotly_chart(fig_q, **chart_kwargs())

    # Boxscores
    st.markdown("### Acta y Estadísticas de Jugadores")
    match_players = df_jugadores[df_jugadores['partido_id'] == sel_partido_id].copy()

    def format_boxscore(df_sub):
        df_sub = df_sub.sort_values(['es_titular', 'minutos', 'puntos'], ascending=[False, False, False])
        
        # Advanced stats per game
        ts_denom = 2 * (df_sub['tc_intentados'] + 0.44 * df_sub['tl_intentados'])
        ts_vals = np.where(ts_denom > 0, (df_sub['puntos'] / ts_denom * 100).round(1), 0.0)
        net_rtg_vals = np.where(df_sub['minutos'] > 0, ((df_sub['mas_menos'] / df_sub['minutos']) * 53.3).round(1), 0.0)

        display_df = pd.DataFrame({
            'T': df_sub['es_titular'].apply(lambda x: '★' if x == 1 else ''),
            'D': df_sub['dorsal'],
            'Jugador': df_sub['jugador'],
            'MIN': df_sub['minutos'],
            'PTS': df_sub['puntos'],
            'TS%': [f"{v:.1f}%" if v > 0 else "-" for v in ts_vals],
            'NetRtg': [f"{v:+.1f}" if m > 0 else "-" for v, m in zip(net_rtg_vals, df_sub['minutos'])],
            'T2': df_sub.apply(lambda r: f"{r['t2_anotados']}/{r['t2_intentados']} ({r['t2_pct']:.0f}%)", axis=1),
            'T3': df_sub.apply(lambda r: f"{r['t3_anotados']}/{r['t3_intentados']} ({r['t3_pct']:.0f}%)", axis=1),
            'TL': df_sub.apply(lambda r: f"{r['tl_anotados']}/{r['tl_intentados']} ({r['tl_pct']:.0f}%)", axis=1),
            'REB': df_sub['rebotes_totales'],
            'AST': df_sub['asistencias'],
            'ROB': df_sub['recuperaciones'],
            'PER': df_sub['perdidas'],
            'TAP': df_sub['tapones_favor'],
            'FAL': df_sub['faltas_cometidas'],
            'VAL': df_sub['valoracion'],
            '+/-': df_sub['mas_menos']
        })
        if df_sub['es_titular'].sum() == 0:
            display_df = display_df.drop(columns=['T'])
        return display_df

    tab_beni, tab_rival = st.tabs(["CB Benicarló", f"Rival: {match_row['equipo_rival']}"])
    with tab_beni:
        beni_players = match_players[match_players['es_benicarlo'] == 1]
        if not beni_players.empty:
            st.dataframe(format_boxscore(beni_players), hide_index=True, width="stretch")
        else:
            st.info("No hay datos de jugadores para este partido.")

    with tab_rival:
        rival_players = match_players[match_players['es_benicarlo'] == 0]
        if not rival_players.empty:
            st.dataframe(format_boxscore(rival_players), hide_index=True, width="stretch")
        else:
            st.info("No hay datos de jugadores para el equipo rival.")
