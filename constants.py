CATEGORIES_ASSETS = [
    "Actions & Fonds",
    "Crypto",
    "Livrets",
    "Immobilier",
    "Fonds euros",
]

# Catégories dont le montant est calculé automatiquement (ticker + quantité)
CATEGORIES_AUTO = {"Actions & Fonds", "Crypto"}

# Catégories à saisie manuelle du montant
CATEGORIES_MANUAL = {"Livrets", "Immobilier", "Fonds euros"}

CATEGORY_COLORS = [
    "#A4E84C", "#85357d", "#486df0", "#6f50e5", "#A78BFA",
]

# Couleur fixe par catégorie (indépendant de l'ordre d'affichage)
CATEGORY_COLOR_MAP = {
    "Actions & Fonds": "#85357d",
    "Crypto":          "#6f50e5",
    "Livrets":         "#486df0",
    "Immobilier":      "#E8547A",
    "Fonds euros":     "#A78BFA",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#1A1D27",
    plot_bgcolor="#1A1D27",
    font=dict(color="#E8EAF0", family="sans-serif"),
    xaxis=dict(gridcolor="#2A2D3A", linecolor="#2A2D3A"),
    yaxis=dict(gridcolor="#2A2D3A", linecolor="#2A2D3A"),
    margin=dict(l=0, r=0, t=0, b=0),
    hovermode=False,
)

# ── Chemins des fichiers de données ──────────────────────────────────────────

DATA_PATH       = "data/patrimoine.csv"
HISTORIQUE_PATH = "data/historique.csv"
POSITIONS_PATH  = "data/positions.csv"

# ── Cache yfinance ────────────────────────────────────────────────────────────

CACHE_TTL_SECONDS = 3 * 3600  # 3 heures

# ── Périodes disponibles dans le tab Historique ───────────────────────────────
# Format : label → (période yfinance, nb jours de filtre — None = pas de filtre)

PERIOD_OPTIONS = {
    "1S":  ("5d",  7),
    "1M":  ("1mo", 30),
    "3M":  ("3mo", 90),
    "6M":  ("6mo", 180),
    "1A":  ("1y",  365),
    "Max": ("max", None),
}

PERIOD_DEFAULT = "3M"