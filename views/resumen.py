"""Vista: Resumen & Trayectoria."""
import os
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from charts import style_fig, chart_kwargs
from components import _html_plano, truncar_nombre, hito_badge


def render(ctx):
    # Datos compartidos (inyectados por app.py)
    df_partidos = ctx['df_partidos']
    df_cuartos = ctx['df_cuartos']
    df_jugadores = ctx['df_jugadores']
    cat_jugadores = ctx['cat_jugadores']
    cat_equipos = ctx['cat_equipos']
    df_temporadas = ctx['df_temporadas']
    st.markdown("## Trayectoria Histórica del CB Benicarló")
    st.caption("Evolución de resultados, anotación y balance competitivo en Segunda FEB y LEB Plata.")

    partidos_played = df_partidos[df_partidos['estado'] == 'jugado'].copy()
    total_games = len(partidos_played)
    wins = len(partidos_played[partidos_played['resultado_benicarlo'] == 'Victoria'])
    losses = len(partidos_played[partidos_played['resultado_benicarlo'] == 'Derrota'])
    win_pct = (wins / total_games * 100) if total_games > 0 else 0
    
    pts_scored = partidos_played['puntos_benicarlo'].sum()
    pts_allowed = partidos_played['puntos_rival'].sum()
    avg_scored = (pts_scored / total_games) if total_games > 0 else 0
    avg_allowed = (pts_allowed / total_games) if total_games > 0 else 0
    diff_pts = pts_scored - pts_allowed
    pending_current = len(df_partidos[df_partidos['estado'] == 'programado'])

    # Fila flex propia (cards-row): iguala alturas de las 5 tarjetas y apila
    # con aire en móvil; st.columns no estira el contenido entre columnas.
    diff_color = "#34D399" if diff_pts >= 0 else "#F87171"
    tarjetas_kpi = [
        ("Partidos Oficiales", f"{total_games}",
         f"{pending_current} por jugar en 2026/2027", ""),
        ("Balance W / L", f"{wins} - {losses}",
         f"{win_pct:.1f}% de victorias", "color: #6EE7B7; font-weight: 700;"),
        ("Puntos a Favor (PPP)", f"{avg_scored:.1f}",
         f"{pts_scored:,} puntos anotados", ""),
        ("Puntos en Contra (PPP)", f"{avg_allowed:.1f}",
         f"{pts_allowed:,} puntos recibidos", ""),
        ("Diferencial Neto", f"{diff_pts:+d}",
         f"{(diff_pts / total_games if total_games else 0):+.1f} pts / partido",
         f"color: {diff_color};"),
    ]
    tarjetas_html = [_html_plano(f"""
    <div class="metric-container">
        <div class="metric-label">{etiqueta}</div>
        <div class="metric-value" style="{estilo}">{valor}</div>
        <div class="metric-sub">{sub}</div>
    </div>
    """) for etiqueta, valor, sub, estilo in tarjetas_kpi]
    st.markdown(_html_plano(f"""
    <div class="cards-row">
        {''.join(tarjetas_html)}
    </div>
    """), unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    col_graph1, col_graph2 = st.columns([3, 2])

    with col_graph1:
        st.markdown("### Victorias y Derrotas por Temporada")
        
        season_summary = partidos_played.groupby('temporada').agg(
            Victorias=('resultado_benicarlo', lambda x: (x == 'Victoria').sum()),
            Derrotas=('resultado_benicarlo', lambda x: (x == 'Derrota').sum()),
            Total=('partido_id', 'count')
        ).reset_index()

        fig_wl = go.Figure()
        fig_wl.add_trace(go.Bar(
            name='Victorias',
            x=season_summary['temporada'],
            y=season_summary['Victorias'],
            marker_color='#2563EB',
            text=season_summary['Victorias'],
            textposition='auto',
            textfont=dict(color='#FFFFFF'),
            hovertemplate='%{x}<br>Victorias: <b>%{y}</b><extra></extra>',
        ))
        fig_wl.add_trace(go.Bar(
            name='Derrotas',
            x=season_summary['temporada'],
            y=season_summary['Derrotas'],
            marker_color='#64748B',
            text=season_summary['Derrotas'],
            textposition='auto',
            textfont=dict(color='#FFFFFF'),
            hovertemplate='%{x}<br>Derrotas: <b>%{y}</b><extra></extra>',
        ))

        style_fig(fig_wl)
        fig_wl.update_layout(
            barmode='group',
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#F8FAFC", size=11)),
            xaxis=dict(showgrid=False, tickfont=dict(color="#E2E8F0")),
            yaxis=dict(gridcolor="#1E293B", gridwidth=1, tickfont=dict(color="#E2E8F0")),
        )
        st.plotly_chart(fig_wl, **chart_kwargs())

    with col_graph2:
        st.markdown("### Anotación Promedio: Favor vs Contra")
        
        season_pts = partidos_played.groupby('temporada').agg(
            Puntos_Favor=('puntos_benicarlo', 'mean'),
            Puntos_Contra=('puntos_rival', 'mean')
        ).reset_index()
        season_pts['temporada_corta'] = season_pts['temporada'].str[2:4] + '/' + season_pts['temporada'].str[7:9]

        fig_pts = go.Figure()
        fig_pts.add_trace(go.Scatter(
            x=season_pts['temporada_corta'],
            y=season_pts['Puntos_Favor'],
            name='Puntos Favor',
            line=dict(color='#38BDF8', width=3),
            mode='lines+markers',
            customdata=season_pts['temporada'],
            hovertemplate='%{customdata}<br>Favor: <b>%{y:.1f}</b> pts<extra></extra>',
        ))
        fig_pts.add_trace(go.Scatter(
            x=season_pts['temporada_corta'],
            y=season_pts['Puntos_Contra'],
            name='Puntos Contra',
            line=dict(color='#F43F5E', width=2, dash='dot'),
            mode='lines+markers',
            customdata=season_pts['temporada'],
            hovertemplate='%{customdata}<br>Contra: <b>%{y:.1f}</b> pts<extra></extra>',
        ))

        style_fig(fig_pts, hovermode='x unified')
        fig_pts.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#F8FAFC", size=11)),
            xaxis=dict(showgrid=False, tickfont=dict(color="#E2E8F0"), tickangle=0),
            yaxis=dict(gridcolor="#1E293B", gridwidth=1, tickfont=dict(color="#E2E8F0")),
        )
        st.plotly_chart(fig_pts, **chart_kwargs())

    # RENDIMIENTO LOCAL vs VISITANTE (P2 · split de condición)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("### Rendimiento Local vs Visitante")
    st.caption("Balance, anotación y diferencial según se juegue en casa o fuera.")

    split_seasons = ["Todas las temporadas"] + sorted(partidos_played['temporada'].unique().tolist(), reverse=True)
    sel_split = st.selectbox("Temporada", split_seasons, index=0, key="split_season")

    base_split = partidos_played
    if sel_split != "Todas las temporadas":
        base_split = base_split[base_split['temporada'] == sel_split]

    if base_split.empty:
        st.info(f"Sin partidos jugados en {sel_split}.")
    else:
        def _tarjeta_venue(df_venue, titulo):
            n = len(df_venue)
            v = int((df_venue['resultado_benicarlo'] == 'Victoria').sum())
            d = n - v
            pct = (v / n * 100) if n else 0.0
            pf = df_venue['puntos_benicarlo'].mean() if n else 0.0
            pc = df_venue['puntos_rival'].mean() if n else 0.0
            dif = pf - pc
            color = '#34D399' if dif >= 0 else '#F87171'
            return f"""
            <div class="metric-container">
                <div class="metric-label">{titulo} · {n} partidos</div>
                <div class="metric-value">{v} - {d} <span style="font-size: 1.1rem; color: #93C5FD;">{pct:.1f}% victorias</span></div>
                <div class="metric-sub">PPP a favor <b>{pf:.1f}</b> · PPP en contra <b>{pc:.1f}</b></div>
                <div class="metric-sub" style="color: {color}; font-weight: 700;">Diferencial: {dif:+.1f} pts / partido</div>
            </div>
            """

        casa_df = base_split[base_split['es_benicarlo_local'] == 1]
        fuera_df = base_split[base_split['es_benicarlo_local'] == 0]

        st.markdown(_html_plano(f"""
        <div class="cards-row">
            {_tarjeta_venue(casa_df, "CASA")}
            {_tarjeta_venue(fuera_df, "FUERA")}
        </div>
        """), unsafe_allow_html=True)

        # Narrativa: la ventaja de campo medida en puntos porcentuales
        if not casa_df.empty and not fuera_df.empty:
            pct_casa = (casa_df['resultado_benicarlo'] == 'Victoria').mean() * 100
            pct_fuera = (fuera_df['resultado_benicarlo'] == 'Victoria').mean() * 100
            delta = pct_casa - pct_fuera
            if abs(delta) < 1:
                txt = "Sin ventaja de campo apreciable: el porcentaje de victorias es prácticamente igual en casa y fuera."
            elif delta > 0:
                txt = (f"Ventaja de campo: {delta:.1f} puntos porcentuales más de victorias en casa "
                       f"({pct_casa:.1f}% en casa vs {pct_fuera:.1f}% fuera).")
            else:
                txt = (f"Ventaja de campo invertida: {abs(delta):.1f} puntos porcentuales más de victorias fuera "
                       f"({pct_fuera:.1f}% fuera vs {pct_casa:.1f}% en casa).")
            st.caption(txt)

    # ENFRENTAMIENTOS DIRECTOS (P2 · head-to-head por rival)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("### Enfrentamientos Directos")
    st.caption("Historial completo contra cada rival: balance, medias anotadoras y últimos cruces.")

    h2h_base = partidos_played.copy()
    if 'equipo_rival_id' in h2h_base.columns:
        h2h_base['_rival_id'] = h2h_base['equipo_rival_id'].fillna('')
    else:
        h2h_base['_rival_id'] = h2h_base['equipo_rival']
    # Nombre visible: la variante más frecuente del rival canónico
    nombres_rival = (h2h_base.groupby('_rival_id')['equipo_rival']
                     .agg(lambda s: s.value_counts().index[0]))
    h2h_base['_rival'] = h2h_base['_rival_id'].map(nombres_rival)

    conteo_rivales = h2h_base['_rival'].value_counts()
    opciones_rivales = sorted(h2h_base['_rival'].dropna().unique())
    sel_rival = st.selectbox(
        "Rival",
        opciones_rivales,
        index=opciones_rivales.index(conteo_rivales.index[0]),
        key="h2h_rival",
    )

    h2h = h2h_base[h2h_base['_rival'] == sel_rival].sort_values('fecha', ascending=False)
    if h2h.empty:
        st.info(f"No hay enfrentamientos registrados contra {sel_rival}.")
    else:
        n_h2h = len(h2h)
        v_h2h = int((h2h['resultado_benicarlo'] == 'Victoria').sum())
        d_h2h = n_h2h - v_h2h
        pct_h2h = v_h2h / n_h2h * 100
        pf_h2h = h2h['puntos_benicarlo'].mean()
        pc_h2h = h2h['puntos_rival'].mean()
        dif_h2h = pf_h2h - pc_h2h
        color_h2h = '#34D399' if dif_h2h >= 0 else '#F87171'
        ultimo = h2h.iloc[0]
        ult_fecha = ultimo['fecha'].strftime('%d/%m/%Y') if pd.notnull(ultimo['fecha']) else 'S/F'
        ult_txt = (f"{ult_fecha} · "
                   f"{int(ultimo['puntos_benicarlo'])}-{int(ultimo['puntos_rival'])} "
                   f"({ultimo['resultado_benicarlo'].lower()})")

        col_h2h_card, col_h2h_tabla = st.columns([2, 3])
        with col_h2h_card:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Historial vs {sel_rival}</div>
                <div class="metric-value">{v_h2h} - {d_h2h} <span style="font-size: 1.1rem; color: #93C5FD;">{pct_h2h:.1f}% victorias</span></div>
                <div class="metric-sub">PPP a favor <b>{pf_h2h:.1f}</b> · PPP en contra <b>{pc_h2h:.1f}</b></div>
                <div class="metric-sub" style="color: {color_h2h}; font-weight: 700;">Diferencial: {dif_h2h:+.1f} pts / partido</div>
                <div class="metric-sub">Último cruce: {ult_txt}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_h2h_tabla:
            st.markdown("### Últimos cruces")
            ultimos_h2h = h2h.head(8)
            tabla_h2h = pd.DataFrame({
                'Fecha': ultimos_h2h['fecha'].dt.strftime('%d/%m/%Y').fillna('S/F'),
                'Temporada': ultimos_h2h['temporada'],
                'Condición': np.where(ultimos_h2h['es_benicarlo_local'] == 1, 'Casa', 'Fuera'),
                'Marcador': ultimos_h2h.apply(
                    lambda r: f"{int(r['puntos_benicarlo'])} - {int(r['puntos_rival'])}", axis=1),
                'Resultado': ultimos_h2h['resultado_benicarlo'],
            })
            st.dataframe(tabla_h2h, hide_index=True, width="stretch")

    # NARRATIVA DE PARTIDO (P2 · cerrados, rachas y remontadas)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("### Narrativa de Partido")
    st.caption("Los partidos que se definen al final: cerrados (±5 pts), rachas y remontadas al descanso.")

    narr = partidos_played.sort_values(['fecha', 'partido_id']).copy()

    def _fmt_fecha(f):
        return f.strftime('%d/%m/%Y') if pd.notnull(f) else 'S/F'

    # --- Partidos cerrados (margen <= 5) ---
    cerrados = narr[narr['diferencia_puntos'].abs() <= 5]
    n_cer = len(cerrados)
    v_cer = int((cerrados['resultado_benicarlo'] == 'Victoria').sum())
    d_cer = n_cer - v_cer
    pct_cer = (v_cer / n_cer * 100) if n_cer else 0.0
    pf_cer = cerrados['puntos_benicarlo'].mean() if n_cer else 0.0
    pc_cer = cerrados['puntos_rival'].mean() if n_cer else 0.0
    dif_cer = pf_cer - pc_cer
    color_cer = '#34D399' if dif_cer >= 0 else '#F87171'

    # --- Rachas (resultados consecutivos por fecha) ---
    res_n = narr['resultado_benicarlo'].tolist()
    fechas_n = narr['fecha'].tolist()

    def _mejor_racha(tipo):
        mejor = act = fin = 0
        for i, r in enumerate(res_n):
            if r == tipo:
                act += 1
                if act > mejor:
                    mejor, fin = act, i
            else:
                act = 0
        return mejor, fin

    racha_v, fin_v = _mejor_racha('Victoria')
    racha_d, fin_d = _mejor_racha('Derrota')
    act_tipo = res_n[-1] if res_n else ''
    act_n = 0
    for r in reversed(res_n):
        if r == act_tipo:
            act_n += 1
        else:
            break
    act_desde = _fmt_fecha(fechas_n[len(fechas_n) - act_n]) if act_n else 'S/F'

    # --- Remontadas: victoria tras ir perdiendo al descanso ---
    beni_q = df_cuartos[df_cuartos['es_benicarlo'] == 1].set_index('partido_id')
    riv_q = df_cuartos[df_cuartos['es_benicarlo'] == 0].set_index('partido_id')
    descanso = pd.DataFrame({
        'desc_beni': beni_q['q1'] + beni_q['q2'],
        'desc_riv': riv_q['q1'] + riv_q['q2'],
    })
    narr_ix = narr.set_index('partido_id').join(descanso)
    remontadas = narr_ix[(narr_ix['resultado_benicarlo'] == 'Victoria') &
                         (narr_ix['desc_beni'] < narr_ix['desc_riv'])].copy()
    remontadas['desventaja'] = remontadas['desc_riv'] - remontadas['desc_beni']
    n_rem = len(remontadas)
    n_vic = int((narr['resultado_benicarlo'] == 'Victoria').sum())
    pct_rem = (n_rem / n_vic * 100) if n_vic else 0.0

    tipo_actual = 'victoria' if act_tipo == 'Victoria' else 'derrota'
    if act_n != 1:
        tipo_actual += 's'
    mayor_rem = remontadas.sort_values('desventaja', ascending=False).iloc[0] if n_rem else None
    ultima_rem = remontadas.sort_values('fecha', ascending=False).iloc[0] if n_rem else None
    linea_mayor = (f"Mayor: -{int(mayor_rem['desventaja'])} al descanso → "
                   f"{int(mayor_rem['puntos_benicarlo'])}-{int(mayor_rem['puntos_rival'])} vs {mayor_rem['equipo_rival']}"
                   if n_rem else 'Sin remontadas registradas')
    linea_ultima = (f"Última: {_fmt_fecha(ultima_rem['fecha'])} vs {ultima_rem['equipo_rival']}"
                    if n_rem else '')

    # Fila flex propia: iguala alturas de forma fiable (los wrappers de
    # st.columns no estiran el contenido de las tarjetas)
    st.markdown(_html_plano(f"""
    <div class="cards-row">
        <div class="metric-container">
            <div class="metric-label">Partidos cerrados (±5)</div>
            <div class="metric-value">{v_cer} - {d_cer} <span style="font-size: 1.1rem; color: #93C5FD;">{pct_cer:.1f}% victorias</span></div>
            <div class="metric-sub">{n_cer} de {len(narr)} partidos ({n_cer / len(narr) * 100:.1f}%)</div>
            <div class="metric-sub">PPP a favor <b>{pf_cer:.1f}</b> · PPP en contra <b>{pc_cer:.1f}</b></div>
            <div class="metric-sub" style="color: {color_cer}; font-weight: 700;">Diferencial: {dif_cer:+.1f} pts / partido</div>
        </div>
        <div class="metric-container">
            <div class="metric-label">Mayor racha de victorias</div>
            <div class="metric-value">{racha_v} seguidas</div>
            <div class="metric-sub">hasta el {_fmt_fecha(fechas_n[fin_v])}</div>
            <div class="metric-sub">Racha actual: <b>{act_n} {tipo_actual}</b> desde el {act_desde}</div>
            <div class="metric-sub" style="color: #F87171; font-weight: 700;">Mayor racha de derrotas: {racha_d} (hasta el {_fmt_fecha(fechas_n[fin_d])})</div>
        </div>
        <div class="metric-container">
            <div class="metric-label">Remontadas al descanso</div>
            <div class="metric-value">{n_rem} <span style="font-size: 1.1rem; color: #93C5FD;">{pct_rem:.1f}% de las victorias</span></div>
            <div class="metric-sub">{linea_mayor}</div>
            <div class="metric-sub">{linea_ultima}</div>
        </div>
    </div>
    """), unsafe_allow_html=True)

    if n_rem:
        st.markdown("### Mayores Remontadas")
        top_rem = remontadas.sort_values('desventaja', ascending=False).head(5)
        tabla_rem = pd.DataFrame({
            'Fecha': top_rem['fecha'].apply(_fmt_fecha),
            'Rival': top_rem['equipo_rival'],
            'Condición': np.where(top_rem['es_benicarlo_local'] == 1, 'Casa', 'Fuera'),
            'Al descanso': top_rem.apply(
                lambda r: f"{int(r['desc_beni'])} - {int(r['desc_riv'])} (-{int(r['desventaja'])})", axis=1),
            'Final': top_rem.apply(
                lambda r: f"{int(r['puntos_benicarlo'])} - {int(r['puntos_rival'])}", axis=1),
        })
        st.dataframe(tabla_rem, hide_index=True, width="stretch")

    # TRAYECTORIA POR TEMPORADA (P2 · punto 5: contexto de liga)
    if df_temporadas is not None and not df_temporadas.empty:
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        st.markdown("### Trayectoria por Temporada")

        filas = []
        for _, t in df_temporadas.sort_values('temporada', ascending=False).iterrows():
            clase, texto = hito_badge(t.get('resultado_hito'), t.get('fase_alcanzada', ''))
            badge = (f'<span class="hito-badge {clase}">{texto}</span>' if clase
                     else '<span style="color:#475569;">—</span>')
            pos = f"{int(t['posicion_grupo'])}º" if pd.notnull(t.get('posicion_grupo')) else '—'
            fase = t.get('fase_alcanzada') or ''
            narrativa = t.get('hito') or (fase if fase not in ('', 'Liga Regular') else '—')
            filas.append(_html_plano(f"""
            <tr>
                <td class="c-temp" data-label="Temporada">{t['temporada']}</td>
                <td class="c-meta" data-label="Competición">{t.get('competicion') or ''} · {t.get('grupo') or ''}</td>
                <td class="c-pos" data-label="Pos">{pos}</td>
                <td class="c-bal" data-label="Balance">{int(t['balance_v'])}-{int(t['balance_d'])}</td>
                <td class="c-hito" data-label="Hito">{narrativa}</td>
                <td class="c-badge" data-label="Estado">{badge}</td>
            </tr>
            """))
        st.markdown(_html_plano(f"""
        <div class="tray-wrap">
        <table class="tray-table">
            <colgroup>
                <col style="width: 12%">
                <col style="width: 27%">
                <col style="width: 7%">
                <col style="width: 10%">
                <col style="width: 29%">
                <col style="width: 15%">
            </colgroup>
            <thead>
                <tr>
                    <th>TEMPORADA</th>
                    <th class="c-meta">COMPETICIÓN · GRUPO</th>
                    <th class="c-pos">POS</th>
                    <th class="c-bal">BALANCE</th>
                    <th class="c-hito">HITO</th>
                    <th class="c-badge">ESTADO</th>
                </tr>
            </thead>
            <tbody>
            {''.join(filas)}
            </tbody>
        </table>
        </div>
        """), unsafe_allow_html=True)

    # CALENDARIO DE PRÓXIMOS PARTIDOS: Strictly temporada actual 2026/2027
    upcoming_2026 = df_partidos[
        (df_partidos['temporada'] == '2026/2027') & 
        (df_partidos['estado'] == 'programado')
    ].sort_values('fecha').head(6)

    if not upcoming_2026.empty:
        st.markdown("### Calendario de Próximos Partidos (Segunda FEB · 2026/2027)")
        # Fila flex propia (patrón de la Narrativa): en móvil las tarjetas se
        # apilan con gap real, sin el contacto borde con borde de st.columns.
        tarjetas = []
        for _, row in upcoming_2026.iterrows():
            date_str = row['fecha'].strftime('%d/%m/%Y') if pd.notnull(row['fecha']) else 'S/F'
            is_home = row['es_benicarlo_local'] == 1
            cond = "CASA" if is_home else "FUERA"
            tarjetas.append(_html_plano(f"""
            <div class="scheduled-card">
                <div class="scheduled-jornada">{row['jornada_nombre'].split('(')[0]} · {cond}</div>
                <div class="scheduled-rival">vs {row['equipo_rival']}</div>
                <div class="scheduled-info">📅 {date_str}</div>
                <div class="scheduled-info" style="color: #93C5FD;">⏰ {row['hora'] or '18:00'}</div>
            </div>
            """))
        st.markdown(_html_plano(f"""
        <div class="cards-row">
            {''.join(tarjetas)}
        </div>
        """), unsafe_allow_html=True)

