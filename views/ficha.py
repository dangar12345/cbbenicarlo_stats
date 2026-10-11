"""Vista: Ficha & Comparador."""
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
    st.markdown("## Ficha & Comparador de Jugadores")
    st.caption("Ficha individual por temporada y comparación lado a lado entre jugadores del club.")

    # Claves internas de métrica -> etiqueta legible (ejes, leyendas y tablas)
    NOMBRES_CMP = {'PPP': 'Pts/p', 'RPP': 'Reb/p', 'APP': 'As/p', 'ROB': 'Rob/p',
                   'TAP': 'Tap/p', 'T3P': 'Trip/p', 'VPP': 'Val/p', 'MIN': 'Min/p'}

    # Deep link: ?jugador=<nombre canónico> preselecciona la ficha
    _param_jugador = st.query_params.get("jugador")
    if _param_jugador and "ficha_jugador" not in st.session_state:
        st.session_state["ficha_jugador"] = _param_jugador

    def _serie_temporada(jrows):
        """Agregados por temporada de un jugador (mismas fórmulas que los rankings).

        Las métricas derivadas se calculan con el índice de temporada intacto
        (antes del reset_index) para que las Series se alineen por temporada;
        hacerlo después provoca la unión de índices y NaN.
        """
        g = jrows.groupby('temporada')
        s = pd.DataFrame({
            'PJ': g['partido_id'].nunique(),
            'MIN': g['minutos'].sum(),
            'PTS': g['puntos'].sum(),
            'PPP': g['puntos'].mean().round(1),
            'REB': g['rebotes_totales'].sum(),
            'RPP': g['rebotes_totales'].mean().round(1),
            'AST': g['asistencias'].sum(),
            'APP': g['asistencias'].mean().round(1),
            'VAL': g['valoracion'].sum(),
            'VPP': g['valoracion'].mean().round(1),
        })
        ts_den = 2 * (g['tc_intentados'].sum() + 0.44 * g['tl_intentados'].sum())
        efg_den = g['tc_intentados'].sum()
        efg_num = g['tc_anotados'].sum() + 0.5 * g['t3_anotados'].sum()
        min_den = g['minutos'].sum()
        s['TS%'] = np.where(ts_den > 0, (s['PTS'] / ts_den.replace(0, np.nan) * 100).round(1), 0.0)
        s['eFG%'] = np.where(efg_den > 0, (efg_num / efg_den.replace(0, np.nan) * 100).round(1), 0.0)
        s['NetRtg'] = np.where(min_den > 0, (g['mas_menos'].sum() / min_den.replace(0, np.nan) * 53.3).round(1), 0.0)
        return s.reset_index().sort_values('temporada').reset_index(drop=True)

    def _agg_carrera(jrows):
        """Agregados de carrera en un dict por partido (para el comparador)."""
        pj = jrows['partido_id'].nunique()
        if pj == 0:
            return None
        pts, minu = jrows['puntos'].sum(), jrows['minutos'].sum()
        ts_den = 2 * (jrows['tc_intentados'].sum() + 0.44 * jrows['tl_intentados'].sum())
        efg_den = jrows['tc_intentados'].sum()
        return {
            'PJ': pj,
            'MIN': round(minu / pj, 1),
            'PPP': round(pts / pj, 1),
            'RPP': round(jrows['rebotes_totales'].sum() / pj, 1),
            'APP': round(jrows['asistencias'].sum() / pj, 1),
            'ROB': round(jrows['recuperaciones'].sum() / pj, 1),
            'TAP': round(jrows['tapones_favor'].sum() / pj, 1),
            'T3P': round(jrows['t3_anotados'].sum() / pj, 1),
            'VPP': round(jrows['valoracion'].sum() / pj, 1),
            'TS%': round(pts / ts_den * 100, 1) if ts_den > 0 else 0.0,
            'eFG%': round((jrows['tc_anotados'].sum() + 0.5 * jrows['t3_anotados'].sum()) / efg_den * 100, 1) if efg_den > 0 else 0.0,
        }

    beni_jug = df_jugadores[df_jugadores['es_benicarlo'] == 1].copy()
    # Ordena el selector por relevancia (puntos totales en el club)
    relevancia = beni_jug.groupby('jugador')['puntos'].sum().sort_values(ascending=False)
    lista_jugadores = relevancia.index.tolist()

    modo_jug = st.radio("Modo", ["Ficha individual", "Comparador"],
                        horizontal=True, label_visibility="collapsed")

    # ------------------------------------------------------------------ FICHA
    if modo_jug == "Ficha individual":
        if not lista_jugadores:
            st.warning("No hay registros de jugadores del club.")
            st.stop()
        sel_ficha = st.selectbox("Jugador", lista_jugadores, key="ficha_jugador")
        jrows = beni_jug[beni_jug['jugador'] == sel_ficha]
        serie = _serie_temporada(jrows)
        pj_total = int(serie['PJ'].sum())

        st.markdown(f"### {sel_ficha}")
        st.caption(f"{serie.shape[0]} temporadas · {pj_total} partidos")

        # KPIs de carrera
        titulares = int(jrows['es_titular'].sum())
        pct_titular = (titulares / pj_total * 100) if pj_total else 0.0
        ts_carrera = _agg_carrera(jrows)
        kpis = [
            ("Puntos por partido", f"{ts_carrera['PPP']}", f"{miles(int(jrows['puntos'].sum()))} puntos en total"),
            ("Rebotes por partido", f"{ts_carrera['RPP']}", f"{miles(int(jrows['rebotes_totales'].sum()))} rebotes"),
            ("Asistencias por partido", f"{ts_carrera['APP']}", f"{miles(int(jrows['asistencias'].sum()))} asistencias"),
            ("Valoración por partido", f"{ts_carrera['VPP']}",
             f"{miles(int(jrows['valoracion'].sum()))} VAL · TS% {ts_carrera['TS%']:.1f}%"),
            ("Titularidad", f"{pct_titular:.0f}%", f"{titulares} de {pj_total} partidos como inicial"),
        ]
        tarjetas = []
        for etiqueta, valor, sub in kpis:
            tarjetas.append(_html_plano(f"""
            <div class="metric-container">
                <div class="metric-label">{etiqueta}</div>
                <div class="metric-value">{valor}</div>
                <div class="metric-sub">{sub}</div>
            </div>
            """))
        st.markdown(_html_plano(f"""
        <div class="cards-row">
            {''.join(tarjetas)}
        </div>
        """), unsafe_allow_html=True)
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        col_ficha_chart, col_ficha_split = st.columns([3, 2])
        with col_ficha_chart:
            st.markdown("#### Trayectoria por Temporada")
            metricas_tray = (('PPP', '#38BDF8'), ('RPP', '#F43F5E'),
                             ('APP', '#34D399'), ('VPP', '#FBBF24'))
            nombres_tray = {'PPP': 'Pts/p', 'RPP': 'Reb/p', 'APP': 'As/p', 'VPP': 'Val/p'}
            if len(serie) < 2:
                # Un solo punto en líneas queda perdido: barras con las
                # métricas de esa temporada.
                fig_tray = go.Figure(go.Bar(
                    x=[nombres_tray[m] for m, _ in metricas_tray],
                    y=[serie[m].iloc[0] for m, _ in metricas_tray],
                    marker_color=[c for _, c in metricas_tray],
                    text=[f"{serie[m].iloc[0]:.1f}" for m, _ in metricas_tray],
                    textposition='outside',
                    textfont=dict(color='#F8FAFC'),
                    hovertemplate='%{x}: <b>%{y:.1f}</b><extra>' + serie['temporada'].iloc[0] + '</extra>',
                ))
                style_fig(fig_tray, height=320)
                fig_tray.update_layout(
                    margin=dict(l=20, r=20, t=30, b=20),
                    xaxis=dict(tickfont=dict(color="#E2E8F0"), showgrid=False),
                    yaxis=dict(gridcolor="#1E293B", tickfont=dict(color="#E2E8F0"), title='Por partido',
                               range=[0, max(serie[m].iloc[0] for m, _ in metricas_tray) * 1.25]),
                )
            else:
                fig_tray = go.Figure()
                for serie_nombre, color in metricas_tray:
                    fig_tray.add_trace(go.Scatter(
                        x=serie['temporada'], y=serie[serie_nombre], name=nombres_tray[serie_nombre],
                        mode='lines+markers', line=dict(color=color, width=2),
                        hovertemplate='%{x}<br>' + nombres_tray[serie_nombre] + ': <b>%{y:.1f}</b><extra></extra>',
                    ))
                style_fig(fig_tray, height=320, hovermode='x unified')
                fig_tray.update_layout(
                    margin=dict(l=20, r=20, t=20, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#F8FAFC", size=11)),
                    xaxis=dict(tickfont=dict(color="#E2E8F0"), tickangle=0),
                    yaxis=dict(gridcolor="#1E293B", tickfont=dict(color="#E2E8F0"), title='Por partido'),
                )
            st.plotly_chart(fig_tray, **chart_kwargs())

        with col_ficha_split:
            st.markdown("#### Titular vs Suplente")
            jrows_cp = jrows.copy()
            jrows_cp['rol'] = np.where(jrows_cp['es_titular'] == 1, 'Titular', 'Suplente')
            g_rol = jrows_cp.groupby('rol')
            tabla_rol = pd.DataFrame({
                'PJ': g_rol['partido_id'].nunique(),
                'PPP': g_rol['puntos'].mean().round(1),
                'RPP': g_rol['rebotes_totales'].mean().round(1),
                'APP': g_rol['asistencias'].mean().round(1),
                'VPP': g_rol['valoracion'].mean().round(1),
            }).reset_index().rename(columns={'rol': 'Rol'})
            st.dataframe(tabla_rol, hide_index=True, width="stretch")

        # Tabla por temporada
        tabla_ficha = serie.copy()
        for col in ('PPP', 'RPP', 'APP', 'VPP'):
            tabla_ficha[col] = tabla_ficha[col].apply(lambda x: f"{x:.1f}")
        tabla_ficha['TS%'] = tabla_ficha['TS%'].apply(lambda x: f"{x:.1f}%")
        tabla_ficha['eFG%'] = tabla_ficha['eFG%'].apply(lambda x: f"{x:.1f}%")
        tabla_ficha['NetRtg'] = tabla_ficha['NetRtg'].apply(lambda x: f"{x:+.1f}")
        tabla_ficha.columns = ['Temporada', 'PJ', 'MIN', 'PTS', 'Pts/p', 'REB', 'Reb/p',
                               'AST', 'As/p', 'VAL', 'Val/p', 'TS%', 'eFG%', 'NetRtg']
        st.markdown("#### Temporada a Temporada")
        st.dataframe(tabla_ficha, hide_index=True, width="stretch")

        # Últimos partidos (bitácora)
        partidos_info = df_partidos[['partido_id', 'fecha', 'equipo_rival',
                                     'es_benicarlo_local', 'resultado_benicarlo', 'estado']]
        log = jrows.merge(partidos_info, on='partido_id')
        log = log[log['estado'] == 'jugado'].sort_values('fecha', ascending=False).head(10)
        if not log.empty:
            st.markdown("#### Últimos Partidos")
            tabla_log = pd.DataFrame({
                'Fecha': log['fecha'].dt.strftime('%d/%m/%y'),
                'Rival': log['equipo_rival'].apply(truncar_nombre),
                'Sede': np.where(log['es_benicarlo_local'] == 1, 'Casa', 'Fuera'),
                'Res': log['resultado_benicarlo'].str[0],
                'MIN': log['minutos'],
                'PTS': log['puntos'],
                'T3': log['t3_anotados'],
                'REB': log['rebotes_totales'],
                'AST': log['asistencias'],
                'VAL': log['valoracion'],
                '+/-': log['mas_menos'],
            })
            st.dataframe(tabla_log, hide_index=True, width="stretch")

    # ------------------------------------------------------------- COMPARADOR
    else:
        c_cmp_a, c_cmp_b = st.columns(2)
        with c_cmp_a:
            jugador_a = st.selectbox("Jugador A", lista_jugadores, key="cmp_a")
        with c_cmp_b:
            idx_b = 1 if len(lista_jugadores) > 1 else 0
            jugador_b = st.selectbox("Jugador B", lista_jugadores, index=idx_b, key="cmp_b")

        temporadas_cmp = ["Toda la carrera"] + sorted(
            beni_jug['temporada'].unique().tolist(), reverse=True)
        alcance = st.selectbox("Alcance", temporadas_cmp, key="cmp_temporada")

        def _filas(jugador):
            f = beni_jug[beni_jug['jugador'] == jugador]
            if alcance != "Toda la carrera":
                f = f[f['temporada'] == alcance]
            return f

        filas_a, filas_b = _filas(jugador_a), _filas(jugador_b)
        agg_a, agg_b = _agg_carrera(filas_a), _agg_carrera(filas_b)

        if agg_a is None or agg_b is None:
            st.warning("No hay partidos con los filtros seleccionados.")
            st.stop()

        st.markdown(f"### {truncar_nombre(jugador_a, 28)} vs {truncar_nombre(jugador_b, 28)}")
        st.caption(f"Alcance: {alcance} · {agg_a['PJ']} vs {agg_b['PJ']} partidos")

        # Radar normalizado EJE A EJE (cada métrica escala frente al máximo de
        # los dos jugadores en esa métrica): si todas compartieran el máximo
        # absoluto, Reb/As/Tap colapsarían al centro cuando PPP domina.
        ejes = ['PPP', 'RPP', 'APP', 'ROB', 'TAP', 'VPP']
        maximos = {e: (max(agg_a[e], agg_b[e]) or 1) for e in ejes}
        fig_cmp = go.Figure()
        for nombre, agg, color in ((truncar_nombre(jugador_a, 20), agg_a, '#38BDF8'),
                                   (truncar_nombre(jugador_b, 20), agg_b, '#F43F5E')):
            fig_cmp.add_trace(go.Scatterpolar(
                r=[agg[e] / maximos[e] * 100 for e in ejes],
                theta=[NOMBRES_CMP[e] for e in ejes],
                customdata=[agg[e] for e in ejes],
                fill='toself', name=nombre,
                line=dict(color=color),
                hovertemplate='%{theta}: <b>%{customdata:.1f}</b> por partido<extra>' + nombre + '</extra>',
            ))
        style_fig(fig_cmp, height=400)
        fig_cmp.update_layout(
            polar=dict(radialaxis=dict(range=[0, 112], gridcolor="#1E293B",
                                       tickfont=dict(color="#E2E8F0"), showticklabels=False),
                       bgcolor='rgba(0,0,0,0)'),
            margin=dict(l=40, r=40, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#F8FAFC", size=11)),
        )
        st.plotly_chart(fig_cmp, **chart_kwargs())

        # Tabla comparativa
        filas_tabla = []
        for metrica, formato in (('PJ', 'd'), ('MIN', '.1f'), ('PPP', '.1f'), ('RPP', '.1f'),
                                 ('APP', '.1f'), ('ROB', '.1f'), ('TAP', '.1f'), ('T3P', '.1f'),
                                 ('VPP', '.1f'), ('TS%', '.1f'), ('eFG%', '.1f')):
            va, vb = agg_a[metrica], agg_b[metrica]
            mejor_a = va > vb
            filas_tabla.append({
                'Métrica': NOMBRES_CMP.get(metrica, metrica),
                jugador_a[:20]: f"{va:{formato}}" if formato != 'd' else str(va),
                jugador_b[:20]: f"{vb:{formato}}" if formato != 'd' else str(vb),
                'Ventaja': truncar_nombre(jugador_a, 16) if mejor_a else truncar_nombre(jugador_b, 16),
            })
        st.dataframe(pd.DataFrame(filas_tabla), hide_index=True, width="stretch")

