"""
formats.py
Mise en forme des nombres à la française, partagée par app.py et onglets.py.
"""

import streamlit as st


def euros(x):
    """Formate un nombre en euros avec des espaces : 1234567 -> '1 234 567 €'."""
    return f"{x:,.0f} €".replace(",", " ")


def pct(x, decimales=2):
    """Formate un nombre en pourcentage à la française : 0.0235 -> '2,35 %'."""
    return f"{x * 100:.{decimales}f} %".replace(".", ",")


def nombre(x, decimales=1):
    """Formate un nombre décimal à la française : 19.94 -> '19,9'."""
    return f"{x:.{decimales}f}".replace(".", ",")


def p_value(x):
    """Formate une p-value : les valeurs minuscules s'affichent '< 0,001' plutôt que '0'."""
    return "< 0,001" if x < 0.001 else nombre(x, 3)


def colonne(definition):
    """Ajoute une icône d'aide à l'en-tête d'une colonne de tableau."""
    return st.column_config.Column(help=definition)
