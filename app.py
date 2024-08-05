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
        top_n = request.form['top_n']
        if not notes_string:
            flash('Notes are required!')
        elif not top_n:
            flash('Number of positions is required!')
        else:
            return redirect(url_for('display', notes_string=notes_string, top_n=top_n))
    return render_template('input.html')


@app.route("/<notes_string>/<int:top_n>/")
def display(notes_string: str, top_n: int) -> str:
    notes_list = [notes.Note.from_string(note) for note in escape(notes_string).split(',')]
    chord = notes.Chord(notes_list)
    positions = chord.guitar_positions()[:top_n]
    positions_printable = ['<br>'.join(p.printable()) for p in positions]
    return render_template(
        'display.html',
        chord=chord, top_n=top_n, positions=positions_printable
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
