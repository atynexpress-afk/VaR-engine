"""
Test de l'export Excel (export.py) : le fichier produit se relit correctement.
"""

from io import BytesIO

import pandas as pd
import pytest

from export import creer_excel


def test_fichier_excel_relisible():
    var_es = pd.DataFrame({"VaR (%)": [0.044], "ES (%)": [0.064],
                           "VaR (€)": [44_000.0], "ES (€)": [64_000.0]}, index=["Historique"])
    stress = pd.DataFrame({"Perte totale": [0.40], "Pire journée": [0.13],
                           "Perte (€)": [400_000.0]}, index=["Krach Covid (2020)"])
    contenu = creer_excel({"Niveau de confiance": 0.99}, var_es, tests=None, stress=stress)

    feuilles = pd.read_excel(BytesIO(contenu), sheet_name=None, index_col=0)
    assert list(feuilles) == ["Paramètres", "VaR et ES", "Stress tests"]   # pas de backtesting
    assert feuilles["VaR et ES"].loc["Historique", "VaR (%)"] == pytest.approx(0.044)
    assert feuilles["Stress tests"].loc["Krach Covid (2020)", "Perte (€)"] == 400_000
