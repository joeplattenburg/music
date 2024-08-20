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

There is a `demo.py` script that will generate guitar chord positions. See `--help` for more info on the args.

### `notes` Mode

In `notes` mode, you must specify the notes (including octave) that you want as a comma-separated string:

```commandline
$ python demo.py --notes C3,G3,E4,Bb4 -n 3
You input the chord: C3,G3,E4,Bb4
There are 9 playable guitar positions (out of 54 possible) for a guitar tuned to standard.
Here are the top 3:
{'E': 8, 'A': 10, 'G': 9, 'B': 11}
{'E': 8, 'A': 10, 'B': 11, 'e': 0}
{'E': 8, 'G': 0, 'B': 11, 'e': 0}
```

### `name` Mode

In `name` mode, you can just pass a chord name (e.g., `Cmaj7#11/E`)

```commandline
$ python demo.py --name Cmaj7/E   
You input the chord: Cmaj7#11/E
There are 48 playable guitar positions (out of 986 possible) for a guitar tuned to standard.
Here are the top 3:
{'E': 0, 'A': 10, 'D': 10, 'G': 11, 'B': 0}
{'E': 0, 'A': 3, 'G': 0, 'B': 0, 'e': 2}
{'E': 0, 'A': 2, 'G': 0, 'B': 1, 'e': 2}
```

### Other features

You can use the `--graphical` (`-g`) flag for ASCII art:

```commandline
$ python demo.py --notes C3,G3,E4,Bb4 --top_n 3 --graphical
You input the chord: C3,G3,E4,Bb4
There are 9 playable guitar positions (out of 54 possible) for a guitar tuned to standard.
Here are the top 3:

e x|---|---|---|---|
B  |---|---|---|-@-|
G  |---|-@-|---|---|
D x|---|---|---|---|
A  |---|---|-@-|---|
E  |-@-|---|---|---|
  7fr

e o|---|---|---|---|
B  |---|---|---|-@-|
G x|---|---|---|---|
D x|---|---|---|---|
A  |---|---|-@-|---|
E  |-@-|---|---|---|
  7fr

e o|---|---|---|---|
B  |---|---|---|-@-|
G o|---|---|---|---|
D x|---|---|---|---|
A x|---|---|---|---|
E  |-@-|---|---|---|
  7fr
```

You can specify different tunings, numbers of frets, and a capo location:

```commandline
$ python demo.py -g \
    --notes C3,G3,E4,Bb4 \
    --top_n 2 \
    --tuning '{"D": "D2", "A": "A2", "d": "D3", "F#": "F#3", "a": "A3", "dd": "D4"}' \
    --capo 1
You input the chord: C3,G3,E4,Bb4
There are 6 playable guitar positions (out of 54 possible) for a guitar tuned to custom ({'D': Eb2, 'A': Bb2, 'd': Eb3, 'F#': G3, 'a': Bb3, 'dd': Eb4}):.
Here are the top 2:

dd  |-@-|---|---|
 a x|---|---|---|
F#  |---|---|-@-|
 d x|---|---|---|
 A  |---|---|-@-|
 D  |---|---|-@-|
   6fr

dd  |---|-@-|---|---|
 a  |-@-|---|---|---|
F# x|---|---|---|---|
 d x|---|---|---|---|
 A  |---|---|---|-@-|
 D  |---|---|---|-@-|
   5fr
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

## TODO

- [x] Add upper extensions
- [x] Add playability heuristics
- [x] Better ranking
- [x] Allow repeated notes
- [x] Option to remove redundant positions
- [ ] Clean up app url
- [ ] Show voicings on staff
- [ ] Better GUI
  - [ ] Sort on different metrics
  - [ ] Better input for specifying tuning
- [ ] Automated testing
- [ ] Deploy on AWS
- [ ] Request logging?
