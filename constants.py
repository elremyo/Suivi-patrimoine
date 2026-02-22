CATEGORIES_ASSETS = [
    "Immobilier",
    "Actions",
    "Obligations",
    "Liquidités",
    "SCPI",
    "Crypto",
    "ETF",
    "Livrets",
]

CATEGORY_COLORS = [
    "#4C9BE8", "#36C28A", "#F5A623", "#E8547A",
    "#A78BFA", "#34D8E0", "#F97316", "#8BC34A",
]

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#1A1D27",
    plot_bgcolor="#1A1D27",
    font=dict(color="#E8EAF0", family="sans-serif"),
    xaxis=dict(gridcolor="#2A2D3A", linecolor="#2A2D3A"),
    yaxis=dict(gridcolor="#2A2D3A", linecolor="#2A2D3A"),
    margin=dict(l=0, r=0, t=0, b=0),
    hovermode=False,
)