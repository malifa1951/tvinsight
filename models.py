from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ---------- TABLE ASSOCIATION (Serie <-> Plateforme) ----------
serie_plateforme = db.Table(
    'serie_plateforme',
    db.Column('serie_id', db.Integer, db.ForeignKey('serie.id'), primary_key=True),
    db.Column('plateforme_id', db.Integer, db.ForeignKey('plateforme.id'), primary_key=True)
)


# ---------- GENRE ----------
class Genre(db.Model):
    __tablename__ = 'genre'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    series = db.relationship('Serie', backref='genre', lazy=True)
    films = db.relationship('Film', backref='genre', lazy=True)


# ---------- PLATEFORME ----------
class Plateforme(db.Model):
    __tablename__ = 'plateforme'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False, unique=True)
    url = db.Column(db.String(200))
    couleur = db.Column(db.String(20))  # ex: "#E50914" pour Netflix
    series = db.relationship('Serie', secondary=serie_plateforme, backref='plateformes')


# ---------- SERIE ----------
class Serie(db.Model):
    __tablename__ = 'serie'
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(150), nullable=False, index=True)
    annee_debut = db.Column(db.Integer, index=True)
    annee_fin = db.Column(db.Integer)
    note = db.Column(db.Float, index=True)
    synopsis = db.Column(db.Text)
    genre_id = db.Column(db.Integer, db.ForeignKey('genre.id'), index=True)
    saisons = db.relationship('Saison', backref='serie', lazy=True, cascade="all, delete-orphan")
    roles = db.relationship('Role', backref='serie', lazy=True, cascade="all, delete-orphan")


# ---------- FILM ----------
class Film(db.Model):
    __tablename__ = 'film'
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(150), nullable=False, index=True)
    annee = db.Column(db.Integer, index=True)
    note = db.Column(db.Float, index=True)
    duree = db.Column(db.Integer)  # en minutes
    synopsis = db.Column(db.Text)
    genre_id = db.Column(db.Integer, db.ForeignKey('genre.id'), index=True)


# ---------- SAISON ----------
class Saison(db.Model):
    __tablename__ = 'saison'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False)
    nb_episodes = db.Column(db.Integer)
    serie_id = db.Column(db.Integer, db.ForeignKey('serie.id'))


# ---------- ACTEUR ----------
class Acteur(db.Model):
    __tablename__ = 'acteur'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(80), nullable=False)
    prenom = db.Column(db.String(80))
    roles = db.relationship('Role', backref='acteur', lazy=True, cascade="all, delete-orphan")


# ---------- ROLE ----------
class Role(db.Model):
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    nom_personnage = db.Column(db.String(100))
    serie_id = db.Column(db.Integer, db.ForeignKey('serie.id'))
    acteur_id = db.Column(db.Integer, db.ForeignKey('acteur.id'))


# ---------- CATALOGUE (données IMDb importées, sert aux suggestions) ----------
# Source : IMDb Non-Commercial Datasets (usage non commercial)
class Catalogue(db.Model):
    __tablename__ = 'catalogue'
    id = db.Column(db.Integer, primary_key=True)
    imdb_id = db.Column(db.String(12), unique=True)
    type = db.Column(db.String(10), index=True)       # 'serie' ou 'film'
    titre = db.Column(db.String(300), index=True)
    annee_debut = db.Column(db.Integer)
    annee_fin = db.Column(db.Integer)
    genre = db.Column(db.String(50))                  # premier genre IMDb
    note = db.Column(db.Numeric(3, 1))
    votes = db.Column(db.Integer, index=True)
    duree = db.Column(db.Integer)                     # minutes (films)
