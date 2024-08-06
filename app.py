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
        notes_string = request.form['notes']
        top_n = request.form['top_n'] or 5
        tuning = (
            request.form['tuning'] or
            str({string: str(note) for string, note in notes.Guitar.STANDARD_TUNING.items()})
        )
        if not notes_string:
            flash('Notes are required!')
        else:
            return redirect(url_for('display', notes_string=notes_string, top_n=top_n, tuning=tuning))
    return render_template('input.html')


@app.route("/<notes_string>/<int:top_n>/<tuning>/")
def display(notes_string: str, top_n: int, tuning: str) -> str:
    notes_list = [notes.Note.from_string(note) for note in escape(notes_string).split(',')]
    chord = notes.Chord(notes_list)
    guitar = notes.Guitar(tuning=notes.Guitar.parse_tuning(tuning))
    positions = chord.guitar_positions(guitar=guitar)[:top_n]
    positions_printable = ['<br>'.join(p.printable()) for p in positions]
    return render_template(
        'display.html',
        chord=chord, tuning=tuning, top_n=top_n, positions=positions_printable
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the Guitar Position Calculator web server')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    app.run(debug=args.debug, port=args.port, host='0.0.0.0')
