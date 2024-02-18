# `music`

Helpers for music.

## `notes` Module

Classes include:
- `Note`: define a music note, e.g.: `Note(name='C#', octave=3)`
  - `guitar_positions`: returns all positions the note can be played
- `Chord`: constructed from a `list[Note]`; methods
  - `guitar_positions`: returns all positions the chord can be played

Run the demo:

```commandline
$ python demo.py

Here's a demo!
Get the guitar positions for for the C7 chord: C3,G3,E4,Bb4
(In order of lowest to highest fret span)
{'E': 8, 'A': 10, 'G': 9, 'B': 11}
{'E': 8, 'A': 10, 'B': 11, 'e': 0}
{'E': 8, 'D': 5, 'B': 5, 'e': 6}
{'E': 8, 'G': 0, 'B': 5, 'e': 6}
{'E': 8, 'G': 0, 'B': 11, 'e': 0}
{'A': 3, 'D': 5, 'B': 5, 'e': 6}
{'A': 3, 'G': 0, 'B': 5, 'e': 6}
{'E': 8, 'A': 10, 'G': 9, 'e': 6}
{'E': 8, 'D': 5, 'G': 9, 'e': 6}
{'E': 8, 'A': 10, 'B': 5, 'e': 6}
{'E': 8, 'A': 10, 'D': 14, 'B': 11}
{'E': 8, 'D': 5, 'G': 9, 'B': 11}
{'E': 8, 'D': 5, 'B': 11, 'e': 0}
{'E': 8, 'D': 14, 'G': 0, 'B': 11}
{'A': 3, 'D': 5, 'G': 9, 'e': 6}
{'E': 8, 'A': 10, 'D': 14, 'G': 15}
{'E': 8, 'A': 10, 'G': 15, 'e': 0}
{'E': 8, 'A': 10, 'D': 14, 'e': 6}
{'E': 8, 'D': 14, 'G': 0, 'e': 6}
{'A': 3, 'D': 5, 'G': 9, 'B': 11}
{'A': 3, 'D': 5, 'B': 11, 'e': 0}
{'A': 3, 'G': 0, 'B': 11, 'e': 0}
{'E': 8, 'A': 10, 'G': 15, 'B': 5}
{'E': 8, 'D': 5, 'G': 15, 'B': 5}
{'E': 8, 'D': 5, 'G': 15, 'e': 0}
{'E': 8, 'A': 19, 'G': 0, 'B': 11}
{'A': 3, 'D': 14, 'G': 0, 'B': 11}
{'A': 3, 'D': 14, 'G': 0, 'e': 6}
{'E': 8, 'A': 10, 'D': 20, 'G': 9}
{'E': 8, 'A': 10, 'D': 20, 'e': 0}
{'E': 8, 'A': 19, 'D': 20, 'G': 0}
{'E': 8, 'D': 20, 'G': 0, 'e': 0}
{'E': 15, 'A': 3, 'D': 14, 'G': 15}
{'E': 15, 'A': 3, 'D': 14, 'B': 11}
{'E': 15, 'A': 3, 'D': 14, 'e': 6}
{'E': 15, 'A': 3, 'G': 9, 'B': 11}
{'E': 15, 'A': 3, 'G': 9, 'e': 6}
{'E': 15, 'A': 3, 'G': 15, 'B': 5}
{'E': 15, 'A': 3, 'B': 5, 'e': 6}
{'E': 15, 'A': 3, 'G': 15, 'e': 0}
{'E': 15, 'A': 3, 'B': 11, 'e': 0}
{'A': 3, 'D': 5, 'G': 15, 'B': 5}
{'A': 3, 'D': 5, 'G': 15, 'e': 0}
{'E': 8, 'A': 19, 'G': 0, 'e': 6}
{'E': 8, 'A': 19, 'D': 5, 'G': 15}
{'E': 8, 'A': 19, 'D': 5, 'B': 11}
{'E': 8, 'A': 19, 'D': 5, 'e': 6}
{'E': 8, 'A': 10, 'D': 20, 'B': 5}
{'E': 8, 'D': 20, 'G': 0, 'B': 5}
{'E': 15, 'A': 3, 'D': 20, 'G': 9}
{'E': 15, 'A': 3, 'D': 20, 'B': 5}
{'E': 15, 'A': 3, 'D': 20, 'e': 0}
{'A': 3, 'D': 20, 'G': 0, 'B': 5}
{'A': 3, 'D': 20, 'G': 0, 'e': 0}
```