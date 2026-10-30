"""
Import des datasets IMDb (title.basics + title.ratings) dans la table `catalogue`.

Usage (dans le conteneur) :
    python import_imdb.py                 # seuil 1000 votes
    python import_imdb.py 5000            # seuil 5000 votes
    python import_imdb.py 1000 --tables   # puis copie aussi vers serie/film

Source : IMDb Non-Commercial Datasets (https://datasets.imdbws.com/), usage non commercial.
"""
import gzip
import sys
import time

from app import app
from models import db

DATA_DIR = 'data'
BASICS = f'{DATA_DIR}/title.basics.tsv.gz'
RATINGS = f'{DATA_DIR}/title.ratings.tsv.gz'

TYPES = {'movie': 'film', 'tvSeries': 'serie'}


def val(x):
    """IMDb utilise \\N pour une valeur manquante."""
    return None if x == '\\N' else x


def to_int(x):
    x = val(x)
    return int(x) if x is not None else None


def charger_notes(min_votes):
    notes = {}
    with gzip.open(RATINGS, 'rt', encoding='utf-8') as f:
        next(f)  # en-tête
        for ligne in f:
            tconst, note, votes = ligne.rstrip('\n').split('\t')
            votes = int(votes)
            if votes >= min_votes:
                notes[tconst] = (float(note), votes)
    return notes


def importer(min_votes):
    debut = time.time()
    print(f'Lecture des notes (seuil : {min_votes} votes)...')
    notes = charger_notes(min_votes)
    print(f'  {len(notes)} titres avec assez de votes')

    raw = db.engine.raw_connection()
    try:
        cur = raw.cursor()
        cur.execute('TRUNCATE catalogue RESTART IDENTITY')

        total = 0
        with cur.copy(
            'COPY catalogue (imdb_id, type, titre, annee_debut, annee_fin, '
            'genre, note, votes, duree) FROM STDIN'
        ) as copy:
            with gzip.open(BASICS, 'rt', encoding='utf-8') as f:
                next(f)
                for ligne in f:
                    c = ligne.rstrip('\n').split('\t')
                    # tconst, titleType, primaryTitle, originalTitle,
                    # isAdult, startYear, endYear, runtimeMinutes, genres
                    if len(c) < 9:
                        continue
                    tconst, ttype, titre, _, adulte, debut_a, fin_a, duree, genres = c
                    if ttype not in TYPES or adulte != '0' or tconst not in notes:
                        continue
                    note, votes = notes[tconst]
                    genre = val(genres)
                    genre = genre.split(',')[0] if genre else None
                    copy.write_row((
                        tconst, TYPES[ttype], titre[:300],
                        to_int(debut_a), to_int(fin_a),
                        genre, note, votes, to_int(duree),
                    ))
                    total += 1
        raw.commit()
    finally:
        raw.close()

    print(f'{total} lignes importees dans catalogue en {time.time() - debut:.1f} s')


def vers_tables():
    """Copie le catalogue vers genre / serie / film (a lancer une seule fois)."""
    with app.app_context():
        db.session.execute(db.text("""
            INSERT INTO genre (nom)
            SELECT DISTINCT c.genre FROM catalogue c
            WHERE c.genre IS NOT NULL
              AND c.genre NOT IN (SELECT nom FROM genre)
        """))
        db.session.execute(db.text("""
            INSERT INTO serie (titre, annee_debut, annee_fin, note, genre_id)
            SELECT left(c.titre, 150), c.annee_debut, c.annee_fin, c.note, g.id
            FROM catalogue c
            LEFT JOIN (SELECT nom, MIN(id) AS id FROM genre GROUP BY nom) g ON g.nom = c.genre
            WHERE c.type = 'serie'
        """))
        db.session.execute(db.text("""
            INSERT INTO film (titre, annee, note, duree, genre_id)
            SELECT left(c.titre, 150), c.annee_debut, c.note, c.duree, g.id
            FROM catalogue c
            LEFT JOIN (SELECT nom, MIN(id) AS id FROM genre GROUP BY nom) g ON g.nom = c.genre
            WHERE c.type = 'film'
        """))
        db.session.commit()
        nb_s = db.session.execute(db.text('SELECT count(*) FROM serie')).scalar()
        nb_f = db.session.execute(db.text('SELECT count(*) FROM film')).scalar()
        print(f'Tables mises a jour : {nb_s} series, {nb_f} films')


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    seuil = int(args[0]) if args else 1000
    with app.app_context():
        db.create_all()
        importer(seuil)
    if '--tables' in sys.argv:
        vers_tables()
