"""
guide.py
Guide de démarrage affiché à l'ouverture de l'application.
Il s'adresse aux personnes qui découvrent la finance : chaque étape explique,
sans jargon, une partie de l'outil. Il peut être passé à tout moment et
rouvert depuis la barre latérale.
"""

import streamlit as st

# =============================================================================
# 1. CONTENU DES ÉTAPES
# Chaque étape : un titre, un texte (HTML simple) et un exemple facultatif.
# =============================================================================
ETAPES = [
    {
        "titre": "Bienvenue dans VaR Engine",
        "texte": """
            <p>Cet outil répond à une question simple :
            <b>combien mon argent placé en bourse pourrait-il perdre lors d'une mauvaise journée ?</b></p>
            <p>Pas besoin de connaître la finance : ce guide t'explique en quelques étapes
            comment régler l'outil et lire ses résultats.</p>
        """,
        "exemple": """
            <b>Un peu de vocabulaire</b><br>
            Une <b>action</b> est une petite part d'une entreprise (LVMH, Airbus…) qui s'achète en bourse.
            Un <b>portefeuille</b> est l'ensemble des actions que l'on possède.
        """,
    },
    {
        "titre": "1. Compose ton portefeuille",
        "texte": """
            <p>Tout se règle dans la <b>barre latérale à gauche</b> :</p>
            <ul>
              <li><b>Actions du CAC 40</b> : choisis les entreprises françaises dans lesquelles tu investis.</li>
              <li><b>Autres tickers</b> : un ticker est le code d'une action en bourse
                  (ex. AAPL pour Apple). Facultatif.</li>
              <li><b>Poids</b> : la part de ton argent placée dans chaque action.
                  Le total reste toujours à 100 %.</li>
              <li><b>Valeur du portefeuille</b> : la somme investie au total.</li>
              <li><b>Dates</b> : la période passée que l'outil observe pour voir comment les prix ont bougé.</li>
            </ul>
        """,
        "exemple": """
            <b>Pas d'idée ?</b> Garde les réglages proposés : trois grandes entreprises
            françaises à parts égales, pour 1&nbsp;000&nbsp;000&nbsp;€.
        """,
    },
    {
        "titre": "2. Lis les trois chiffres clés",
        "texte": """
            <p>En haut de la page, trois cartes résument le risque :</p>
            <ul>
              <li><b>VaR</b> (Value at Risk, « valeur en risque ») : la perte qu'on ne devrait
                  presque jamais dépasser.</li>
              <li><b>Expected Shortfall</b> (« perte moyenne en cas de coup dur ») : la perte moyenne
                  les rares jours où la VaR est dépassée. C'est le scénario du pire.</li>
              <li><b>Volatilité</b> : à quel point les prix bougent. Plus elle est élevée,
                  plus le portefeuille est agité.</li>
            </ul>
        """,
        "exemple": """
            <b>Exemple</b> : une VaR à 99 % sur 1 jour de 44&nbsp;000&nbsp;€ signifie que
            <b>99 jours sur 100</b>, tu ne devrais pas perdre plus de 44&nbsp;000&nbsp;€ en une journée.
            Le 100<sup>e</sup> jour, la perte peut être plus forte : l'Expected Shortfall dit de combien, en moyenne.
        """,
    },
    {
        "titre": "3. Explore les quatre onglets",
        "texte": """
            <ul>
              <li><b>Portefeuille</b> : l'évolution des prix de tes actions et la façon dont elles
                  montent ou baissent ensemble.</li>
              <li><b>VaR & ES</b> : les résultats détaillés, calculés de six façons différentes
                  pour pouvoir les comparer.</li>
              <li><b>Backtesting</b> : on vérifie si l'outil aurait eu raison dans le passé.
                  Un feu <b>vert</b> veut dire que le calcul est fiable, <b>orange</b> ou <b>rouge</b>
                  qu'il sous-estime le risque.</li>
              <li><b>Stress tests</b> : combien tu aurais perdu pendant de vraies crises
                  (2008, Covid 2020…), et ce que donnerait une crise que tu inventes toi-même.</li>
            </ul>
        """,
        "exemple": None,
    },
    {
        "titre": "4. Les réglages avancés",
        "texte": """
            <p>Sous <b>Mesure du risque</b>, dans la barre latérale :</p>
            <ul>
              <li><b>Niveau de confiance</b> : 99 % = on regarde le mauvais jour sur 100 ;
                  95 % = le mauvais jour sur 20. Plus il est haut, plus la VaR est prudente.</li>
              <li><b>Horizon</b> : la durée considérée. 10 jours = « combien puis-je perdre
                  en deux semaines ? ».</li>
              <li><b>Méthode</b> : la façon de calculer. « Historique », qui se base simplement
                  sur ce qui s'est passé, est la plus intuitive. « Historique filtrée »
                  est la plus fiable : c'est elle qui réagit le mieux aux crises.</li>
            </ul>
            <p>Les autres réglages s'adressent aux spécialistes : tu peux les laisser tels quels.</p>
        """,
        "exemple": """
            <b>Astuce</b> : chaque réglage et chaque résultat a une petite icône
            <span class="guide-aide">?</span> qui donne sa définition au survol.
        """,
    },
    {
        "titre": "C'est parti !",
        "texte": """
            <p>Tu sais maintenant l'essentiel :</p>
            <ul>
              <li>tu composes ton portefeuille à gauche ;</li>
              <li>tu lis la VaR et l'Expected Shortfall en haut ;</li>
              <li>tu explores les onglets pour aller plus loin.</li>
            </ul>
            <p>Tu pourras rouvrir ce guide à tout moment avec le bouton
            <b>Revoir le guide</b> de la barre latérale.</p>
        """,
        "exemple": None,
    },
]


# =============================================================================
# 2. MÉMOIRE DU GUIDE
# st.session_state garde l'étape en cours et le fait que le guide a été vu.
# =============================================================================
def _fermer():
    """Marque le guide comme vu : il ne se rouvre plus pendant la session."""
    st.session_state["guide_vu"] = True


def _aller_a(etape):
    st.session_state["guide_etape"] = etape


def rouvrir_guide():
    """Appelée par le bouton « Revoir le guide » de la barre latérale."""
    st.session_state["guide_vu"] = False
    st.session_state["guide_etape"] = 0


# =============================================================================
# 3. FENÊTRE DU GUIDE
# st.dialog ouvre une fenêtre au-dessus de l'application. Fermer la fenêtre
# (croix, touche Échap ou clic à côté) appelle _fermer grâce à on_dismiss.
# =============================================================================
@st.dialog("Guide de démarrage", width="medium", on_dismiss=_fermer)
def _fenetre_guide():
    n = len(ETAPES)
    i = st.session_state.get("guide_etape", 0)
    etape = ETAPES[i]

    # Points de progression : l'étape en cours est allongée
    points = "".join(f'<span class="guide-point{" actif" if k == i else ""}"></span>'
                     for k in range(n))
    html = (f'<div class="guide-progression">{points}'
            f'<span class="guide-compteur">Étape {i + 1} sur {n}</span></div>'
            f'<h3 class="guide-titre">{etape["titre"]}</h3>'
            f'<div class="guide-texte">{etape["texte"]}</div>')
    if etape["exemple"]:
        html += f'<div class="guide-exemple">{etape["exemple"]}</div>'
    st.markdown(html, unsafe_allow_html=True)

    # Boutons : « Passer » à gauche, navigation à droite.
    # Un clic dans la fenêtre ne relance que la fenêtre ; st.rerun() relance
    # toute l'application pour la fermer.
    gauche, _, precedent, suivant = st.columns([1.3, 0.5, 1, 1.2], vertical_alignment="center")
    if i < n - 1:
        if gauche.button("Passer le guide", key="guide_passer", type="tertiary"):
            _fermer()
            st.rerun()
    if i > 0:
        precedent.button("Précédent", key="guide_precedent", on_click=_aller_a, args=(i - 1,),
                         width="stretch")
    if i < n - 1:
        suivant.button("Suivant", key="guide_suivant", type="primary", on_click=_aller_a,
                       args=(i + 1,), width="stretch")
    elif suivant.button("Commencer", key="guide_commencer", type="primary", width="stretch"):
        _fermer()
        st.rerun()


def afficher_guide():
    """Ouvre le guide tant qu'il n'a pas été vu ou passé."""
    if not st.session_state.get("guide_vu", False):
        _fenetre_guide()
