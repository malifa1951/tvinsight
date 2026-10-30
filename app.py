import csv
import io
import time
from flask import Flask, render_template, request, redirect, url_for, Response, flash, jsonify
from config import Config
from models import (db, Genre, Serie, Film, Plateforme, Saison, Acteur, Role,
                    serie_plateforme, Catalogue)

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)


# ---------- CONTEXTE GLOBAL (pour les templates) ----------
@app.context_processor
def inject_globals():
    return {
        'app_name': 'TVinsight',
        'app_version': '1.1',
        'current_year': time.strftime('%Y')
    }


# ---------- PAGE D'ACCUEIL ----------
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 25

    pagination = Serie.query.order_by(Serie.titre).paginate(
        page=page, per_page=per_page, error_out=False
    )
    series = pagination.items
    genres = Genre.query.all()
    stats = {
        'total_series': Serie.query.count(),
        'total_genres': Genre.query.count(),
        'avg_note': round(db.session.query(db.func.avg(Serie.note)).scalar() or 0, 2)
    }
    return render_template(
        'index.html',
        series=series,
        genres=genres,
        stats=stats,
        pagination=pagination
    )


# ---------- AUTOCOMPLETION (catalogue importé) ----------
@app.route('/api/suggest')
def api_suggest():
    """
    /api/suggest?q=bre&type=serie  ->  liste JSON de titres du catalogue
    type : 'serie' ou 'film' (optionnel)
    """
    q = request.args.get('q', '').strip()
    type_ = request.args.get('type', '').strip()
    if len(q) < 2:
        return jsonify([])

    query = Catalogue.query.filter(Catalogue.titre.ilike(f'{q}%'))
    if type_ in ('serie', 'film'):
        query = query.filter(Catalogue.type == type_)
    resultats = query.order_by(Catalogue.votes.desc().nullslast()).limit(10).all()

    return jsonify([
        {
            'titre': c.titre,
            'type': c.type,
            'annee_debut': c.annee_debut,
            'annee_fin': c.annee_fin,
            'genre': c.genre,
            'note': float(c.note) if c.note is not None else None,
            'duree': c.duree,
        }
        for c in resultats
    ])


def trouver_ou_creer_genre(nom):
    """Retourne l'id du genre (le crée s'il n'existe pas). Utilisé avec l'autocomplétion."""
    if not nom:
        return None
    nom = nom.strip()
    genre = Genre.query.filter_by(nom=nom).first()
    if not genre:
        genre = Genre(nom=nom)
        db.session.add(genre)
        db.session.flush()
    return genre.id


# ---------- AJOUT ----------
@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        try:
            genre_id = request.form.get('genre_id') or None
            if not genre_id and request.form.get('genre_nom'):
                genre_id = trouver_ou_creer_genre(request.form['genre_nom'])
            serie = Serie(
                titre=request.form['titre'],
                annee_debut=request.form.get('annee_debut') or None,
                annee_fin=request.form.get('annee_fin') or None,
                note=request.form.get('note') or None,
                genre_id=genre_id
            )
            db.session.add(serie)
            db.session.commit()
            flash(f'Série « {serie.titre} » ajoutée avec succès !', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur : {str(e)}', 'danger')

    genres = Genre.query.all()
    return render_template('form.html', serie=None, genres=genres)


# ---------- MODIFICATION ----------
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    serie = Serie.query.get_or_404(id)
    if request.method == 'POST':
        try:
            serie.titre = request.form['titre']
            serie.annee_debut = request.form.get('annee_debut') or None
            serie.annee_fin = request.form.get('annee_fin') or None
            serie.note = request.form.get('note') or None
            serie.genre_id = request.form.get('genre_id') or None
            db.session.commit()
            flash(f'Série « {serie.titre} » modifiée !', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur : {str(e)}', 'danger')

    genres = Genre.query.all()
    return render_template('form.html', serie=serie, genres=genres)


# ---------- SUPPRESSION ----------
@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    serie = Serie.query.get_or_404(id)
    titre = serie.titre
    db.session.delete(serie)
    db.session.commit()
    flash(f'Série « {titre} » supprimée.', 'success')
    return redirect(url_for('index'))


# ---------- EXPORT CSV ----------
@app.route('/export')
def export_csv():
    series = Serie.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'titre', 'annee_debut', 'annee_fin', 'note', 'genre_id'])
    for s in series:
        writer.writerow([s.id, s.titre, s.annee_debut, s.annee_fin, s.note, s.genre_id])
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=tvinsight_series.csv'}
    )


# ---------- IMPORT CSV ----------
@app.route('/import', methods=['POST'])
def import_csv():
    file = request.files.get('file')
    if not file:
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('index'))
    try:
        stream = io.StringIO(file.stream.read().decode('UTF-8'))
        reader = csv.DictReader(stream)
        count = 0
        for row in reader:
            db.session.add(Serie(
                titre=row['titre'],
                annee_debut=row.get('annee_debut') or None,
                annee_fin=row.get('annee_fin') or None,
                note=row.get('note') or None,
                genre_id=row.get('genre_id') or None
            ))
            count += 1
        db.session.commit()
        flash(f'{count} série(s) importée(s) avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur d'import : {str(e)}", 'danger')
    return redirect(url_for('index'))


# ---------- STATISTIQUES ----------
@app.route('/stats')
def stats():
    start = time.time()

    top_series = db.session.query(Serie.titre, Serie.note) \
        .filter(Serie.note.isnot(None)) \
        .order_by(Serie.note.desc()).limit(5).all()

    par_genre = db.session.query(Genre.nom, db.func.count(Serie.id)) \
        .join(Serie, Serie.genre_id == Genre.id) \
        .group_by(Genre.nom).all()

    longues = db.session.query(Serie.titre, db.func.count(Saison.id)) \
        .join(Saison).group_by(Serie.titre) \
        .having(db.func.count(Saison.id) > 3).all()

    roles = db.session.query(Acteur.nom, Acteur.prenom, Role.nom_personnage, Serie.titre) \
        .join(Role, Role.acteur_id == Acteur.id) \
        .join(Serie, Role.serie_id == Serie.id).limit(10).all()

    duree = round((time.time() - start) * 1000, 2)

    return render_template(
        'stats.html',
        top_series=top_series,
        par_genre=par_genre,
        longues=longues,
        roles=roles,
        duree=duree
    )


# ---------- COMMANDE CLI ----------
@app.cli.command('init-db')
def init_db():
    db.create_all()
    print("Base initialisée.")


# ---------- FILMS ----------
@app.route('/films')
def films():
    tous_films = Film.query.order_by(Film.titre).limit(500).all()
    return render_template('films.html', films=tous_films)


@app.route('/films/add', methods=['GET', 'POST'])
def add_film():
    if request.method == 'POST':
        try:
            genre_id = request.form.get('genre_id') or None
            if not genre_id and request.form.get('genre_nom'):
                genre_id = trouver_ou_creer_genre(request.form['genre_nom'])
            film = Film(
                titre=request.form['titre'],
                annee=request.form.get('annee') or None,
                note=request.form.get('note') or None,
                duree=request.form.get('duree') or None,
                synopsis=request.form.get('synopsis') or None,
                genre_id=genre_id
            )
            db.session.add(film)
            db.session.commit()
            flash(f'Film « {film.titre} » ajouté !', 'success')
            return redirect(url_for('films'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur : {str(e)}', 'danger')
    genres = Genre.query.all()
    return render_template('form_film.html', film=None, genres=genres)


# ---------- PLATEFORMES ----------
@app.route('/plateformes')
def plateformes():
    toutes_plateformes = Plateforme.query.order_by(Plateforme.nom).all()
    return render_template('plateformes.html', plateformes=toutes_plateformes)


# ---------- RECOMMANDATIONS ----------
@app.route('/recommandations')
def recommandations():
    genres_populaires = db.session.query(
        Genre.nom, db.func.count(Serie.id).label('nb')
    ).join(Serie, Serie.genre_id == Genre.id) \
     .group_by(Genre.nom).order_by(db.func.count(Serie.id).desc()).limit(5).all()

    top_series = Serie.query.filter(Serie.note.isnot(None)) \
        .order_by(Serie.note.desc()).limit(10).all()

    top_films = Film.query.filter(Film.note.isnot(None)) \
        .order_by(Film.note.desc()).limit(10).all()

    series_par_plateforme = {}
    for p in Plateforme.query.all():
        series_par_plateforme[p.nom] = p.series[:5]

    return render_template(
        'recommandations.html',
        genres_populaires=genres_populaires,
        top_series=top_series,
        top_films=top_films,
        series_par_plateforme=series_par_plateforme
    )


# ---------- STATISTIQUES DYNAMIQUES ----------
@app.route('/stats/dynamique')
def stats_dynamique():
    """Ex: /stats/dynamique?type=saisons"""
    type_stats = request.args.get('type', 'top')
    resultats = []
    titre_stats = ""
    colonne1 = ""
    colonne2 = ""

    if type_stats == 'top':
        resultats = db.session.query(Serie.titre, Serie.note) \
            .filter(Serie.note.isnot(None)) \
            .order_by(Serie.note.desc()).limit(20).all()
        titre_stats = "Top 20 des séries les mieux notées"
        colonne1, colonne2 = "Titre", "Note"

    elif type_stats == 'saisons':
        resultats = db.session.query(
            Serie.titre, db.func.count(Saison.id).label('nb_saisons')
        ).join(Saison).group_by(Serie.titre) \
         .order_by(db.func.count(Saison.id).desc()).limit(20).all()
        titre_stats = "Top 20 des séries avec le plus de saisons"
        colonne1, colonne2 = "Titre", "Nombre de saisons"

    elif type_stats == 'episodes':
        resultats = db.session.query(
            Serie.titre, db.func.sum(Saison.nb_episodes).label('total')
        ).join(Saison).group_by(Serie.titre) \
         .order_by(db.func.sum(Saison.nb_episodes).desc()).limit(20).all()
        titre_stats = "Top 20 des séries avec le plus d'épisodes"
        colonne1, colonne2 = "Titre", "Nombre d'épisodes"

    elif type_stats == 'genres':
        resultats = db.session.query(
            Genre.nom, db.func.count(Serie.id).label('nb')
        ).join(Serie, Serie.genre_id == Genre.id) \
         .group_by(Genre.nom).order_by(db.func.count(Serie.id).desc()).all()
        titre_stats = "Répartition par genre"
        colonne1, colonne2 = "Genre", "Nombre de séries"

    elif type_stats == 'annees':
        resultats = db.session.query(
            Serie.annee_debut, db.func.count(Serie.id).label('nb')
        ).filter(Serie.annee_debut.isnot(None)) \
         .group_by(Serie.annee_debut) \
         .order_by(Serie.annee_debut.desc()).limit(30).all()
        titre_stats = "Séries par année de début (30 dernières)"
        colonne1, colonne2 = "Année", "Nombre de séries"

    elif type_stats == 'plateformes':
        resultats = db.session.query(
            Plateforme.nom, db.func.count(Serie.id).label('nb')
        ).join(serie_plateforme) \
         .join(Serie, Serie.id == serie_plateforme.c.serie_id) \
         .group_by(Plateforme.nom) \
         .order_by(db.func.count(Serie.id).desc()).all()
        titre_stats = "Nombre de séries par plateforme"
        colonne1, colonne2 = "Plateforme", "Nombre de séries"

    return render_template(
        'stats_dynamique.html',
        type_stats=type_stats,
        titre_stats=titre_stats,
        colonne1=colonne1,
        colonne2=colonne2,
        resultats=resultats
    )


# ---------- LANCEMENT ----------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
