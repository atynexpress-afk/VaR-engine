# VaR Engine — Mesure du risque de marché

Application interactive de calcul de la **Value at Risk (VaR)** et de l'**Expected Shortfall (ES)** d'un portefeuille d'actions, avec **backtesting réglementaire** et **stress tests**.

**Démo en ligne :** [lien vers l'application](https://var-engine-haroun-abbes.streamlit.app) 

Projet réalisé dans le cadre du Master 2 Ingénierie des risques économiques et financiers (finance quantitative et actuariat). Il est conçu comme un **modèle challenger** : une réimplémentation indépendante des méthodes utilisées en banque pour mesurer et valider le risque de marché.

---

## Fonctionnalités

- **Portefeuille paramétrable** : actions du CAC 40 ou tout ticker Yahoo Finance, poids rééquilibrés automatiquement, période et montant au choix.
- **Conversion en euros** : les titres cotés dans une autre devise (dollar, livre, franc suisse…) sont convertis au taux de change de chaque jour, ce qui intègre le risque de change dans la VaR.
- **Six méthodes de VaR et d'ES** : historique, paramétrique (loi normale et loi de Student), Monte Carlo avec corrélations, EWMA (RiskMetrics) et historique filtrée (FHS).
- **Tous les paramètres modifiables** : niveau de confiance, horizon, degrés de liberté, nombre de simulations, graine aléatoire, facteur de lissage λ, fenêtre d'estimation.
- **Backtesting** : VaR et ES glissantes hors échantillon, tests de Kupiec et de Christoffersen, backtest de l'ES d'Acerbi et Szekely, feux tricolores de Bâle, et conclusion en langage clair (quel modèle passe les tests, et pourquoi les autres échouent).
- **Stress tests** : crises historiques (Lehman 2008, dette européenne 2011, Covid 2020, Ukraine 2022) et chocs hypothétiques définis par l'utilisateur.
- **Diagnostic des queues de distribution** : histogramme comparé à la loi normale, QQ-plot, skewness et kurtosis.
- **Graphiques interactifs** et définition de chaque notion accessible depuis l'interface.
- **Export Excel** des résultats : paramètres, VaR et ES, backtesting et stress tests, une feuille par thème.
- **Guide de démarrage** pour les utilisateurs qui découvrent la finance.

## Méthodologie

| Méthode | Principe | Formule |
|---|---|---|
| Historique | Quantile empirique des pertes observées | VaR = quantile à α des pertes |
| Paramétrique normale | Rendements gaussiens | VaR = −μ + σ·z_α |
| Paramétrique Student | Queues épaisses, variance ajustée à σ | VaR = −μ + σ·√((ν−2)/ν)·t_α,ν |
| Monte Carlo | Scénarios corrélés par décomposition de Cholesky (Σ = L·Lᵀ) | X = μ + Z·Lᵀ, puis quantile |
| EWMA (RiskMetrics) | Volatilité conditionnelle, plus de poids aux jours récents | σ²ₜ₊₁ = λ·σ²ₜ + (1−λ)·r²ₜ, VaR = σₜ₊₁·z_α |
| Historique filtrée (FHS) | Chocs standardisés par la volatilité EWMA, puis remis à l'échelle | VaR = σₜ₊₁ · quantile à α de (−rₜ/σₜ) |

- **Expected Shortfall** : perte moyenne au-delà de la VaR, avec formules fermées pour les lois normale et de Student.
- **Changement d'horizon** : règle de la racine du temps, VaR(h) = VaR(1) × √h.
- **Rendements** : rendements simples, qui s'agrègent linéairement entre actifs du portefeuille.
- **Pourquoi des modèles à volatilité variable ?** Les modèles à volatilité constante sont rejetés par le test de Christoffersen : leurs exceptions arrivent par grappes pendant les crises. L'EWMA corrige ce regroupement mais sous-estime les queues (loi normale) ; l'historique filtrée corrige les deux et passe les tests de validation sur le portefeuille par défaut.

### Validation

- **Test de Kupiec** (couverture non conditionnelle) : le nombre d'exceptions est-il compatible avec le niveau de confiance ? Rapport de vraisemblance, χ²(1).
- **Test de Christoffersen** (couverture conditionnelle) : les exceptions sont-elles indépendantes dans le temps ? χ²(2).
- **Test d'Acerbi et Szekely** (backtest de l'Expected Shortfall) : les jours de dépassement, la perte est-elle en moyenne égale à l'ES prévue ? Statistique Z₂ = 1 − Σ (Lₜ / ESₜ)·𝟙{Lₜ > VaRₜ} / (T·(1−α)), zones verte (> −0,70), orange et rouge (≤ −1,80).
- **Feux tricolores de Bâle** : zones verte, orange et rouge selon le nombre d'exceptions sur 250 jours.
- Les formules ont été vérifiées par simulation : sur des données gaussiennes, les trois méthodes retrouvent la VaR théorique à moins de 1 % près.

## Structure du projet

```
var-engine/
├── app.py              Interface Streamlit : barre latérale, calculs, en-tête
├── onglets.py          Contenu des quatre onglets (une fonction par onglet)
├── formats.py          Mise en forme des nombres à la française
├── export.py           Export des résultats en Excel
├── data.py             Téléchargement des prix, rendements, portefeuille
├── var_models.py       VaR et ES : historique, paramétrique, Monte Carlo, EWMA, FHS
├── backtesting.py      Kupiec, Christoffersen, Bâle, stress tests
├── definitions.py      Définitions affichées dans l'interface
├── style.py            Apparence : CSS et modèle des graphiques
├── guide.py            Guide de démarrage pour les débutants
├── tests/              Tests automatiques (pytest)
├── requirements.txt    Bibliothèques nécessaires
├── requirements-dev.txt  Outils de développement (pytest)
└── .streamlit/
    └── config.toml     Thème de l'application
```

Le moteur de calcul (`data.py`, `var_models.py`, `backtesting.py`) est indépendant de l'interface : chaque module peut être utilisé et testé seul.

## Installation et lancement

```bash
git clone https://github.com/atynexpress-afk/var-engine.git
cd var-engine
pip install -r requirements.txt
streamlit run app.py
```

## Tests

Le moteur de calcul est couvert par 49 tests automatiques, sur données simulées (sans connexion Internet) :

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Ils vérifient notamment les formules fermées de la VaR et de l'ES normales, la convergence du Monte Carlo, la récurrence EWMA, la statistique de Kupiec sur le cas de référence de Jorion (10 exceptions sur 250 jours : LR = 12,96), la détection des grappes d'exceptions par Christoffersen, les bornes des zones de Bâle, l'absence de regard vers le futur dans le backtesting, l'équivalence entre le backtesting vectorisé et le calcul direct, les zones du test d'Acerbi et Szekely, la conversion en euros (dont les cours en pence de Londres), la reprise après une panne de Yahoo Finance et l'export Excel.

Le backtesting est vectorisé avec les fenêtres glissantes de pandas (`rolling`) : 259 fois plus rapide qu'une boucle jour par jour, pour des résultats identiques.

## Limites connues

- La règle de la racine du temps suppose des rendements indépendants et de même loi, ce qui n'est pas vérifié en période de crise (regroupement de la volatilité).
- Les méthodes historique et paramétrique sur fenêtre fixe réagissent lentement aux changements de régime, ce que le test de Christoffersen met souvent en évidence. Les modèles EWMA et FHS corrigent ce point.
- Le Monte Carlo repose sur une hypothèse gaussienne multivariée.
- Les données proviennent de Yahoo Finance et ne sont pas contrôlées comme des données de production.
- Pour des titres cotés sur plusieurs places, seuls les jours ouvrés communs sont conservés : un rendement peut alors couvrir deux jours de bourse.

**Pistes d'amélioration :** volatilité GARCH, copules pour la dépendance, théorie des valeurs extrêmes.

## Technologies

Python · pandas · NumPy · SciPy · Plotly · Streamlit · yfinance

---

*Projet pédagogique. Ne constitue pas un outil de gestion des risques en production.*
