// Autocomplétion des titres via /api/suggest (catalogue IMDb importé)
(function () {
    const input = document.querySelector('input[data-suggest-type]');
    if (!input) return;

    const type = input.dataset.suggestType;           // 'serie' ou 'film'
    const list = document.getElementById('suggest-list');
    const hint = document.getElementById('suggest-hint');
    const form = input.form;
    let cache = {};
    let timer = null;

    function champ(nom) {
        return form.elements[nom];
    }

    function remplir(nom, valeur) {
        const el = champ(nom);
        if (el && valeur !== null && valeur !== undefined) el.value = valeur;
    }

    function appliquer(d) {
        if (type === 'film') {
            remplir('annee', d.annee_debut);
            remplir('duree', d.duree);
        } else {
            remplir('annee_debut', d.annee_debut);
            remplir('annee_fin', d.annee_fin);
        }
        remplir('note', d.note);

        // Genre : on sélectionne le genre existant s'il porte le même nom,
        // sinon on l'envoie dans genre_nom (le serveur le crée).
        const select = champ('genre_id');
        const genreNom = champ('genre_nom');
        if (d.genre && select && genreNom) {
            let trouve = false;
            for (const opt of select.options) {
                if (opt.text.trim().toLowerCase() === d.genre.toLowerCase()) {
                    select.value = opt.value;
                    genreNom.value = '';
                    trouve = true;
                    break;
                }
            }
            if (!trouve) {
                select.value = '';
                genreNom.value = d.genre;
            }
        }
        if (hint) hint.textContent = d.genre ? 'Genre suggéré : ' + d.genre : '';
    }

    input.addEventListener('input', function (e) {
        // Choix dans la liste : le navigateur ne donne pas de inputType de saisie
        const choisi = !e.inputType || e.inputType === 'insertReplacementText';
        if (choisi && cache[input.value]) {
            appliquer(cache[input.value]);
            return;
        }

        const q = input.value.trim();
        if (q.length < 2) {
            list.innerHTML = '';
            return;
        }

        clearTimeout(timer);
        timer = setTimeout(async function () {
            try {
                const r = await fetch('/api/suggest?q=' + encodeURIComponent(q) + '&type=' + type);
                const data = await r.json();
                cache = {};
                list.innerHTML = '';
                data.forEach(function (d) {
                    if (!(d.titre in cache)) cache[d.titre] = d;   // le plus voté en premier
                    const o = document.createElement('option');
                    o.value = d.titre;
                    o.label = [d.annee_debut, d.genre].filter(Boolean).join(' · ');
                    list.appendChild(o);
                });
            } catch (err) {
                /* pas de suggestion si le serveur ne répond pas */
            }
        }, 200);
    });
})();
