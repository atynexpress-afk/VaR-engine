"""
Tests de la préparation des données (data.py). Le vrai téléchargement Yahoo
Finance dépend d'Internet : on le remplace par une fausse fonction pour tester
la gestion des pannes.
"""

import numpy as np
import pandas as pd
import pytest

import data
from data import calculer_rendements, normaliser_poids, rendements_portefeuille


def test_normaliser_poids():
    assert normaliser_poids([2, 1, 1]) == pytest.approx([0.5, 0.25, 0.25])


@pytest.mark.parametrize("poids", [[-1, 2], [0, 0]])
def test_poids_invalides(poids):
    with pytest.raises(ValueError):
        normaliser_poids(poids)


def test_rendements_simples_et_log():
    prix = pd.DataFrame({"A": [100.0, 110.0, 99.0]})
    assert calculer_rendements(prix)["A"].tolist() == pytest.approx([0.10, -0.10])
    assert calculer_rendements(prix, "log")["A"].tolist() == pytest.approx(
        [np.log(1.1), np.log(0.9)])


def test_rendement_du_portefeuille():
    rendements = pd.DataFrame({"A": [0.10, -0.02], "B": [0.00, 0.04]})
    r_ptf = rendements_portefeuille(rendements, [3, 1])          # 75 % / 25 %
    assert r_ptf.tolist() == pytest.approx([0.075, -0.005])


def test_un_poids_par_action():
    rendements = pd.DataFrame({"A": [0.01], "B": [0.02]})
    with pytest.raises(ValueError):
        rendements_portefeuille(rendements, [1.0])


# ---------------------------------------------------------------------------
# Téléchargement : on remplace Yahoo Finance par une fausse fonction
# (monkeypatch), pour tester les nouvelles tentatives sans Internet.
# ---------------------------------------------------------------------------
def _faux_prix():
    index = pd.date_range("2024-01-01", periods=3)
    return pd.concat({"Close": pd.DataFrame({"A": [1.0, 2.0, 3.0], "B": [4.0, 5.0, 6.0]},
                                            index=index)}, axis=1)


def test_nouvel_essai_apres_une_panne(monkeypatch):
    appels = []

    def yahoo_capricieux(*args, **kwargs):
        appels.append(1)
        if len(appels) == 1:
            raise ConnectionError("trop de requêtes")       # premier appel : échec
        return _faux_prix()                                  # deuxième appel : succès

    monkeypatch.setattr(data.yf, "download", yahoo_capricieux)
    monkeypatch.setattr(data, "PAUSE", 0)
    prix = data.telecharger_prix(["A", "B"], "2024-01-01")
    assert len(appels) == 2
    assert prix["B"].tolist() == [4.0, 5.0, 6.0]


def test_message_clair_si_yahoo_ne_repond_pas(monkeypatch):
    def yahoo_en_panne(*args, **kwargs):
        raise ConnectionError("service indisponible")

    monkeypatch.setattr(data.yf, "download", yahoo_en_panne)
    monkeypatch.setattr(data, "PAUSE", 0)
    with pytest.raises(ValueError, match="Yahoo Finance ne répond pas"):
        data.telecharger_prix(["A"], "2024-01-01")


# ---------------------------------------------------------------------------
# Conversion en euros
# ---------------------------------------------------------------------------
def test_conversion_en_euros():
    index = pd.date_range("2024-01-01", periods=3)
    prix = pd.DataFrame({"LVMH": [700.0, 710.0, 720.0],      # déjà en euros
                         "AAPL": [110.0, 110.0, 110.0],      # en dollars
                         "HSBC": [600.0, 600.0, 600.0]},     # en pence
                        index=index)
    taux = pd.DataFrame({"USD": [1.10, 1.00, np.nan],        # taux manquant le 3e jour
                         "GBP": [0.80, 0.80, 0.80]}, index=index)
    devises = {"LVMH": "EUR", "AAPL": "USD", "HSBC": "GBp"}

    en_euros = data.convertir_en_euros(prix, devises, taux)
    assert en_euros["LVMH"].tolist() == [700.0, 710.0, 720.0]            # inchangé
    assert en_euros["AAPL"].tolist() == pytest.approx([100.0, 110.0, 110.0])
    # 600 pence = 6 livres = 6 / 0,80 = 7,50 €
    assert en_euros["HSBC"].tolist() == pytest.approx([7.5, 7.5, 7.5])


def test_baisse_du_dollar_visible_en_euros():
    # Cours en dollars stable, mais l'euro passe de 1,00 à 1,10 dollar :
    # l'investisseur européen perd 1 / 1,10 - 1 = -9,1 %
    index = pd.date_range("2024-01-01", periods=2)
    prix = pd.DataFrame({"AAPL": [100.0, 100.0]}, index=index)
    taux = pd.DataFrame({"USD": [1.00, 1.10]}, index=index)
    rendement = calculer_rendements(data.convertir_en_euros(prix, {"AAPL": "USD"}, taux))
    assert rendement["AAPL"].iloc[0] == pytest.approx(1 / 1.10 - 1)
