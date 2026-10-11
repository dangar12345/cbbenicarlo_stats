"""Tema visual del Analytics Hub (CSS inyectado por app.py)."""

CSS = """<style>
    @import url('https://fonts.googleapis.com/css2?family=Chivo:ital,wght@0,300..900;1,300..900&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, .stApp {
        font-family: 'Chivo', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #F8FAFC;
    }

    .stMarkdown, .stMarkdown p, label {
        font-family: 'Chivo', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: #F8FAFC !important;
    }

    /* Preserve Streamlit icon fonts */
    [data-testid="stIconMaterial"], .material-symbols-rounded, .material-symbols-outlined, [class*="material-symbols"] {
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
        font-weight: normal !important;
    }

    .stApp {
        background-color: #080D1A;
    }

    /* Clean top header: eliminate black mismatch, hide unnecessary deploy button */
    header[data-testid="stHeader"] {
        background-color: #080D1A !important;
        border-bottom: 1px solid #1E293B !important;
    }

    .stDeployButton,
    div[data-testid="stAppDeployButton"] {
        display: none !important;
    }

    /* High-contrast three-dots menu popup */
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[data-baseweb="menu"] {
        background-color: #0F172A !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="menu"] li, div[data-baseweb="menu"] div, div[data-baseweb="menu"] span {
        color: #F8FAFC !important;
    }
    div[data-baseweb="menu"] li:hover {
        background-color: #1E293B !important;
    }

    /* Headings */
    h1, h2, h3, h4 {
        font-family: 'Chivo', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em !important;
        color: #FFFFFF !important;
    }

    /* Subtitles and captions with high contrast */
    .stCaption, caption {
        color: #CBD5E1 !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
    }

    /* High-contrast Metric Cards */
    .metric-container {
        background: #111A2E;
        border: 1px solid #233554;
        border-radius: 8px;
        padding: 18px 20px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
        height: 100%;
    }
    /* Para que height:100% funcione, toda la cadena de ancestros dentro de la
       fila de columnas debe tener altura definida (el DOM de Streamlit monta
       4-5 wrappers por elemento). */
    div[data-testid="stHorizontalBlock"] > div:has(.metric-container),
    div[data-testid="stHorizontalBlock"] > div:has(.metric-container) *:has(.metric-container) {
        height: 100%;
    }

    /* Fila de tarjetas con altura igualada (flex propio, sin wrappers) */
    .cards-row {
        display: flex;
        align-items: stretch;
        gap: 24px;
    }
    .cards-row .metric-container {
        flex: 1 1 0;
        height: auto; /* el height:100% base bloquea el stretch de flex */
    }
    .cards-row .scheduled-card {
        flex: 1 1 0;
    }
    @media (max-width: 720px) {
        .cards-row {
            flex-direction: column;
        }
    }
    .metric-label {
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #93C5FD;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 900;
        color: #FFFFFF;
        line-height: 1.1;
        font-feature-settings: "tnum" 1;
    }
    .metric-sub {
        font-size: 0.85rem;
        color: #E2E8F0;
        margin-top: 6px;
        font-weight: 500;
        font-feature-settings: "tnum" 1;
    }

    /* Scoreboard display */
    .scoreboard {
        background: #0F172A;
        border: 1px solid #3B82F6;
        border-radius: 12px;
        padding: 26px;
        margin-bottom: 24px;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45);
    }
    .team-name {
        font-size: 1.35rem;
        font-weight: 800;
        letter-spacing: -0.01em;
        color: #FFFFFF;
        min-width: 0;
        overflow-wrap: break-word;
        text-wrap: balance;
    }
    .team-score {
        font-size: 3.2rem;
        font-weight: 900;
        color: #FFFFFF;
        font-feature-settings: "tnum" 1;
    }
    /* Marcador en grid de filas fijas: los dos nombres comparten fila y los dos
       marcadores otra, así un nombre largo (3 líneas) no desplaza su cifra. */
    .sb-grid {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        grid-template-areas:
            "nameL dash nameR"
            "scoreL dash scoreR";
        column-gap: 12px;
        align-items: start;
        text-align: center;
    }
    .sb-name-l { grid-area: nameL; }
    .sb-name-r { grid-area: nameR; }
    .sb-score-l { grid-area: scoreL; }
    .sb-score-r { grid-area: scoreR; }
    .sb-dash {
        grid-area: dash;
        align-self: center;
        font-size: 2rem;
        font-weight: 300;
        color: #64748B;
        padding: 0 8px;
    }

    /* High-contrast Badges */
    .badge-win {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 6px;
        background: #047857;
        color: #ECFDF5 !important;
        font-size: 0.82rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-loss {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 6px;
        background: #B91C1C;
        color: #FEF2F2 !important;
        font-size: 0.82rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-pending {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 6px;
        background: #1D4ED8;
        color: #EFF6FF !important;
        font-size: 0.82rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Scheduled Match Card */
    .scheduled-card {
        background: #111A2E;
        border: 1px solid #2563EB;
        border-radius: 8px;
        padding: 16px;
        min-height: 145px;
    }
    .scheduled-jornada {
        font-size: 0.78rem;
        font-weight: 800;
        color: #60A5FA;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .scheduled-rival {
        font-size: 1.05rem;
        font-weight: 800;
        color: #FFFFFF;
        margin: 8px 0;
    }
    .scheduled-info {
        font-size: 0.85rem;
        color: #E2E8F0;
        font-weight: 500;
    }

    /* Dataframe high-contrast */
    div[data-testid="stDataFrame"] {
        border: 1px solid #334155;
        border-radius: 8px;
        background: #0F172A;
    }

    /* Sidebar customization */
    section[data-testid="stSidebar"] {
        background-color: #0A101F;
        border-right: 1px solid #1E293B;
    }
    section[data-testid="stSidebar"] hr {
        margin: 0.5rem 0 1rem 0;
    }

    /* Selectbox, Inputs, Radio */
    .stSelectbox label, .stTextInput label, .stRadio label {
        color: #F8FAFC !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
    }

    /* Form controls: consistent dark surface + visible hover/focus */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    textarea[data-testid="stTextInput"] {
        background-color: #0F172A !important;
        border: 1px solid #233554 !important;
        border-radius: 8px !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    div[data-baseweb="select"] > div:hover,
    div[data-baseweb="input"] > div:hover,
    textarea[data-testid="stTextInput"]:hover {
        border-color: #3B82F6 !important;
    }
    div[data-baseweb="select"]:focus-within > div,
    div[data-baseweb="input"]:focus-within > div,
    textarea[data-testid="stTextInput"]:focus {
        border-color: #60A5FA !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25) !important;
    }
    div[data-baseweb="select"] svg {
        fill: #93C5FD !important;
    }

    /* Tabs */
    button[data-baseweb="tab"] {
        background: transparent !important;
        border-radius: 8px 8px 0 0 !important;
    }
    button[data-baseweb="tab"]:hover p {
        color: #93C5FD !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] p {
        color: #60A5FA !important;
    }
    div[data-baseweb="tab-border"] {
        background-color: #2563EB !important;
    }

    /* Dataframe: dark surface, tight edges */
    div[data-testid="stDataFrame"] {
        overflow: hidden;
    }

    /* Plotly hover tooltips: readable regardless of theme merging */
    .hoverlayer .hovertext rect {
        fill: #0F172A !important;
        stroke: #3B82F6 !important;
    }
    .hoverlayer .hovertext text {
        fill: #F8FAFC !important;
        font-family: 'Chivo', sans-serif !important;
    }

    /* Browser surfaces: selection, caret, scrollbars, focus */
    ::selection {
        background: #2563EB;
        color: #FFFFFF;
    }
    input, textarea {
        caret-color: #60A5FA;
    }
    :focus-visible {
        outline: 2px solid #60A5FA;
        outline-offset: 2px;
    }
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    ::-webkit-scrollbar-track {
        background: #0A101F;
    }
    ::-webkit-scrollbar-thumb {
        background: #24344F;
        border-radius: 6px;
        border: 2px solid #0A101F;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #33507F;
    }
    html {
        scrollbar-color: #24344F #0A101F;
        scrollbar-width: thin;
    }

    /* Footer link-ish affordances */
    a {
        color: #60A5FA;
        text-underline-offset: 3px;
    }
    a:hover {
        color: #93C5FD;
    }

    /* P2 · Contexto de liga: tira de trayectoria por temporada */
    .tray-wrap {
        overflow-x: auto;
    }
    table.tray-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
    }
    .tray-table th {
        text-align: left;
        font-size: 0.72rem;
        letter-spacing: 0.06em;
        color: #93C5FD;
        font-weight: 800;
        padding: 8px 12px;
        border-top: none;
        border-left: none;
        border-right: none;
        border-bottom: 1px solid #233554;
    }
    .tray-table td {
        padding: 11px 12px;
        border-top: none;
        border-left: none;
        border-right: none;
        border-bottom: 1px solid #16233D;
        color: #CBD5E1;
        font-size: 0.875rem;
        vertical-align: middle;
    }
    .tray-table tbody tr:hover td {
        background: #0F172A;
    }
    .tray-table .c-temp {
        color: #FFFFFF;
        font-weight: 800;
        font-feature-settings: "tnum" 1;
    }
    .tray-table .c-meta {
        color: #94A3B8;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .tray-table .c-pos {
        color: #60A5FA;
        font-weight: 800;
        font-size: 1.05rem;
        text-align: right;
        font-feature-settings: "tnum" 1;
    }
    .tray-table .c-bal {
        text-align: right;
        font-feature-settings: "tnum" 1;
    }
    .tray-table .c-hito {
        color: #CBD5E1;
    }
    .tray-table .c-badge {
        text-align: right;
    }
    .tray-table .c-badge .hito-badge {
        white-space: nowrap;
    }
    .tray-table th.c-pos,
    .tray-table th.c-bal,
    .tray-table th.c-badge {
        text-align: right;
    }
    @media (max-width: 720px) {
        /* Filas como tarjetas: la tabla con anchos fijos no cabe en móvil.
           Ojo: el CSS de Streamlit fija display:table en <table>; sin
           !important los hijos bloque se envuelven en celdas anónimas y el
           layout colapsa. */
        .tray-table thead {
            display: none !important;
        }
        .tray-table,
        .tray-table tbody,
        .tray-table tr {
            display: block !important;
            width: 100% !important;
        }
        .tray-table tr {
            border: 1px solid #1E293B;
            border-radius: 8px;
            margin-bottom: 10px;
            padding: 8px 4px;
            box-sizing: border-box;
        }
        .tray-table tbody tr:hover td {
            background: transparent;
        }
        .tray-table td {
            display: flex !important;
            width: auto !important;
            border-bottom: none;
            padding: 4px 12px;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            text-align: right;
            font-size: 0.84rem;
        }
        .tray-table td::before {
            content: attr(data-label);
            color: #93C5FD;
            font-size: 0.68rem;
            letter-spacing: 0.05em;
            font-weight: 800;
            text-transform: uppercase;
            text-align: left;
            flex: 0 0 auto;
        }
        .tray-table td.c-temp {
            justify-content: flex-start;
            font-size: 1rem;
        }
        .tray-table td.c-temp::before {
            display: none;
        }
        .tray-table .c-meta {
            display: flex;
            white-space: normal;
        }
        .tray-table .c-badge {
            justify-content: space-between;
        }
    }
    .hito-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        white-space: nowrap;
    }
    .hito-ascenso, .hito-campeon {
        background: #047857;
        color: #ECFDF5;
    }
    .hito-eliminado_playoff {
        background: #1D4ED8;
        color: #EFF6FF;
    }
    .hito-permanencia {
        background: #B45309;
        color: #FFFBEB;
    }
    .hito-cancelada {
        background: #334155;
        color: #E2E8F0;
    }
    .hito-en_curso {
        background: rgba(37, 99, 235, 0.12);
        border: 1px solid #2563EB;
        color: #93C5FD;
    }

    /* Franja de contexto de liga bajo el marcador */
    .match-context {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
        margin: 10px 0 4px 0;
        color: #94A3B8;
        font-size: 0.85rem;
    }
    .match-context .ctx-fase {
        color: #93C5FD;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-size: 0.78rem;
    }
    /* Cada parte lleva su separador como sufijo con espacio irrompible: el
       "·" viaja con el texto y nunca empieza una línea al envolver. */
    .match-context .ctx-item {
        min-width: 0;
    }

    /* Móvil: sin anclas de título ni modebar de Plotly (táctil, sin hover) */
    @media (max-width: 720px) {
        .stHeadingAnchor {
            display: none !important;
        }
        .modebar-container {
            display: none !important;
        }
        .team-name {
            font-size: 1.05rem;
        }
        .team-score {
            font-size: 2.5rem;
        }
        .scoreboard {
            padding: 18px 14px;
        }
        /* Columnas apiladas: aire real entre tarjetas (el gap por defecto de
           16px es menor que el padding interno y las cajas se ven pegadas) */
        div[data-testid="stHorizontalBlock"] {
            gap: 24px !important;
            row-gap: 24px !important;
        }
    }

    /* Tablet / ventanas estrechas: sin este mínimo, las filas de 4-5 tarjetas
       se aplastan en columnas de ~105-150px. Con mínimo de 280px envuelven a
       2 por fila y las filas de gráficas [3,2] mantienen su proporción. */
    @media (min-width: 641px) and (max-width: 1023px) {
        div[data-testid="stColumn"] {
            min-width: 280px !important;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 24px !important;
            row-gap: 24px !important;
        }
    }
</style>"""
