#! /usr/bin/python
from functools import total_ordering
from itertools import permutations
from typing import Hashable

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
        '#': 1,
        '##': 2,
        's': 1,
        'ss': 2,
    }

    def __init__(self, name: str, octave: int):
        self.simple_name, self.modifier = self.parse_name(name)
        self.octave = octave
        self.semitones = (
                12 * self.octave +
                self.SEMITONE_MAPPER[self.simple_name] +
                self.MODIFIER_MAPPER.get(self.modifier, 0)
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
    def from_semitones(semitones: int) -> 'Note':
        octave = semitones // 12
        remainder = semitones % 12
        if remainder not in Note.SEMITONE_MAPPER.values():
            remainder += 1
            modifier = 'b'
        else:
            modifier = ''
        inverse_mapper = {v: k for k, v in Note.SEMITONE_MAPPER.items()}
        name = inverse_mapper[remainder] + modifier
        return Note(name=name, octave=octave)

    @staticmethod
    def from_string(note: str) -> 'Note':
        return Note(note[:-1], int(note[-1]))

    def add_semitones(self, semitones: int) -> 'Note':
        return self.from_semitones(self.semitones + semitones)

    def __repr__(self):
        return self.simple_name + self.modifier + str(self.octave)

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

    def print(self) -> str:
        rows = []
        for string in reversed(self.guitar.string_names):
            frets = ['---'] * (self.fret_span + 1)
            fret = self.positions_dict.get(string, -1)
            if fret > 0:
                frets[fret - self.lowest_fret] = '-@-'
                ring_status = ' '
            else:
                ring_status = 'o' if fret == 0 else 'x'
            row = f'{string} {ring_status}|{"|".join(frets)}|'
            rows.append(row)
        if self.lowest_fret > 1:
            rows.append(f'  {self.lowest_fret - 1}fr')
        return '\n'.join(rows)


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
        self.tuning = tuning or self.STANDARD_TUNING
        self.capo = capo
        self.tuning = {name: note.add_semitones(capo) for name, note in self.tuning.items()}
        self.string_names = list(self.tuning.keys())
        self.frets = frets - capo
