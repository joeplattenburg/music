import argparse
from functools import reduce
from operator import add
import os
import time

from flask import Flask, render_template, request, url_for, flash, redirect
from markupsafe import escape

from music import music

STATIC_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static')
TEMPLATE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')

app = Flask(
    'music',
    static_folder=STATIC_DIR,
    template_folder=TEMPLATE_DIR,
)
app.config['SECRET_KEY'] = os.urandom(24).hex()
SAMPLE_RATE = 11_025
NOTE_DURATION = 2.0


def cleanup() -> None:
    if os.path.isfile(os.path.join(STATIC_DIR, 'temp.png')):
        os.remove(os.path.join(STATIC_DIR, 'temp.png'))
    if os.path.isfile(os.path.join(STATIC_DIR, 'temp.wav')):
        os.remove(os.path.join(STATIC_DIR, 'temp.wav'))


@app.route("/", methods=('GET', 'POST'))
def home():
    return render_template('base.html')


@app.route("/guitar_positions", methods=('GET', 'POST'))
def guitar_positions():
    if request.method == 'POST':
        tuning_name = request.form['tuning_name'].strip()
        tuning = request.form['tuning'].strip()
        tuning = 'custom;' + tuning if tuning_name == 'custom' and tuning else tuning_name
        top_n = request.form['top_n'].strip() or '-1'
        max_fret_span = request.form['max_fret_span'].strip() or str(music.DEFAULT_MAX_FRET_SPAN)
        notes_string = request.form['notes'].strip()
        chord_name = request.form['chord_name'].strip()
        allow_repeats = request.form.get('allow_repeats', '').strip() or 'false'
        allow_identical = request.form.get('allow_identical', '').strip() or 'false'
        show_fingers = request.form.get('show_fingers', '').strip() or 'false'
        allow_thumb = request.form.get('allow_thumb', '').strip() or 'false'
        all_voicings = request.form.get('all_voicings', '').strip() or 'false'
        if notes_string:
            return redirect(url_for(
                'guitar_positions_display_notes',
                notes_string=notes_string,
                top_n='top_n=' + top_n,
                max_fret_span='max_fret_span=' + max_fret_span,
                tuning='tuning=' + tuning,
                show_fingers='show_fingers=' + show_fingers,
                allow_thumb='allow_thumb=' + allow_thumb,
            ))
        elif chord_name:
            try:
                music.ChordName(chord_name)
                return redirect(url_for(
                    'guitar_positions_display_name',
                    chord_name=chord_name.replace('/', '_'),
                    top_n='top_n=' + top_n,
                    max_fret_span='max_fret_span=' + max_fret_span,
                    tuning='tuning=' + tuning,
                    allow_repeats='allow_repeats=' + allow_repeats,
                    allow_identical='allow_identical=' + allow_identical,
                    show_fingers='show_fingers=' + show_fingers,
                    allow_thumb='allow_thumb=' + allow_thumb,
                    all_voicings='all_voicings=' + all_voicings,
                ))
            except ValueError as e:
                flash(f'Invalid chord name! ({e})')
        else:
            flash('Either notes or name are required!')
    return render_template('guitar_positions_input.html')


@app.route(
    "/guitar_positions/notes/<notes_string>"
    "/<top_n>/<max_fret_span>/<tuning>/<show_fingers>/<allow_thumb>"
)
def guitar_positions_display_notes(
        notes_string: str,
        top_n: str,
        max_fret_span: str,
        tuning: str,
        show_fingers: str,
        allow_thumb: str,
) -> str:
    top_n_ = int(escape(top_n).split('=')[1])
    if top_n_ < 0:
        top_n_ = None
    max_fret_span_ = int(escape(max_fret_span).split('=')[1])
    tuning_ = escape(tuning).split('=')[1]
    show_fingers_: bool = escape(show_fingers).split('=')[1] == 'true'
    allow_thumb_: bool = escape(allow_thumb).split('=')[1] == 'true'
    notes_list = [music.Note.from_string(note) for note in escape(notes_string).split(',')]
    chord = music.Chord(notes_list)
    if music.media_installed:
        chord.to_audio(
            sample_rate=SAMPLE_RATE, duration=NOTE_DURATION
        ).write_wav(
            os.path.join(STATIC_DIR, 'temp.wav')
        )
        music.Staff(chords=[chord]).write_png(os.path.join(STATIC_DIR, 'temp.png'))
    else:
        cleanup()
    if tuning_.startswith('custom'):
        tuning_ = tuning_.split(';', maxsplit=1)[1]
        guitar = music.Guitar(tuning=music.Guitar.parse_tuning(tuning_, how='csv'))
    else:
        guitar = music.Guitar(tuning_name=tuning_)
    t1 = time.time()
    positions_playable = chord.guitar_positions(
        guitar=guitar, max_fret_span=max_fret_span_, include_unplayable=False, allow_thumb=allow_thumb_
    )
    positions_all = chord.num_total_guitar_positions
    positions = music.GuitarPosition.sorted(positions_playable)[:top_n_]
    positions_printable = ['<br>'.join(p.printable(fingers=show_fingers_)) for p in positions]
    elapsed_time = f'{(time.time() - t1):.2f}'
    return render_template(
        'guitar_positions_display.html',
        chord=chord, tuning=tuning_, positions=positions_printable, chords_n=1,
        total_n=positions_all, playable_n=len(positions_playable), elapsed_time=elapsed_time
    )


@app.route(
    "/guitar_positions/chord_name/<chord_name>"
    "/<top_n>/<max_fret_span>/<tuning>/<allow_repeats>/<allow_identical>/<show_fingers>/<allow_thumb>/<all_voicings>"
)
def guitar_positions_display_name(
        chord_name: str,
        top_n: str,
        max_fret_span: str,
        tuning: str,
        allow_repeats: str,
        allow_identical: str,
        show_fingers: str,
        allow_thumb: str,
        all_voicings: str
) -> str:
    chord_name_ = escape(chord_name).replace('_', '/')
    top_n_ = int(escape(top_n).split('=')[1])
    if top_n_ < 0:
        top_n_ = None
    max_fret_span_ = int(escape(max_fret_span).split('=')[1])
    tuning_ = escape(tuning).split('=')[1]
    allow_repeats_: bool = escape(allow_repeats).split('=')[1] == 'true'
    allow_identical_: bool = escape(allow_identical).split('=')[1] == 'true'
    show_fingers_: bool = escape(show_fingers).split('=')[1] == 'true'
    allow_thumb_: bool = escape(allow_thumb).split('=')[1] == 'true'
    all_voicings_: bool = escape(all_voicings).split('=')[1] == 'true'
    if tuning_.startswith('custom'):
        tuning_ = tuning_.split(';', maxsplit=1)[1]
        guitar = music.Guitar(tuning=music.Guitar.parse_tuning(tuning_, how='csv'))
    else:
        guitar = music.Guitar(tuning_name=tuning_)
    t1 = time.time()
    chord = music.ChordName(chord_name_)
    low_chord = chord.get_chord(lower=music.Note('E', 2))
    positions_all = music.get_all_guitar_positions_for_chord_name(
        chord_name=chord,
        guitar=guitar,
        max_fret_span=max_fret_span_,
        allow_repeats=allow_repeats_,
        allow_identical=allow_identical_,
        allow_thumb=allow_thumb_,
        parallel=True,
    )
    positions_playable = list(filter(lambda x: (x.playable and not x.redundant), positions_all))
    if allow_repeats_:
        positions_playable = music.GuitarPosition.filter_subsets(positions_playable)
    chords_playable = sorted(list(set(p.chord for p in positions_playable)))
    chords_print = chords_playable if all_voicings_ else [low_chord]
    if music.media_installed:
        music.Staff(chords=chords_print).write_png(os.path.join(STATIC_DIR, 'temp.png'))
        low_chord.to_audio(
            sample_rate=SAMPLE_RATE, duration=NOTE_DURATION
        ).write_wav(
            os.path.join(STATIC_DIR, 'temp.wav')
        )
    else:
        cleanup()
    positions = music.GuitarPosition.sorted(positions_playable)[:top_n_]
    positions_printable = ['<br>'.join(p.printable(fingers=show_fingers_)) for p in positions]
    elapsed_time = f'{(time.time() - t1):.2f}'
    return render_template(
        'guitar_positions_display.html',
        chord=chord_name_, tuning=tuning_, positions=positions_printable, chords_n=len(chords_playable),
        total_n=len(positions_all), playable_n=len(positions_playable), elapsed_time=elapsed_time
    )


@app.route("/guitar_chord_progression", methods=('GET', 'POST'))
def guitar_chord_progression():
    if request.method == 'POST':
        chords_string = request.form['chords'].strip()
        allow_repeats = request.form.get('allow_repeats', '').strip() or 'false'
        show_fingers = request.form.get('show_fingers', '').strip() or 'false'
        return redirect(url_for(
            'guitar_chord_progression_display',
            chords_string=chords_string,
            allow_repeats='allow_repeats=' + allow_repeats,
            show_fingers='show_fingers=' + show_fingers,
        ))
    return render_template('guitar_chord_progression_input.html')


@app.route("/guitar_chord_progression/<chords_string>/<allow_repeats>/<show_fingers>", methods=('GET', 'POST'))
def guitar_chord_progression_display(
        chords_string: str,
        allow_repeats: str,
        show_fingers: str,
):
    t1 = time.time()
    chord_progression = music.ChordProgression(
        [music.ChordName(chord) for chord in escape(chords_string).split(',')]
    )
    allow_repeats_: bool = escape(allow_repeats).split('=')[1] == 'true'
    show_fingers_: bool = escape(show_fingers).split('=')[1] == 'true'
    opt_positions = chord_progression.optimal_guitar_positions(allow_repeats=allow_repeats_)
    opt_chords = [p.chord for p in opt_positions]
    if music.media_installed and opt_chords:
        audio = reduce(add, (chord.to_audio(sample_rate=SAMPLE_RATE, duration=NOTE_DURATION) for chord in opt_chords))
        audio.write_wav(os.path.join(STATIC_DIR, 'temp.wav'))
        music.Staff(chords=opt_chords).write_png(os.path.join(STATIC_DIR, 'temp.png'))
    else:
        cleanup()
    positions_printable = ['<br>'.join(p.printable(fingers=show_fingers_)) for p in opt_positions]
    elapsed_time = f'{(time.time() - t1):.2f}'
    return render_template(
        'guitar_chord_progression_display.html',
        chords=chords_string, positions=positions_printable, elapsed_time=elapsed_time
    )


@app.route("/voice_leading", methods=('GET', 'POST'))
def voice_leading():
    if request.method == 'POST':
        chords_string = request.form['chords'].strip()
        lower = request.form['lower'].strip() or 'G2'
        upper = request.form['upper'].strip() or 'G5'
        return redirect(url_for(
            'voice_leading_display',
            chords_string=chords_string,
            lower='lower=' + lower,
            upper='upper=' + upper,
        ))
    return render_template('voice_leading_input.html')


@app.route("/voice_leading/<chords_string>/<lower>/<upper>", methods=('GET', 'POST'))
def voice_leading_display(chords_string: str, lower: str, upper: str):
    t1 = time.time()
    chord_progression = music.ChordProgression(
        [music.ChordName(chord) for chord in escape(chords_string).split(',')]
    )
    lower_ = music.Note.from_string(escape(lower).split('=')[1])
    upper_ = music.Note.from_string(escape(upper).split('=')[1])
    opt_chords = chord_progression.optimal_voice_leading(lower=lower_, upper=upper_)
    if music.media_installed:
        audio = reduce(add, (chord.to_audio(sample_rate=SAMPLE_RATE, duration=NOTE_DURATION) for chord in opt_chords))
        audio.write_wav(os.path.join(STATIC_DIR, 'temp.wav'))
        music.Staff(chords=opt_chords).write_png(os.path.join(STATIC_DIR, 'temp.png'))
    else:
        cleanup()
    elapsed_time = f'{(time.time() - t1):.2f}'
    return render_template(
        'voice_leading_display.html',
        chords=chords_string,
        elapsed_time=elapsed_time
    )


def main():
    parser = argparse.ArgumentParser(description='Run music helpers web app')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    app.run(debug=args.debug, port=args.port, host='0.0.0.0')


if __name__ == '__main__':
    main()
