#! /usr/bin/python
from functools import total_ordering
from itertools import permutations, product
import json
from typing import Hashable, Optional, Any, Literal

@total_ordering
class Note:

    SEMITONE_MAPPER: dict[str, int] = {
        'C': 0,
        'D': 2,
        'E': 4,
        'F': 5,
        'G': 7,
        'A': 9,
        'B': 11
    }

    MODIFIER_MAPPER: dict[str, int] = {
        'bb': -2,
        'b': -1,
        '': 0,
        '#': 1,
        '##': 2,
        's': 1,
        'ss': 2,
    }

    ALL_NOTES_NAMES: list[str] = [
        name + mod for name, mod in product(SEMITONE_MAPPER.keys(), MODIFIER_MAPPER.keys())
    ]

    def __init__(self, name: str, octave: int):
        self.simple_name, self.modifier = self.parse_name(name)
        self.name = name
        self.octave = octave
        self.semitones = (
                12 * self.octave +
                self.SEMITONE_MAPPER[self.simple_name] +
                self.MODIFIER_MAPPER[self.modifier]
        )

    def parse_name(self, name: str) -> tuple[str, str]:
        assert len(name) <= 3
        simple_name = name[0].upper()
        assert simple_name in self.SEMITONE_MAPPER.keys()
        if len(name) > 1:
            modifier = name[1:]
            assert modifier in self.MODIFIER_MAPPER.keys()
        else:
            modifier = ''
        return simple_name, modifier

    def guitar_positions(self, guitar: 'Guitar' = None, valid_only: bool = True) -> 'GuitarPosition':
        guitar = guitar or Guitar()
        positions = {
            string: self.semitones - note.semitones
            for string, note in guitar.tuning.items()
            if (valid_only and self >= note and (self.semitones - note.semitones) <= guitar.frets)
            or not valid_only
        }
        return GuitarPosition(positions, guitar=guitar)

    @staticmethod
    def from_semitones(semitones: int, bias: Literal['b', '#'] = 'b') -> 'Note':
        octave = semitones // 12
        remainder = semitones % 12
        if remainder not in Note.SEMITONE_MAPPER.values():
            modifier = bias
            remainder = remainder + 1 if bias == 'b' else remainder - 1
        else:
            modifier = ''
        inverse_mapper = {v: k for k, v in Note.SEMITONE_MAPPER.items()}
        name = inverse_mapper[remainder] + modifier
        return Note(name=name, octave=octave)

    @staticmethod
    def from_string(note: str) -> 'Note':
        return Note(note[:-1], int(note[-1]))

    def add_semitones(self, semitones: int, bias: Literal['b', '#'] = 'b') -> 'Note':
        return self.from_semitones(self.semitones + semitones, bias)

    def same_name(self, other: 'Note') -> bool:
        return self.semitones % 12 == other.semitones % 12

    def nearest_above(self, note: str, allow_equal: bool = True) -> 'Note':
        interval = (Note(note, 0).semitones - self.semitones) % 12
        if not allow_equal and interval == 0:
            interval = 12
        return self.add_semitones(interval)

    def nearest_below(self, note: str, allow_equal: bool = True) -> 'Note':
        interval = (self.semitones - Note(note, 0).semitones) % 12
        if not allow_equal and interval == 0:
            interval = 12
        return self.add_semitones(-interval)


    def __repr__(self):
        return str(self.simple_name + self.modifier + str(self.octave))

    def __eq__(self, other: 'Note'):
        return self.semitones == other.semitones

    def __lt__(self, other: 'Note'):
        return self.semitones < other.semitones


class Chord:
    def __init__(self, notes: list[Note]):
        self.notes = sorted(notes)

    def guitar_positions(self, guitar: 'Guitar' = None) -> list['GuitarPosition']:
        guitar = guitar or Guitar()
        # This is a list of lists
        # The outer list has the length of the number of notes in the chord
        # Each note has the length of the number of strings of the guitar,
        # corresponding to the fret positions that note can be played on that string
        all_positions = [
            list(note.guitar_positions(guitar=guitar, valid_only=False).positions_dict.values())
            for note in self.notes
        ]
        # This gives all the permutations (n_strings P n_notes) of where the notes can be played on the strings
        valid_combinations = permutations(range(len(guitar.tuning)), len(self.notes))
        valid_positions = []
        for comb in valid_combinations:
            positions_dict = {
                guitar.string_names[string]: all_positions[note][string]
                for note, string in enumerate(comb)
            }
            guitar_position = GuitarPosition(positions_dict, guitar=guitar)
            if guitar_position.valid:
                valid_positions.append(guitar_position)
        return sorted(valid_positions, key=lambda x: x.fret_span)

    def __repr__(self):
        return ','.join(str(n) for n in self.notes)

    def __eq__(self, other: 'Chord'):
        return (
            (len(self.notes) == len(other.notes)) and
            all(s == o for s, o in zip(self.notes, other.notes))
        )


class ChordName:

    QUALITY_SEMITONE_MAPPER = {
        '': [0, 4, 7],
        'm': [0, 3, 7],
        'dim': [0, 3, 6],
        'aug': [0, 4, 8],
        'maj7': [0, 4, 7, 11],
        '7': [0, 4, 7, 10],
        'm7': [0, 3, 7, 10],
        'm7b5': [0, 3, 6, 10],
        'dim7': [0, 3, 6, 9],
        'aug7': [0, 4, 8, 10],
    }
    FLAT_KEYS = ['C', 'F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Cb', 'Fb', 'Bbb', 'Ebb', 'Abb', 'Dbb']
    SHARP_KEYS = ['G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#', 'D#', 'A#', 'E#', 'B#', 'F##']
    KEY_BIAS = {
        **{k: 'b' for k in FLAT_KEYS},
        **{k: '#' for k in SHARP_KEYS},
    }

    def __init__(self, chord_name: str):
        chord_notes = []
        for note_name in Note.ALL_NOTES_NAMES:
            if chord_name.startswith(note_name):
                chord_notes.append(note_name)
        try:
            chord_note = max(chord_notes, key=len)
        except ValueError:
            raise ValueError(f'Invalid chord name; must start with one of {Note.ALL_NOTES_NAMES}')
        if '/' in chord_name:
            chord_name, root = chord_name.split('/')
        else:
            root = chord_note
        quality = chord_name.replace(chord_note, '')
        self.chord_note = chord_note
        self.root = root
        self.quality = quality
        self.note_names = [
            Note(self.chord_note, octave=0).add_semitones(s, bias=self.KEY_BIAS[self.chord_note]).name
            for s in self.QUALITY_SEMITONE_MAPPER[self.quality]
        ]
        root_index = None
        for ind, note in enumerate(self.note_names):
            if Note(note, 0).same_name(Note(self.root, 0)):
                root_index = ind
        if root_index is not None:
            self.note_names = _rotate_list(self.note_names, root_index)
        else:
            self.note_names.insert(0, self.root)

    def get_chord(
            self, *, lower: 'Note' = Note('C', 0), raise_octave: dict[int, int] = None
    ) -> 'Chord':
        """
        For a chord name, return a `Chord` in close position whose root is the lowest note >= `lower`;
        alternately, `raise_octave` can raise one or more of the chord tones by one or more octaves
        E.g., for notes [C, E, G], close position would be [C0, E0, G0]
        if we set raise_octave = {0: 1, 2: 2}, it would do the following:
          - raise the root (C) by one octave -> C1
          - raise the E to the nearest above -> E1
          - raise the G by two octaves above the nearest above -> G3
        """
        raise_octave = raise_octave or {}
        notes = []
        for chord_ind, note_name in enumerate(self.note_names):
            semitones_to_add = raise_octave.get(chord_ind, 0) * 12
            notes.append(lower.nearest_above(note_name).add_semitones(semitones_to_add))
            lower = notes[0]  # each subsequent note must be above root
        return Chord(notes)

    def get_all_chords(self, *, lower: 'Note' = Note('C', 0), upper: 'Note') -> list['Chord']:
        """
        For a chord name, return all `Chord`s that can fit between `lower` and `upper`
        """

        def _is_valid(notes: list[Note]) -> bool:
            return (
                all(lower <= note <= upper for note in notes) and
                (notes[0] < other for other in notes[1:])
            )

        chord_list = []
        root_valid = True
        raise_octave = {0: 0}
        while root_valid:
            test_chord = self.get_chord(lower=lower, raise_octave=raise_octave)
            if test_chord.notes[0] > upper:
                break
            if _is_valid(test_chord.notes):
                chord_list.append(test_chord)
            raise_octave[0] += 1
        return chord_list


class GuitarPosition:
    def __init__(self, positions: dict[Hashable, int], guitar: 'Guitar' = None):
        self.guitar = guitar or Guitar()
        self.valid = all(0 <= fret <= self.guitar.frets for fret in positions.values())
        if len(positions) == 0:
            self.lowest_fret = None
            self.fret_span = None
        else:
            self.lowest_fret = (
                0 if all(f == 0 for f in positions.values())
                else min(f for f in positions.values() if f != 0)
            )
            highest_fret = max(positions.values())
            self.fret_span = highest_fret - self.lowest_fret
        # Sort the position in order of the guitar strings
        self.positions_dict = {
            string: positions[string]
            for string in self.guitar.string_names
            if string in positions
        }

    def __repr__(self) -> str:
        return str(self.positions_dict)

    def printable(self) -> list[str]:
        """
        Given a chord position, return ASCII art for the position; each line is an item of the list
        (e.g., you can `print('\n'.join(position.printable()))`)
        """
        rows = []
        widest_name = max(len(str(string)) for string in self.guitar.string_names)
        for string in reversed(self.guitar.string_names):
            left_padding = ' ' * (widest_name - len(str(string)))
            frets = ['---'] * (self.fret_span + 1)
            fret = self.positions_dict.get(string, -1)
            if fret > 0:
                frets[fret - self.lowest_fret] = '-@-'
                ring_status = ' '
            else:
                ring_status = 'o' if fret == 0 else 'x'
            row = f'{left_padding}{string} {ring_status}|{"|".join(frets)}|'
            rows.append(row)
        if self.lowest_fret > 1:
            left_padding = ' ' * widest_name
            rows.append(f'{left_padding} {self.lowest_fret - 1}fr')
        return rows


class Guitar:
    STANDARD_TUNING: dict[str, 'Note'] = {
        'E': Note('E', 2),
        'A': Note('A', 2),
        'D': Note('D', 3),
        'G': Note('G', 3),
        'B': Note('B', 3),
        'e': Note('E', 4),
    }

    def __init__(self, tuning: dict[Hashable, 'Note'] = None, frets: int = 22, capo: int = 0):
        self.open_tuning = tuning or self.STANDARD_TUNING
        self.capo = capo
        self.tuning = {name: note.add_semitones(capo) for name, note in self.open_tuning.items()}
        self.string_names = list(self.tuning.keys())
        self.frets = frets - capo
        self.lowest = min(note for note in self.tuning.values())
        self.highest = max(note for note in self.tuning.values()).add_semitones(self.frets)

    def __repr__(self):
        return str(self.tuning)

    @staticmethod
    def parse_tuning(tuning: Optional[str] = None) -> dict[str, 'Note']:
        if not tuning:
            return Guitar.STANDARD_TUNING
        else:
            return {
                string: Note.from_string(note)
                for string, note in json.loads(tuning.replace("'", '"')).items()
            }


def _rotate_list(l: list[Any], n: int) -> list[Any]:
    if n >= len(l):
        raise ValueError
    return l[n:] + l[:n]
