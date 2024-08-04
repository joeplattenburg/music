import notes

from flask import Flask, render_template
from markupsafe import escape


app = Flask(__name__)


@app.route("/demo")
def info():
    return render_template('info.html')


@app.route("/demo/<notes_string>/<int:top_n>/")
def demo(notes_string: str, top_n: int) -> str:
    notes_list = [notes.Note.from_string(note) for note in escape(notes_string).split(',')]
    chord = notes.Chord(notes_list)
    positions = chord.guitar_positions()[:top_n]
    return render_template(
        'demo.html',
        chord=chord, top_n=top_n, positions=[p.print().replace('\n', '<br>') for p in positions]
    )
