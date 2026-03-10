#  Suivi de patrimoine
Application web personnelle pour suivre l'évolution de son patrimoine dans le temps. Construite avec Streamlit, elle tourne en local et stocke tout dans une base de données SQLite — pas de compte, pas de cloud, pas de tierce partie avec accès à vos données.


## Ce que ça fait
Le patrimoine est divisé en deux types d'actifs. Les actifs financiers (actions, ETF, crypto) sont synchronisés automatiquement via Yahoo Finance à partir d'un ticker et d'une quantité détenue. Les actifs manuels (livrets, immobilier, fonds euros) sont mis à jour à la main.
L'application conserve un historique de chaque actif et permet de visualiser l'évolution du patrimoine total ou par catégorie sur différentes périodes.

## Stack
- Python / Streamlit
- pandas pour les calculs
- yfinance pour les prix en temps réel
- Plotly pour les graphiques
- Stockage local en base de données SQLite

## Lancer le projet

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

Projet personnel, pas de roadmap publique, ni de support, ni de contributions.
