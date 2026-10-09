"""
export.py
Export des résultats dans un fichier Excel, une feuille par thème.
Le fichier est construit en mémoire (sans être écrit sur le disque),
puis proposé au téléchargement par app.py.
"""

from io import BytesIO

import pandas as pd

FORMAT_POURCENT = "0.00%"
FORMAT_EUROS = '#,##0 "€"'
FORMAT_DECIMAL = "0.000"


def _formater(feuille, formats):
    """
    Applique un format de nombre Excel à certaines colonnes d'une feuille.
    formats : {nom de colonne: format}, ex. {"VaR (%)": "0.00%"}
    Les valeurs restent des nombres : on peut refaire des calculs dans Excel.
    """
    entetes = {cellule.value: cellule.column for cellule in feuille[1]}
    for nom, fmt in formats.items():
        if nom in entetes:
            for (cellule,) in feuille.iter_rows(min_row=2, min_col=entetes[nom],
                                                max_col=entetes[nom]):
                cellule.number_format = fmt
    for colonne in feuille.columns:                      # largeur adaptée au contenu
        largeur = max(len(str(c.value)) if c.value is not None else 0 for c in colonne)
        feuille.column_dimensions[colonne[0].column_letter].width = min(largeur + 2, 45)


def creer_excel(parametres, var_es, tests=None, stress=None):
    """
    parametres : dictionnaire {libellé: valeur} des réglages utilisés
    var_es     : DataFrame VaR et ES par méthode (fractions et euros)
    tests      : DataFrame des tests de backtesting (facultatif)
    stress     : DataFrame des crises historiques (facultatif)
    Renvoie le contenu du fichier .xlsx (des octets).
    """
    memoire = BytesIO()
    with pd.ExcelWriter(memoire, engine="openpyxl") as excel:
        pd.Series(parametres, name="Valeur").rename_axis("Paramètre").to_frame().to_excel(
            excel, sheet_name="Paramètres")
        var_es.rename_axis("Méthode").to_excel(excel, sheet_name="VaR et ES")
        _formater(excel.sheets["VaR et ES"], {"VaR (%)": FORMAT_POURCENT,
                                              "ES (%)": FORMAT_POURCENT,
                                              "VaR (€)": FORMAT_EUROS, "ES (€)": FORMAT_EUROS})
        _formater(excel.sheets["Paramètres"], {})

        if tests is not None:
            tests.rename_axis("Méthode").to_excel(excel, sheet_name="Backtesting")
            _formater(excel.sheets["Backtesting"], {"Exceptions attendues": "0.0",
                                                    "p-value Kupiec": FORMAT_DECIMAL,
                                                    "p-value Christoffersen": FORMAT_DECIMAL,
                                                    "Z2 (Acerbi-Szekely)": "0.00"})
        if stress is not None:
            stress.rename_axis("Scénario").to_excel(excel, sheet_name="Stress tests")
            _formater(excel.sheets["Stress tests"], {"Perte totale": FORMAT_POURCENT,
                                                     "Pire journée": FORMAT_POURCENT,
                                                     "Perte (€)": FORMAT_EUROS})
    return memoire.getvalue()
