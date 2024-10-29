# `music`

Helpers for music.

## Installation

You can install `music` from GitHub, e.g. with `pip` or `uv`:

```commandline
# Basic install
uv add git+ssh://git@github.com/joeplattenburg/music.git
# To add optional dependencies
uv add 'music[media] @ git+ssh://git@github.com/joeplattenburg/music.git'
# To specify a particular version / release
uv add git+ssh://git@github.com/joeplattenburg/music.git@vx.y.z
```

## `music` Package

Classes include:
- `Note`: define a music note, e.g.: `Note(name='C#', octave=3)`; methods:
  - `guitar_positions`: returns all positions the note can be played for a `Guitar`
  - also includes some helpers like `nearest_above` and `nearest_below`
  - notes can be added (semitones) and compared to other notes
- `Chord`: constructed from a `list[Note]`; methods:
  - `guitar_positions`: returns all positions the chord can be played for a `Guitar`
- `ChordName`: constructed from a string (e.g., `ChordName('C7b9/E')`); methods:
  - `get_all_chords` returns all possible voicings for a chord that fit between a `lower` and `upper` `Note`
- `ChordProgression`: constructed from a `list[ChordName]`; methods
  - `optimal_voice_leading`: compute optimal chord voicings 
  - `optimal_guitar_positions`: compute optimal guitar fingering positions
- `Staff`: constructed from a `list[Chord]`, used to generate a png image 
- `Guitar`: define a guitar by its tuning and number of frets (can include a capo)
- `GuitarPosition`: the set of fret positions to be played for each string

## CLI

When you install the `music` package, it includes a CLI entrypoint: `music-cli`.
See `--help` for more info on the args.

### `guitar-positions` Subcommand

Compute the fingering positions for a chord.

#### `notes` Mode

In `notes` mode, you must specify the notes (including octave) that you want as a comma-separated string:

```commandline
$ music-cli guitar-positions --notes C3,G3,E4,Bb4 -n 3
You input the chord: C3,G3,E4,Bb4
There are 1 playable voicings and 7 guitar positions (out of 54 possible) for a guitar tuned to standard.
Here are the top 3:
{'E': 8, 'A': 10, 'G': 9, 'B': 11}
{'E': 8, 'D': 5, 'B': 5, 'e': 6}
{'A': 3, 'D': 5, 'B': 5, 'e': 6}
(Computed in 0.00 seconds)
```

#### `name` Mode

In `name` mode, you can just pass a chord name (e.g., `Cmaj7#11/E`)

```commandline
$ music-cli guitar-positions --name Cmaj7#11/E -n 3
You input the chord: Cmaj7#11/E
There are 4 playable voicings and 8 guitar positions (out of 986 possible) for a guitar tuned to standard.
Here are the top 3:
{'E': 0, 'A': 10, 'D': 10, 'G': 11, 'B': 0}
{'E': 0, 'A': 2, 'G': 0, 'B': 1, 'e': 2}
{'E': 0, 'A': 3, 'G': 0, 'B': 0, 'e': 2}
(Computed in 0.04 seconds)
```

#### Other features

You can use the `--graphical` (`-g`) flag for ASCII art:

```commandline
$ music-cli guitar-positions --notes C3,G3,E4,Bb4 -n 3 --graphical 
You input the chord: C3,G3,E4,Bb4
There are 1 playable voicings and 7 guitar positions (out of 54 possible) for a guitar tuned to standard.
Here are the top 3:

e x|---|---|---|---|
B  |---|---|---|-@-|
G  |---|-@-|---|---|
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

e  |---|---|---|-@-|
B  |---|---|-@-|---|
G x|---|---|---|---|
D  |---|---|-@-|---|
A  |-@-|---|---|---|
E x|---|---|---|---|
    3fr
(Computed in 0.00 seconds)

```

You can specify different tunings, numbers of frets, and a capo location:

```commandline
$ music-cli guitar-positions -g \
    --notes C3,G3,E4,Bb4 \
    --top-n 2 \
    --tuning '{"D": "D2", "A": "A2", "d": "D3", "F#": "F#3", "a": "A3", "dd": "D4"}' \
    --capo 1
You input the chord: C3,G3,E4,Bb4
There are 1 playable voicings and 4 guitar positions (out of 54 possible) for a guitar tuned to custom ({'D': Eb2, 'A': Bb2, 'd': Eb3, 'F#': G3, 'a': Bb3, 'dd': Eb4}):.
Here are the top 2:

dd  |-@-|---|---|
 a x|---|---|---|
F#  |---|---|-@-|
 d x|---|---|---|
 A  |---|---|-@-|
 D  |---|---|-@-|
     7fr

dd x|---|---|---|---|
 a  |---|---|---|-@-|
F#  |-@-|---|---|---|
 d x|---|---|---|---|
 A  |-@-|---|---|---|
 D  |-@-|---|---|---|
     9fr
(Computed in 0.00 seconds)
```

### `voice-leading` Subcommand

Compute the optimal voicings for a chord progression.

```commandline
$ music-cli voice-leading --chords Dm7 G7 CM7
You input the chord progresssion: ['Dm7', 'G7', 'CM7']
The optimal voicing for this progression is:
Dm7: D2,C3,F3,A3
G7: G2,D3,F3,B3
CM7: C3,E3,G3,B3
(Computed in 0.03 seconds)
```

### `guitar-chord-progression` Subcommand

Compute the optimal guitar positions for a chord progression.

```commandline
$ music-cli guitar-chord-progression --chords Dm7 G7 CM7 -g
You input the chord progression: ['Dm7', 'G7', 'CM7']
The optimal positions for this progression are:
Dm7
e  |-@-|---|
B  |-@-|---|
G  |---|-@-|
D o|---|---|
A x|---|---|
E x|---|---|
    1fr
G7
e  |-@-|---|---|
B o|---|---|---|
G x|---|---|---|
D o|---|---|---|
A x|---|---|---|
E  |---|---|-@-|
    1fr
CM7
e o|---|
B o|---|
G o|---|
D x|---|
A  |-@-|
E x|---|
    3fr
(Computed in 0.13 seconds)
```

## Web App

This includes a Flask web app to run a server that will accept user requests and display the chord positions.

Run the app with `music-app [--port <port-num>]`. The main landing page looks like this:

![web app](images/web_app_sample.png "Web App")

## Development Environment

To generate a compatible environment with required dependencies, you can use `uv` 
(see instructions [here](https://docs.astral.sh/uv/getting-started/installation/) for installation):

```commandline
uv sync --frozen --extra media
```

The above CLI entrypoints will be available as scripts in the `.venv/bin/` directory.

To deploy on Raspberry Pi, it is highly recommended to use `--extra-index-url https://www.piwheels.org/simple` 
when syncing the environment, and to change the `.python-version` to match the system version 
(since PiWheels typically only builds wheels for the sys python version that comes with a given Linux version).

## Dependency Graph

The classes in the `music` project have an interrelationship as defined below, 
where the keys are classes and the values are classes they depend upon.
A longer term goal will be to eliminate circular dependencies from the module.  

```
{
    Note: [Guitar, GuitarPosition],
    Chord: [Note, Guitar, GuitarPosition],
    ChordName: [Note, Chord, Guitar],
    Staff: [Note, Chord],
    Guitar: [Note, Chord],
    GuitarPosition: [Guitar, Note, Chord]
}
```

## TODO

- [x] Add upper extensions
- [x] Add playability heuristics
- [x] Better ranking
- [x] Automated testing
- [x] Allow repeated notes
- [x] Option to remove redundant positions
- [X] Clean up app url
- [x] Optimize compute
- [x] Rename module (`music`?)
- [x] Show voicings on staff
- [x] Add audio
- [x] Voice leading
- [x] Optimal guitar chords
- [ ] Add more guitar options for chord progression
- [ ] Sort on different metrics
- [ ] Better input for specifying tuning
- [ ] Remove circular dependencies
- [ ] Which fingers to use
- [ ] Improve cost function for position movement
- [ ] Deploy on AWS
- [ ] Request logging
