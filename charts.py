"""Estilo compartido de gráficas (lienzo oscuro, hover, modo de hover)."""

# --- SHARED CHART STYLING ---
HOVERLABEL = dict(
    bgcolor="#0F172A",
    bordercolor="#3B82F6",
    font=dict(family="Chivo", color="#F8FAFC", size=13),
)

def style_fig(fig, height=340, hovermode=None):
    """Dark transparent canvas + readable hover tooltips for every chart."""
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Chivo", color="#F8FAFC"),
        hoverlabel=HOVERLABEL,
        height=height,
    )
    if hovermode:
        fig.update_layout(hovermode=hovermode)
    return fig

def chart_kwargs():
    """Keep the figure's own dark template instead of Streamlit's light one."""
    return dict(theme=None, width="stretch")
