"""
style.py
Apparence de l'application : couleurs, feuille de style CSS et modèle des graphiques.
Séparer le style des calculs permet de changer le design sans toucher au moteur de risque.
"""

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# =============================================================================
# 1. COULEURS
# =============================================================================
ACCENT = "#5b6cf0"            # bleu-lavande principal
ACCENT_CLAIR = "#8c98fa"      # début du dégradé
FOND = "#eef0f4"              # fond de page
CARTE = "#ffffff"             # fond des cartes
TEXTE = "#1c1c24"             # texte principal
TEXTE_SECONDAIRE = "#6b6e7b"  # texte secondaire
GRILLE = "#eceef3"            # lignes de grille des graphiques

# Couleurs des séries, toujours attribuées dans le même ordre.
# Palette vérifiée pour rester distinguable par les personnes daltoniennes.
COULEURS = ["#5b6cf0", "#f08a2c", "#1baf7a", "#eda100",
            "#d670c4", "#008300", "#4a3aa7", "#e34948"]
COULEUR_PORTEFEUILLE = "#2b2d3a"   # encre foncée pour le portefeuille
COULEUR_PERTES = "#c5c8d4"         # gris clair pour les pertes réalisées
COULEUR_EXCEPTION = "#e34948"      # rouge pour les exceptions

# Couleurs des zones de Bâle (toujours accompagnées d'un libellé)
ZONES = {"Verte": "#22a06b", "Orange": "#e8a317", "Rouge": "#e34948"}


# =============================================================================
# 2. FEUILLE DE STYLE CSS
# Le CSS décrit l'apparence des éléments d'une page web. On l'injecte dans
# Streamlit avec st.markdown(..., unsafe_allow_html=True).
# Les éléments sont repérés par leurs « sélecteurs » : [data-testid="stMetric"]
# désigne par exemple toutes les cartes de métriques de Streamlit.
# =============================================================================
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&display=swap');

/* ---- Police et fond ---- */
.stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp li {{
    font-family: 'Outfit', 'Segoe UI', sans-serif !important;
}}
.stApp {{ background: {FOND}; }}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1400px; }}

/* ---- Titres ---- */
.stApp h1 {{ font-weight: 400; font-size: 2.2rem; letter-spacing: -0.02em; color: {TEXTE}; }}
.stApp h3 {{ font-weight: 500; font-size: 1.15rem; color: {TEXTE}; }}
.sous-titre {{ color: {TEXTE_SECONDAIRE}; font-size: 1rem; margin-top: -0.6rem; }}

/* ---- Cartes blanches arrondies ----
   Tout conteneur créé avec key="carte_..." prend ce style. */
[class*="st-key-carte"] {{
    background: {CARTE};
    border-radius: 24px;
    padding: 1.4rem 1.6rem;
    box-shadow: 0 1px 2px rgba(20, 22, 40, 0.04), 0 8px 24px rgba(20, 22, 40, 0.05);
}}

/* ---- Pastille sous la valeur d'une métrique (pourcentage) ---- */
[data-testid="stMetricDelta"] {{ border-radius: 999px; padding: 0.1rem 0.6rem; font-size: 0.85rem; }}

/* ---- Métriques ---- */
[data-testid="stMetricLabel"] p {{ color: {TEXTE_SECONDAIRE}; font-size: 0.92rem; }}
[data-testid="stMetricValue"] {{ font-weight: 500; font-size: 1.9rem; color: {TEXTE}; }}

/* ---- Pastilles de paramètres sous le titre ---- */
.pastilles {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.4rem 0 1.4rem 0; }}
/* Pastilles purement informatives : pas de couleur ni d'ombre,
   pour ne pas ressembler à des boutons cliquables. */
.pastille {{
    background: transparent; color: {TEXTE}; border-radius: 999px;
    padding: 0.35rem 0.9rem; font-size: 0.88rem;
    border: 1px solid #d9dce5; cursor: default;
}}
.pastille-libelle {{ color: {TEXTE_SECONDAIRE}; margin-right: 0.3rem; }}

/* ---- Onglets en forme de pilules ---- */
[role="tablist"] {{ gap: 0.5rem; background: transparent; border: none !important;
                    box-shadow: none !important; padding: 4px 2px 10px 2px; }}
div:has(> [role="tablist"]) {{ border: none !important; box-shadow: none !important; }}
[role="tab"] {{
    background: {CARTE} !important; border-radius: 999px !important;
    padding: 0.55rem 1.3rem !important; height: auto !important; border: none !important;
    box-shadow: 0 1px 2px rgba(20, 22, 40, 0.06);
}}
[role="tab"] p {{ font-size: 0.95rem; color: {TEXTE}; }}
[role="tab"][aria-selected="true"] {{
    background: linear-gradient(135deg, {ACCENT_CLAIR} 0%, {ACCENT} 100%) !important;
    box-shadow: 0 6px 18px rgba(91, 108, 240, 0.35);
}}
[role="tab"][aria-selected="true"] p {{ color: #ffffff !important; }}
.react-aria-SelectionIndicator, [data-baseweb="tab-highlight"],
[data-baseweb="tab-border"] {{ display: none !important; }}
[role="tabpanel"] {{ padding-top: 1.2rem; }}

/* ---- Barre latérale ---- */
[data-testid="stSidebar"] {{ border-right: 1px solid #e6e8ee; }}
[data-testid="stSidebar"] h1 {{ font-size: 1.5rem; font-weight: 500; }}
[data-testid="stSidebar"] h2 {{
    font-size: 0.78rem; font-weight: 500; text-transform: uppercase;
    letter-spacing: 0.08em; color: {TEXTE_SECONDAIRE}; margin-top: 0.8rem;
}}

/* ---- Tableaux ---- */
[data-testid="stDataFrame"] {{ border-radius: 16px; overflow: hidden; }}

/* ---- Barre segmentée des exceptions de Bâle ---- */
.segments {{ display: flex; gap: 5px; margin: 0.8rem 0 0.5rem 0; }}
.segment {{ flex: 1; height: 26px; border-radius: 999px; }}
.legende-segments {{ display: flex; justify-content: space-between;
                     color: {TEXTE_SECONDAIRE}; font-size: 0.85rem; }}

/* ---- Encadré de conclusion (backtesting) ---- */
.encadre {{ border-radius: 16px; padding: 0.9rem 1.1rem; margin: 0.2rem 0 1rem 0;
            border-left: 4px solid; font-size: 0.95rem; line-height: 1.5; color: {TEXTE}; }}
.encadre-succes {{ background: #eaf7f0; border-color: {ZONES['Verte']}; }}
.encadre-alerte {{ background: #fdf3e2; border-color: {ZONES['Orange']}; }}
.encadre-titre {{ font-weight: 600; margin-bottom: 0.3rem; }}
.encadre ul {{ margin: 0; padding-left: 1.1rem; }}
.encadre li {{ color: {TEXTE_SECONDAIRE}; margin: 0.1rem 0; }}

/* ---- Guide de démarrage (fenêtre au-dessus de l'application) ---- */
/* La fenêtre est créée en dehors de .stApp : on lui redonne la police et les coins arrondis */
[data-testid="stDialog"] [role="dialog"] {{ border-radius: 24px !important; background: {CARTE}; }}
[data-testid="stDialog"] [role="dialog"] *:not([data-testid="stIconMaterial"]) {{ font-family: 'Outfit', 'Segoe UI', sans-serif !important; }}
[data-testid="stDialog"] [role="dialog"] h2 {{ font-weight: 400; letter-spacing: -0.01em; }}
.guide-progression {{ display: flex; align-items: center; gap: 6px; margin-bottom: 0.9rem; }}
.guide-point {{ width: 8px; height: 8px; border-radius: 999px; background: #d9dce5; }}
.guide-point.actif {{ width: 26px;
                      background: linear-gradient(135deg, {ACCENT_CLAIR} 0%, {ACCENT} 100%); }}
.guide-compteur {{ margin-left: auto; color: {TEXTE_SECONDAIRE}; font-size: 0.85rem; }}
.guide-titre {{ font-weight: 500 !important; font-size: 1.35rem !important; color: {TEXTE};
                padding: 0 0 0.4rem 0 !important; }}
.guide-texte, .guide-texte li {{ color: {TEXTE}; font-size: 0.98rem; line-height: 1.55; }}
.guide-texte ul {{ padding-left: 1.1rem; }}
.guide-texte li {{ margin-bottom: 0.35rem; }}
.guide-exemple {{ background: #f4f5f9; border-left: 3px solid {ACCENT}; border-radius: 14px;
                  padding: 0.8rem 1rem; margin: 0.4rem 0 1rem 0; color: {TEXTE};
                  font-size: 0.93rem; line-height: 1.5; }}
.guide-aide {{ display: inline-flex; align-items: center; justify-content: center;
               width: 1.1rem; height: 1.1rem; border-radius: 999px; font-size: 0.75rem;
               border: 1px solid {TEXTE_SECONDAIRE}; color: {TEXTE_SECONDAIRE}; }}
/* Boutons du guide : même dégradé que l'onglet sélectionné */
.st-key-guide_suivant button, .st-key-guide_commencer button {{
    background: linear-gradient(135deg, {ACCENT_CLAIR} 0%, {ACCENT} 100%) !important;
    border: none !important; border-radius: 999px !important;
    box-shadow: 0 6px 18px rgba(91, 108, 240, 0.35);
}}
.st-key-guide_precedent button {{ border-radius: 999px !important; }}
.st-key-guide_passer button p {{ color: {TEXTE_SECONDAIRE}; }}
.st-key-revoir_guide button {{ border-radius: 999px !important; }}
</style>
"""


def appliquer_style():
    """Injecte la feuille de style dans la page."""
    st.markdown(CSS, unsafe_allow_html=True)


# =============================================================================
# 3. MODÈLE DES GRAPHIQUES PLOTLY
# Un « template » regroupe les réglages communs à tous les graphiques :
# police, fond transparent, grille discrète, info-bulles blanches…
# =============================================================================
MODELE = go.layout.Template()
MODELE.layout = go.Layout(
    font=dict(family="Outfit, Segoe UI, sans-serif", color=TEXTE_SECONDAIRE, size=13),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    colorway=COULEURS,
    xaxis=dict(showgrid=False, zeroline=False, linecolor=GRILLE, ticks="", automargin=True),
    yaxis=dict(gridcolor=GRILLE, zeroline=False, ticks="", automargin=True),
    hoverlabel=dict(bgcolor="#ffffff", bordercolor=GRILLE,
                    font=dict(family="Outfit, sans-serif", color=TEXTE, size=13)),
    legend=dict(orientation="h", y=-0.18, x=0, font=dict(color=TEXTE_SECONDAIRE)),
    margin=dict(l=10, r=10, t=20, b=10),
    barcornerradius=8,
    separators=", ",          # virgule décimale et espace pour les milliers, à la française
)
pio.templates["var_engine"] = MODELE
pio.templates.default = "var_engine"


def afficher(fig):
    """
    Affiche un graphique Plotly avec notre modèle.
    theme=None empêche Streamlit d'imposer son propre style aux graphiques,
    et on fixe explicitement le fond blanc des cartes.
    """
    fig.update_layout(paper_bgcolor=CARTE, plot_bgcolor=CARTE)
    st.plotly_chart(fig, theme=None, config={"displaylogo": False})


# =============================================================================
# 4. COMPOSANTS HTML
# =============================================================================
def pastilles(elements):
    """
    Rangée de pastilles qui résume les paramètres choisis.
    elements : liste de couples (libellé, valeur), ex. [("Méthode", "Historique")]
    """
    html = '<div class="pastilles">'
    for libelle, valeur in elements:
        html += (f'<span class="pastille"><span class="pastille-libelle">{libelle}</span>'
                 f'{valeur}</span>')
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def barre_exceptions(n_exceptions, n_segments=12):
    """
    Barre segmentée façon « jauge » : un segment par exception sur 250 jours.
    Segments 1 à 4 : zone verte, 5 à 9 : orange, 10 et plus : rouge.
    Les segments atteints sont pleins, les autres pâles.
    """
    html = '<div class="segments">'
    for i in range(1, n_segments + 1):
        zone = "Verte" if i <= 4 else ("Orange" if i <= 9 else "Rouge")
        couleur = ZONES[zone]
        opacite = 1.0 if i <= n_exceptions else 0.15
        html += f'<div class="segment" style="background:{couleur}; opacity:{opacite};"></div>'
    html += "</div>"
    html += ('<div class="legende-segments"><span>Verte 0–4</span>'
             '<span>Orange 5–9</span><span>Rouge 10+</span></div>')
    st.markdown(html, unsafe_allow_html=True)


def encadre(titre, lignes, ton="succes"):
    """
    Encadré de synthèse coloré : un titre en gras et une liste de points.
    ton : "succes" (vert) ou "alerte" (orange)
    """
    html = f'<div class="encadre encadre-{ton}"><div class="encadre-titre">{titre}</div>'
    if lignes:
        html += "<ul>" + "".join(f"<li>{ligne}</li>" for ligne in lignes) + "</ul>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
