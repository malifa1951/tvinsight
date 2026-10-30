"""
Ajoute les plateformes de diffusion par défaut.
"""
from app import app, db
from models import Plateforme

PLATEFORMES = [
    {'nom': 'Netflix', 'url': 'https://www.netflix.com', 'couleur': '#E50914'},
    {'nom': 'Prime Video', 'url': 'https://www.primevideo.com', 'couleur': '#00A8E1'},
    {'nom': 'Disney+', 'url': 'https://www.disneyplus.com', 'couleur': '#113CCF'},
    {'nom': 'Canal+', 'url': 'https://www.canalplus.com', 'couleur': '#000000'},
    {'nom': 'OCS', 'url': 'https://www.ocs.fr', 'couleur': '#F07D00'},
    {'nom': 'Apple TV+', 'url': 'https://tv.apple.com', 'couleur': '#000000'},
    {'nom': 'HBO Max', 'url': 'https://www.hbomax.com', 'couleur': '#5C2D91'},
    {'nom': 'Paramount+', 'url': 'https://www.paramountplus.com', 'couleur': '#0064FF'},
]

with app.app_context():
    for p in PLATEFORMES:
        if not Plateforme.query.filter_by(nom=p['nom']).first():
            db.session.add(Plateforme(**p))
    db.session.commit()
    print(f"✅ {Plateforme.query.count()} plateformes en base")