"""
version.py
Empreinte du moteur de calcul, pour que le cache de Streamlit se renouvelle
quand les calculs changent.

Le problème : @st.cache_data ne recalcule un résultat que si les paramètres ou
le code de la fonction mise en cache changent. Il ne voit pas les modifications
des fonctions qu'elle appelle (var_glissante, telecharger_prix_euros…). Après une
mise à jour du site, il pourrait donc resservir des résultats calculés par
l'ancien code.

La solution : on passe version_moteur() en paramètre des fonctions mises en
cache. C'est une empreinte du contenu des fichiers du moteur : la moindre
modification la change, et le cache repart de zéro.
"""

import hashlib
import pathlib

FICHIERS_MOTEUR = ["data.py", "var_models.py", "backtesting.py"]
DOSSIER = pathlib.Path(__file__).parent


def version_moteur(dossier=DOSSIER):
    """
    Empreinte (12 caractères) du contenu actuel des fichiers du moteur.
    Elle est recalculée à chaque appel, et non une fois pour toutes à
    l'import : Streamlit recharge les fichiers modifiés, mais pas ce module-ci
    s'il n'a pas changé lui-même, et une valeur calculée à l'import resterait figée.
    """
    contenu = b"".join((dossier / fichier).read_bytes() for fichier in FICHIERS_MOTEUR)
    return hashlib.sha256(contenu).hexdigest()[:12]
