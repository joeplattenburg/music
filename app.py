import argparse
import os

from flask import Flask, render_template, request, url_for, flash, redirect
from markupsafe import escape

import notes

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()


@app.route("/", methods=('GET', 'POST'))
def input():
    if request.method == 'POST':
        guitar = notes.Guitar(notes.Guitar.parse_tuning(request.form['tuning']))
        tuning = 'standard' if guitar.tuning_name == 'standard' else 'custom;' + request.form['tuning']
        top_n = request.form['top_n'] or 0
        notes_string = request.form['notes']
        chord_name = request.form['chord_name']
        if notes_string:
            return redirect(url_for(
                'display_notes',
                notes_string=notes_string, top_n=top_n, tuning=tuning
            ))
        elif chord_name:
            try:
                notes.ChordName(chord_name)
                return redirect(url_for(
                    'display_name',
                    chord_name=chord_name.replace('/', '_'), top_n=top_n, tuning=tuning
                ))
            except ValueError:
                flash('Invalid chord name!')
        else:
            flash('Either notes or name are required!')
    return render_template('input.html')


@app.route("/notes/<notes_string>/<int:top_n>/<tuning>/")
def display_notes(notes_string: str, top_n: int, tuning: str) -> str:
    if top_n == 0:
        top_n = None
    notes_list = [notes.Note.from_string(note) for note in escape(notes_string).split(',')]
    chord = notes.Chord(notes_list)
    guitar = (
        notes.Guitar() if tuning == 'standard' else
        notes.Guitar(tuning=notes.Guitar.parse_tuning(tuning.split(';')[1]))
    )
    positions_all = chord.guitar_positions(guitar=guitar)
    positions_playable = list(filter(lambda x: x.playable, positions_all))
    positions = notes.sort_guitar_positions(positions_playable)[:top_n]
    positions_printable = ['<br>'.join(p.printable()) for p in positions]
    return render_template(
        'display.html',
        chord=chord, tuning=tuning, positions=positions_printable,
        total_n=len(positions_all), playable_n=len(positions_playable)
    )


@app.route("/chord_name/<chord_name>/<int:top_n>/<tuning>/")
def display_name(chord_name: str, top_n: int, tuning: str) -> str:
    if top_n == 0:
        top_n = None
    guitar = (
        notes.Guitar() if tuning == 'standard' else
        notes.Guitar(tuning=notes.Guitar.parse_tuning(tuning.split(';')[1]))
    )
    chord_name = chord_name.replace('_', '/')
    chords = notes.ChordName(escape(chord_name)).get_all_chords(lower=guitar.lowest, upper=guitar.highest)
    positions_all = []
    for chord in chords:
        positions_all += chord.guitar_positions(guitar=guitar)
    positions_playable = list(filter(lambda x: x.playable, positions_all))
    positions = notes.sort_guitar_positions(positions_playable)[:top_n]
    positions_printable = ['<br>'.join(p.printable()) for p in positions]
    return render_template(
        'display.html',
        chord=chord_name, tuning=tuning, positions=positions_printable,
        total_n=len(positions_all), playable_n=len(positions_playable)
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the Guitar Position Calculator web server')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    app.run(debug=args.debug, port=args.port, host='0.0.0.0')
