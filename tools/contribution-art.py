#!/usr/bin/env python3
"""Écrit un texte en pixel art dans le graphe de contributions GitHub.

Principe : le calendrier GitHub = 1 colonne par semaine (dimanche en haut),
1 case par jour. On crée des commits vides datés sur les bons jours, dans un
dépôt dédié ; une fois poussés, les cases s'allument.

Usage :
    python3 contribution-art.py --dir ~/Jo/pro-perso/contribution-art \\
        --email EMAIL-DU-COMPTE-JOSH14MAX            # aperçu + confirmation
    python3 contribution-art.py ... --dry-run        # aperçu seulement

Le texte est aligné sur la dernière semaine complète : il reste entier
environ (52 - largeur) semaines, puis glisse vers la gauche. Pour le
rafraîchir, relance le script avec --reset puis force-push.
Pour tout effacer : supprime le dépôt sur GitHub.
"""
import argparse
import datetime as dt
import os
import subprocess
import sys

# Police 5 lignes (posée du lundi au vendredi, dimanche/samedi vides)
FONT = {
    'J': ['###', '..#', '..#', '#.#', '##.'],
    'O': ['###', '#.#', '#.#', '#.#', '###'],
    'S': ['###', '#..', '###', '..#', '###'],
    'H': ['#.#', '#.#', '###', '#.#', '#.#'],
    '1': ['.#.', '##.', '.#.', '.#.', '###'],
    '4': ['#.#', '#.#', '###', '..#', '..#'],
    'M': ['#...#', '##.##', '#.#.#', '#...#', '#...#'],
    'A': ['.#.', '#.#', '###', '#.#', '#.#'],
    'X': ['#.#', '#.#', '.#.', '#.#', '#.#'],
    ' ': ['.', '.', '.', '.', '.'],
}
WEEKS = 52  # colonnes complètes affichées (la 53e = semaine en cours)


def render(text):
    cols = []
    for i, ch in enumerate(text.upper()):
        glyph = FONT[ch]
        if i:
            cols.append([0] * 7)  # espace entre lettres
        for x in range(len(glyph[0])):
            cols.append([0] + [1 if glyph[y][x] == '#' else 0 for y in range(5)] + [0])
    return cols


def plan(text, today):
    cols = render(text)
    if len(cols) > WEEKS:
        sys.exit(f'Texte trop large : {len(cols)} colonnes > {WEEKS}')
    this_sunday = today - dt.timedelta(days=(today.weekday() + 1) % 7)
    last_full = this_sunday - dt.timedelta(weeks=1)
    first = last_full - dt.timedelta(weeks=len(cols) - 1)
    days = []
    for c, col in enumerate(cols):
        for r, on in enumerate(col):
            if on:
                days.append(first + dt.timedelta(weeks=c, days=r))
    return cols, days


def preview(cols):
    names = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam']
    for r in range(7):
        print(f'{names[r]} ' + ''.join('█' if col[r] else '·' for col in cols))


def git(*args, cwd, env=None):
    subprocess.run(['git', *args], cwd=cwd, check=True, env=env,
                   stdout=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--text', default='JOSH14MAX')
    ap.add_argument('--dir', required=True, help='dossier du dépôt dédié')
    ap.add_argument('--email', help='email du compte GitHub (obligatoire sauf --dry-run)')
    ap.add_argument('--name', default='josh14max')
    ap.add_argument('--commits', type=int, default=10,
                    help='commits par case (>= ton max réel par jour pour une couleur vive)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--reset', action='store_true', help='repartir d\'un historique vide')
    a = ap.parse_args()

    cols, days = plan(a.text, dt.date.today())
    print(f'\n{a.text} : {len(cols)} semaines, du {days[0]} au {max(days)}\n')
    preview(cols)
    total = len(days) * a.commits
    print(f'\n{len(days)} cases × {a.commits} commits = {total} contributions ajoutées\n')
    if a.dry_run:
        return
    if not a.email:
        sys.exit('--email est obligatoire (celui du compte josh14max)')
    if input('Créer ces commits ? [o/N] ').strip().lower() not in ('o', 'oui', 'y', 'yes'):
        return

    d = os.path.expanduser(a.dir)
    os.makedirs(d, exist_ok=True)
    if a.reset or not os.path.isdir(os.path.join(d, '.git')):
        if a.reset and os.path.isdir(os.path.join(d, '.git')):
            git('checkout', '-q', '--orphan', 'tmp-reset', cwd=d)
            git('branch', '-D', 'main', cwd=d)
            git('branch', '-m', 'main', cwd=d)
        else:
            git('init', '-q', '-b', 'main', cwd=d)
    git('config', 'user.email', a.email, cwd=d)
    git('config', 'user.name', a.name, cwd=d)
    with open(os.path.join(d, 'README.md'), 'w') as fh:
        fh.write(f'# contribution-art\n\nPixel art « {a.text} » dans mon graphe de contributions, '
                 'généré par commits vides datés. Ce ne sont pas de vraies contributions.\n')
    git('add', 'README.md', cwd=d)

    for i, day in enumerate(days):
        for k in range(a.commits):
            stamp = f'{day.isoformat()}T12:{k:02d}:00+01:00'
            env = dict(os.environ, GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
            git('commit', '-q', '--allow-empty', '-m', f'art: {a.text} {day} #{k+1}', cwd=d, env=env)
        print(f'\r{i+1}/{len(days)} jours', end='', flush=True)
    print('\nTerminé. Pousse avec : git push -u --force origin main')


if __name__ == '__main__':
    main()
