# `music`

Helpers for music.

## `notes` Module

Classes include:
- `Note`: define a music note, e.g.: `Note(name='C#', octave=3)`; methods:
  - `guitar_positions`: returns all positions the note can be played
- `Chord`: constructed from a `list[Note]`; methods:
  - `guitar_positions`: returns all positions the chord can be played
- `Guitar`: define a guitar by its tuning and number of frets (can include a capo)
- `GuitarPosition`: the set of fret positions to be played for each string

## Demo

There is a `demo.py` script that will generate guitar chord positions. E.g.:

```commandline
$ python demo.py --notes C3,G3,E4,Bb4 --top_n 3
Here are the top 3 guitar positions for the chord: C3,G3,E4,Bb4
{'E': 8, 'A': 10, 'G': 9, 'B': 11}
{'E': 8, 'A': 10, 'B': 11, 'e': 0}
{'E': 8, 'D': 5, 'B': 5, 'e': 6}
```

You can use the `--graphical` (`-g`) flag for ASCII art:

```commandline
$ python demo.py --notes C3,G3,E4,Bb4 --top_n 3 --graphical
Here are the top 3 guitar positions for the chord: C3,G3,E4,Bb4

e x|---|---|---|---|
B  |---|---|---|-@-|
G  |---|-@-|---|---|
D x|---|---|---|---|
A  |---|---|-@-|---|
E  |-@-|---|---|---|
  8fr

e o|---|---|---|---|
B  |---|---|---|-@-|
G x|---|---|---|---|
D x|---|---|---|---|
A  |---|---|-@-|---|
E  |-@-|---|---|---|
  8fr

e  |---|-@-|---|---|
B  |-@-|---|---|---|
G x|---|---|---|---|
D  |-@-|---|---|---|
A x|---|---|---|---|
E  |---|---|---|-@-|
  5fr

```

You can specify different tunings, numbers of frets, and a capo location:

```commandline
$ python demo.py -g \
    --notes C3,G3,E4,Bb4 \
    --top_n 2 \
    --tuning '{"D": "D2", "A": "A2", "d": "D3", "F#": "F#3", "a": "A3", "dd": "D4"}' \
    --capo 1
Here are the top 2 guitar positions for the chord: C3,G3,E4,Bb4 with a guitar tuned to: {'D': Eb2, 'A': Bb2, 'd': Eb3, 'F#': G3, 'a': Bb3, 'dd': Eb4}

dd  |-@-|---|---|
 a x|---|---|---|
F#  |---|---|-@-|
 d x|---|---|---|
 A  |---|---|-@-|
 D  |---|---|-@-|
   6fr

dd x|---|---|---|---|
 a  |---|---|---|-@-|
F#  |-@-|---|---|---|
 d x|---|---|---|---|
 A  |-@-|---|---|---|
 D  |-@-|---|---|---|
   8fr

```

## Web App

This includes a Flask web app to run a server that will accept user requests and display the chord positions.

Run the app with `python app.py`. The main landing page looks like this:

![web app](images/web_app_sample.png "Web App")

## Environment

To generate a compatible environment with required dependencies, you can use conda:

```commandline
conda env create --file environment.yml
conda activate music
```
