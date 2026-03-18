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

# Enveloppes fiscales / supports disponibles
ENVELOPPES = [
    "PEA",
    "CTO",
    "Assurance vie",
    "Livret réglementé",
    "Crypto (wallet/exchange)",
    "Compte courant",
]

# Types de biens immobiliers (pour le détail immobilier)
TYPE_BIEN_OPTIONS = {
    "appartement": "Appartement",
    "maison": "Maison",
    "terrain": "Terrain",
    "local_commercial": "Local commercial",
    "parking": "Parking",
    "autre": "Autre"
}

# Couleur fixe par catégorie
CATEGORY_COLOR_MAP = {
    "Actions & Fonds": "#85357d",
    "Crypto":          "#6f50e5",
    "Livrets":         "#486df0",
    "Immobilier":      "#d6475d",
    "Fonds euros":     "#f08696",
    "Emprunts":        "#75cbd1",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#0A0B0E",
    plot_bgcolor="#141519",
    font=dict(color="#F9FAFB", family="Inter, system-ui, sans-serif"),
    xaxis=dict(
        gridcolor="#1F2937",
        showgrid=False,
        showline=False,
        zeroline=False,
        showticklabels=True,
    ),    yaxis=dict(
        gridcolor="#1F2937",
        showgrid=True,
        showline=False,
        zeroline=False,
        showticklabels=True,
    ),    margin=dict(l=0, r=0, t=0, b=0),
    hovermode=False,
    showlegend=False,
)

# ── Chemins des fichiers de données ──────────────────────────────────────────

DB_PATH = "data/patrimoine.db"

# Chemins CSV (utilisés par le script de migration uniquement)
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


# ── Indices de comparaison disponibles ───────────────────────────────────────

BENCHMARK_OPTIONS = {
    "Aucun":       None,
    "MSCI World":  "URTH",
    "S&P 500":     "SPY",
    "CAC 40":      "^FCHI",
    "Bitcoin":     "BTC-USD",
    "Ethereum":    "ETH-USD",
}

BENCHMARK_COLOR = "#F59E0B"  # jaune