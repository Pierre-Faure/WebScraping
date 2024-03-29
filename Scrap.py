
# Imports
from bs4 import BeautifulSoup
from bs4 import SoupStrainer
import requests
import re
import pandas as pd

# from cachecontrol import CacheControl

url_recherche = "https://www.veocinemas.fr/grand-lumiere/films-a-l-affiche/"

# Fonctions

# sess = requests.session()
# cached_sess = CacheControl(sess)
#
# login_data = {"login":"xxxx","password":"xxxx"}
# cached_sess.post("url d'un site necessitant connexion",login_data)
#
# # capture de la requete http
#
# html = cached_sess.get("url_recherche")

# proxies

proxies = {
    # "http": "http://atlas.proxy.edf.fr:3131",
    # "https": "https://atlas.proxy.edf.fr:3131"
}

html = requests.get(url_recherche, proxies=proxies)

soup = BeautifulSoup(html.text, 'html.parser', parse_only=SoupStrainer(id="maincontent-large"))

film = {}
liste_films = []


def has_duration(classe):
    return re.compile("duration").search(classe) and not classe


def scraping(pair_impair, liste):
    for fiches in soup.find_all("div", pair_impair):  # on parcoure les fiches films du cote choisi (pair ou impair)

    #---------------Titre--------------#
        # Le le titre du film est la première valeur de la liste du contenu de la balise h4
        film["Titre"] = str(fiches.h4.contents[0])

    # ---------------En salle--------------#
        film["En Salle"] = str(
            fiches.p.span.strong.contents[0])  # on accede à la date de disponibilité du film en salle

    # ---------------Durée--------------#
        # certains films n'ont pas de duree et on ne peut pas faire .contents sur un NoneType
        if (fiches.p.find("strong","hi duration") != None):
            film["Duree"] = str(fiches.p.find("strong", "hi duration").contents[0])
        else:
            film["Duree"] = None

    # ---------------lien--------------#
        # on recupere l'adresse du lien qui mene à la fiche etendue du film
        lien = requests.get(fiches.a['href'],proxies=proxies)
        # on cree u obj BS pour cette nouvelle page
        souplette = BeautifulSoup(lien.text, 'html.parser', parse_only=SoupStrainer(id="maincontent-large"))

    # ---------------Genre--------------#
        if (souplette.find("strong", "hi duration") != None):
            if (souplette.find("strong", "hi duration").next_sibling != None):
                genre_film = souplette.find("strong", "hi duration").next_sibling.next_sibling
            else:
                genre_film = None
        else:
            genre_film = None

        if (genre_film != None):
            film["Genre"] = str(genre_film.contents[0])
        else:
            film["Genre"] = None

    # ---------------Date sortie nationale--------------#
        if (genre_film != None):
            if (genre_film.next_sibling != None):
                if (genre_film.next_sibling.next_sibling != None):
                    sortie_nationale = genre_film.next_sibling.next_sibling.next_sibling.next_sibling
                else:
                    sortie_nationale = None
            else:
                sortie_nationale = None
        else:
            sortie_nationale = None

        if (sortie_nationale != None):
            film["Sortie nationale"] = str(sortie_nationale.contents[0])
        else:
            film["Sortie nationale"] = None

    # ---------------Casting (acteur(s)/realisateur(s))--------------#
        casting = souplette.find("p","").find("strong","")
        if (casting != None):
            film["Realisateur(s)"] = str(casting.contents[0])
            if (casting.next_sibling != None):
                if (casting.next_sibling.next_sibling != None):
                    film["Acteur(s)"] = str(casting.next_sibling.next_sibling.next_sibling.contents[0])
                else:
                    film["Acteur(s)"] = None
            else:
                film["Acteur(s)"] = None
        else:
            film["Realisateur(s)"] = None

    # ---------------Titre original--------------#
        if (souplette.find("p", "titre_vo") != None):
            if (souplette.find("p", "titre_vo").find("strong") != None):
                film["Titre original"] = str(souplette.find("p", "titre_vo").find("strong").contents[0])
            else:
                film["Titre original"] = None
        else:
            film["Titre original"] = None

    # ---------------Synopsis--------------#
        if (souplette.find("p", "synopsis description") != None):
            film["Synopsis"] = str(souplette.find("p", "synopsis description").contents[0])
        else:
            film["Synopsis"] = None

    # ---------------Note--------------#
        if (souplette.find("span","rating") != None):
            film["Note (/5)"] = str(souplette.find("span","rating").contents[0])
        else:
            film["Note (/5)"] = None

    # ---------------Votes--------------#
        if (souplette.find("span", "nbvote fn") != None):
            film["Votes"] = str(souplette.find("span", "nbvote fn").contents[0])
        else:
            film["Votes"] = None

        liste.append(dict(film))


    return liste


liste_films = scraping("fichefilm-mini-block fichefilm-mini-block-pair", liste_films)
liste_films = scraping("fichefilm-mini-block fichefilm-mini-block-impair", liste_films)
df_films = pd.DataFrame(liste_films)  # création d'un dataframe

# Mise en forme du df

df_films["Note (/5)"] = df_films["Note (/5)"].astype("float")

pd.to_datetime(df_films["Sortie nationale"])
df_films["Sortie nationale"] = df_films["Sortie nationale"].astype("datetime64[D]")

def h_to_min(valeur):
    heures, minutes = valeur.split('h')
    return int(heures)*60 + int(minutes)
df_films['Duree'] = df_films['Duree'].fillna("00h00").apply(h_to_min).astype("int")

def votes_fill():
    som = moy = 0

    for votes in df_films["Votes"]:
        if (votes !=None):
            votes = votes.strip(" votes")
            #votes = int(votes)
            som = som + int(votes)
    moy = som/df_films["Votes"].index.stop

    for votes2 in df_films["Votes"]:
        if (votes2 ==None):
            votes2 = moy
