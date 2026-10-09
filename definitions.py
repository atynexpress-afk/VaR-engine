"""
definitions.py
Dictionnaire des définitions affichées dans l'application, au survol ou au
clic sur la petite icône d'aide placée à côté de chaque notion.
Les regrouper ici évite d'encombrer app.py et permet de les modifier facilement.
"""

DEFINITIONS = {
    # ---- Paramètres du portefeuille ----
    "actions": "Titres qui composent le portefeuille. Les prix de clôture ajustés "
               "(dividendes et divisions d'actions) sont téléchargés depuis Yahoo Finance.",
    "tickers": "Code d'identification d'un titre sur Yahoo Finance. Exemples : AAPL (Apple), "
               "MSFT (Microsoft), ^FCHI (indice CAC 40). Les actions cotées à Paris se "
               "terminent par .PA. Les titres cotés dans une autre devise (dollar, livre…) "
               "sont convertis en euros au taux de change de chaque jour : le risque de "
               "change est ainsi inclus dans la VaR.",
    "poids": "Part de la valeur du portefeuille investie dans chaque titre. Quand un poids est "
             "modifié, les autres s'ajustent en gardant leurs proportions, pour que le total "
             "reste égal à 100 %. Les poids sont positifs : la vente à découvert n'est pas "
             "autorisée.",
    "montant": "Valeur de marché totale du portefeuille. Elle sert à convertir les pertes "
               "exprimées en pourcentage en pertes en euros.",
    "periode": "Historique utilisé pour estimer les modèles. Une période longue contient "
               "davantage de crises ; une période courte reflète mieux les conditions récentes.",

    # ---- Paramètres de risque ----
    "niveau_confiance": "Probabilité que la perte ne dépasse pas la VaR. À 99 %, la perte ne "
                        "doit dépasser la VaR qu'un jour sur cent en moyenne. La réglementation "
                        "retient 99 % pour la VaR et 97,5 % pour l'Expected Shortfall (FRTB).",
    "horizon": "Durée sur laquelle on mesure la perte potentielle. Le passage de 1 jour à h jours "
               "utilise la règle de la racine du temps : VaR(h) = VaR(1) × √h. Cette règle suppose "
               "des rendements indépendants et de même loi d'un jour à l'autre.",
    "methode": "**Historique** : quantile des pertes réellement observées, sans hypothèse de loi.\n\n"
               "**Paramétrique normale** : rendements supposés gaussiens, VaR = −μ + σ·z.\n\n"
               "**Paramétrique Student** : loi aux queues plus épaisses que la normale, "
               "plus réaliste pour des actions.\n\n"
               "**Monte Carlo** : simulation de milliers de scénarios de rendements corrélés, "
               "grâce à la décomposition de Cholesky de la matrice de covariance.\n\n"
               "**EWMA (RiskMetrics)** : loi normale, mais avec une volatilité qui donne plus de "
               "poids aux jours récents, pour réagir vite aux crises.\n\n"
               "**Historique filtrée (FHS)** : les pertes passées sont remises à l'échelle de la "
               "volatilité EWMA actuelle. Elle combine les queues épaisses de la méthode "
               "historique et la réactivité de l'EWMA.",
    "acerbi_szekely": "Test d'Acerbi et Szekely (2014) pour l'Expected Shortfall : "
                      "Z2 = 1 − Σ (perte / ES prévue, les jours où la VaR est dépassée) "
                      "/ (T × (1 − α)). Un modèle juste donne Z2 ≈ 0. Zone verte au-dessus de "
                      "−0,70, orange jusqu'à −1,80 (rejet à 5 %), rouge en dessous (rejet à "
                      "0,01 %). FRTB a fait de l'ES à 97,5 % la mesure réglementaire.",
    "export": "Fichier Excel avec une feuille par thème : paramètres utilisés, VaR et ES de "
              "chaque méthode, tests de backtesting et stress tests historiques. Les valeurs "
              "restent des nombres, pour pouvoir refaire des calculs dans Excel.",
    "lambda": "Facteur de lissage λ de la volatilité EWMA : σ²(t+1) = λ·σ²(t) + (1 − λ)·r(t)². "
              "Plus λ est petit, plus la volatilité réagit vite aux derniers jours. RiskMetrics "
              "(JP Morgan) retient 0,94 pour des données journalières.",
    "ddl": "Degrés de liberté de la loi de Student. Plus ils sont faibles, plus les queues de "
           "distribution sont épaisses et plus les pertes extrêmes sont probables. Au-delà de 30, "
           "la loi de Student est très proche de la loi normale.",
    "n_sim": "Nombre de scénarios générés par la méthode Monte Carlo. Plus il est élevé, plus "
             "l'estimation est précise, mais plus le calcul est long. L'erreur d'estimation "
             "diminue proportionnellement à 1/√n.",
    "graine": "Valeur d'initialisation du générateur de nombres aléatoires. Avec la même graine, "
              "la simulation donne exactement le même résultat : le calcul est reproductible "
              "et auditable.",
    "fenetre": "Nombre de jours passés utilisés, chaque jour, pour recalculer la VaR pendant le "
               "backtesting. 250 jours correspondent à environ une année de bourse, la norme "
               "réglementaire.",

    # ---- Mesures de risque ----
    "var": "Value at Risk : perte qui ne sera dépassée, sur l'horizon choisi, qu'avec une "
           "probabilité égale à 1 − niveau de confiance. C'est un quantile de la distribution "
           "des pertes.",
    "es": "Expected Shortfall : perte moyenne dans les scénarios où la VaR est dépassée. Elle "
          "mesure la gravité des pertes extrêmes, elle est sous-additive, et elle a remplacé la "
          "VaR pour le calcul du capital réglementaire avec FRTB.",
    "volatilite": "Écart-type des rendements, qui mesure leur dispersion. On l'annualise en "
                  "multipliant la volatilité journalière par √252, 252 étant le nombre moyen "
                  "de jours de bourse dans une année.",
    "jours": "Nombre de rendements journaliers utilisés dans les calculs, après suppression "
             "des jours où l'un des titres n'a pas coté.",
    "rendement_annuel": "Rendement journalier moyen multiplié par 252.",
    "skewness": "Coefficient d'asymétrie de la distribution. Négatif : les fortes baisses sont "
                "plus fréquentes que les fortes hausses. Il vaut 0 pour une loi normale.",
    "kurtosis": "Excès d'aplatissement par rapport à la loi normale. Positif : les queues sont "
                "épaisses, c'est-à-dire que les valeurs extrêmes sont plus fréquentes que ne le "
                "prévoit la loi normale. Il vaut 0 pour une loi normale.",

    # ---- Graphiques ----
    "base100": "Chaque série est divisée par sa première valeur puis multipliée par 100, ce qui "
               "permet de comparer des titres de prix différents. La courbe du portefeuille "
               "suppose un achat initial sans rééquilibrage.",
    "stats_annuelles": "Rendement et volatilité de chaque titre et du portefeuille, ramenés à "
                       "une base annuelle pour être comparables.",
    "correlation": "Coefficient compris entre −1 et 1 qui mesure dans quelle mesure deux titres "
                   "évoluent ensemble. Plus les corrélations sont faibles, plus la "
                   "diversification réduit le risque du portefeuille.",
    "distribution": "Histogramme des rendements journaliers comparé à une loi normale de même "
                    "moyenne et de même écart-type. Les lignes verticales indiquent la VaR et "
                    "l'ES à 1 jour de la méthode mise en avant.",
    "qqplot": "Graphique quantile-quantile : il compare les quantiles observés des rendements "
              "centrés réduits à ceux d'une loi normale. Si les points s'écartent de la droite "
              "aux extrémités, la distribution a des queues épaisses.",

    # ---- Backtesting ----
    "backtesting": "Procédure de validation d'un modèle de VaR : chaque jour, la VaR est "
                   "calculée avec les seules données passées, puis comparée à la perte "
                   "réellement observée ce jour-là.",
    "exception": "Jour où la perte réalisée dépasse la VaR calculée avec les données de la "
                 "veille. À 99 %, on en attend environ une tous les 100 jours.",
    "exceptions_attendues": "Nombre théorique d'exceptions : nombre de jours testés × "
                            "(1 − niveau de confiance).",
    "kupiec": "Test de couverture non conditionnelle : il vérifie que le nombre d'exceptions est "
              "compatible avec le niveau de confiance. La statistique du rapport de "
              "vraisemblance suit un χ² à 1 degré de liberté. Une p-value inférieure à 5 % "
              "conduit à rejeter le modèle.",
    "christoffersen": "Test de couverture conditionnelle : il vérifie à la fois le nombre "
                      "d'exceptions et leur indépendance dans le temps. Des exceptions "
                      "regroupées révèlent un modèle qui réagit trop lentement aux crises. "
                      "La statistique suit un χ² à 2 degrés de liberté.",
    "verdict": "Le modèle est rejeté si la p-value de Kupiec ou celle de Christoffersen est "
               "inférieure à 5 %.",
    "bale": "Feux tricolores du Comité de Bâle, sur les 250 derniers jours pour une VaR à 99 % : "
            "zone verte de 0 à 4 exceptions, zone orange de 5 à 9 (capital majoré), zone rouge "
            "à partir de 10 (modèle remis en cause).",

    # ---- Stress tests ----
    "stress_historique": "Application au portefeuille actuel des variations de prix observées "
                         "pendant une crise passée, avec un achat au début de la crise et sans "
                         "rééquilibrage.",
    "perte_totale": "Perte cumulée du portefeuille entre le début et la fin du scénario.",
    "pire_journee": "Plus forte perte journalière du portefeuille pendant le scénario. Elle se "
                    "compare à la VaR et à l'ES à 1 jour, qui portent sur la même durée : une "
                    "pire journée bien au-delà de l'ES montre que le modèle sous-estime les crises.",
    "stress_hypothetique": "Scénario défini par l'utilisateur : un choc instantané est appliqué "
                           "au prix de chaque titre. Perte = − somme des poids × chocs.",
    "choc": "Variation instantanée appliquée au prix du titre, en pourcentage.",
}
