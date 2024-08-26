import argparse
import os
import time

from flask import Flask, render_template, request, url_for, flash, redirect
from markupsafe import escape

import music

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()


@app.route("/", methods=('GET', 'POST'))
def input():
    if request.method == 'POST':
        guitar = music.Guitar(music.Guitar.parse_tuning(request.form['tuning']))
        tuning = 'standard' if guitar.tuning_name == 'standard' else 'custom;' + request.form['tuning']
        top_n = request.form['top_n'] or '-1'
        notes_string = request.form['notes']
        chord_name = request.form['chord_name']
        allow_repeats = request.form.get('allow_repeats') or 'false'
        allow_identical = request.form.get('allow_identical') or 'false'
        allow_thumb = request.form.get('allow_thumb') or 'false'
        if notes_string:
            return redirect(url_for(
                'display_notes',
                notes_string=notes_string,
                top_n='top_n=' + top_n,
                tuning='tuning=' + tuning,
                allow_thumb='allow_thumb=' + allow_thumb,
            ))
        elif chord_name:
            try:
                music.ChordName(chord_name)
                return redirect(url_for(
                    'display_name',
                    chord_name=chord_name.replace('/', '_'),
                    top_n='top_n=' + top_n,
                    tuning='tuning=' + tuning,
                    allow_repeats='allow_repeats=' + allow_repeats,
                    allow_identical='allow_identical=' + allow_identical,
                    allow_thumb='allow_thumb=' + allow_thumb,
                ))
            except ValueError as e:
                flash(f'Invalid chord name! ({e})')
        else:
            flash('Either notes or name are required!')
    return render_template('input.html')


@app.route("/notes/<notes_string>/<top_n>/<tuning>/<allow_thumb>")
def display_notes(notes_string: str, top_n: str, tuning: str, allow_thumb: str) -> str:
    top_n_ = int(escape(top_n).split('=')[1])
    if top_n_ < 0:
        top_n_ = None
    tuning_ = escape(tuning).split('=')[1]
    allow_thumb_: bool = escape(allow_thumb).split('=')[1] == 'true'
    notes_list = [music.Note.from_string(note) for note in escape(notes_string).split(',')]
    chord = music.Chord(notes_list)
    guitar = (
        music.Guitar() if tuning_ == 'standard' else
        music.Guitar(tuning=music.Guitar.parse_tuning(tuning_.split(';')[1]))
    )
    t1 = time.time()
    positions_playable = chord.guitar_positions(guitar=guitar, include_unplayable=False, allow_thumb=allow_thumb_)
    positions_all = chord.num_total_guitar_positions
    positions = music.sort_guitar_positions(positions_playable)[:top_n_]
    positions_printable = ['<br>'.join(p.printable()) for p in positions]
    elapsed_time = f'{(time.time() - t1):.2f}'
    return render_template(
        'display.html',
        chord=chord, tuning=tuning_, positions=positions_printable,
        total_n=positions_all, playable_n=len(positions_playable), elapsed_time=elapsed_time
    )


@app.route("/chord_name/<chord_name>/<top_n>/<tuning>/<allow_repeats>/<allow_identical>/<allow_thumb>")
def display_name(
        chord_name: str, top_n: str, tuning: str, allow_repeats: str, allow_identical: str, allow_thumb: str
) -> str:
    chord_name_ = escape(chord_name).replace('_', '/')
    top_n_ = int(escape(top_n).split('=')[1])
    if top_n_ < 0:
        top_n_ = None
    tuning_ = escape(tuning).split('=')[1]
    allow_repeats_: bool = escape(allow_repeats).split('=')[1] == 'true'
    allow_identical_: bool = escape(allow_identical).split('=')[1] == 'true'
    allow_thumb_: bool = escape(allow_thumb).split('=')[1] == 'true'
    guitar = (
        music.Guitar() if tuning_ == 'standard' else
        music.Guitar(tuning=music.Guitar.parse_tuning(tuning_.split(';')[1]))
    )
    t1 = time.time()
    positions_all = music.get_all_guitar_positions_for_chord_name(
        chord_name=music.ChordName(chord_name_),
        guitar=guitar,
        allow_repeats=allow_repeats_,
        allow_identical=allow_identical_,
        allow_thumb=allow_thumb_,
        parallel=True,
    )
    positions_playable = list(filter(lambda x: (x.playable and not x.redundant), positions_all))
    if allow_repeats_:
        positions_playable = music.filter_subset_guitar_positions(positions_playable)
    positions = music.sort_guitar_positions(positions_playable)[:top_n_]
    positions_printable = ['<br>'.join(p.printable()) for p in positions]
    elapsed_time = f'{(time.time() - t1):.2f}'
    return render_template(
        'display.html',
        chord=chord_name_, tuning=tuning_, positions=positions_printable,
        total_n=len(positions_all), playable_n=len(positions_playable), elapsed_time=elapsed_time
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the Guitar Position Calculator web server')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    app.run(debug=args.debug, port=args.port, host='0.0.0.0')
