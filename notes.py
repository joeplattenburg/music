#! /usr/bin/python
import itertools
from functools import total_ordering
from itertools import combinations


@total_ordering
class Note:
    def __init__(self, name: str, octave: int):
        self.name_simple, self.modifier = self.parse_name(name)
        self.octave = octave
        self.semitones = (
                12 * self.octave +
                SEMITONE_MAPPER[self.name_simple] +
                MODIFIER_MAPPER.get(self.modifier, 0)
        )

    def parse_name(self, name: str) -> tuple[str, str]:
        assert len(name) <= 3
        simple_name = name[0].upper()
        assert simple_name in SEMITONE_MAPPER.keys()
        if len(name) > 1:
            modifier = name[1:]
            assert modifier in MODIFIER_MAPPER.keys()
        else:
            modifier = ''
        return simple_name, modifier

    def guitar_positions(self, valid_only: bool = True) -> dict[str, int]:
        return {
            string: self.semitones - note.semitones
            for string, note in TUNING.items()
            if (valid_only and self >= note and (self.semitones - note.semitones) <= 22)
            or not valid_only
        }

    def __repr__(self):
        return self.name_simple + self.modifier + str(self.octave)

    def __eq__(self, other: 'Note'):
        return self.semitones == other.semitones

    def __lt__(self, other: 'Note'):
        return self.semitones < other.semitones


class Chord:
    def __init__(self, notes: list[Note]):
        self.notes = sorted(notes)

    def guitar_positions(self) -> list[dict[str, int]]:
        string_names = list(TUNING.keys())
        all_positions = [
            list(note.guitar_positions(valid_only=False).values())
            for note in self.notes
        ]
        valid_combinations = combinations(range(len(TUNING)), len(self.notes))
        valid_positions: list[tuple[dict[str, int], int]] = []
        for comb in valid_combinations:
            test_position = {
                string_names[string]: all_positions[note][string]
                for note, string in enumerate(comb)
            }
            if all(0 <= fret <= N_FRETS for fret in test_position.values()):
                # Don't penalize open strings
                lowest_fret = min(f for f in test_position.values() if f != 0)
                highest_fret = max(test_position.values())
                fret_span = highest_fret - lowest_fret
                valid_positions.append((test_position, fret_span))
        return [p for p, _ in sorted(valid_positions, key=lambda x: x[1])]

    def __repr__(self):
        return ','.join(str(n) for n in self.notes)


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
}

N_FRETS = 22

TUNING: dict[str, 'Note'] = {
    'E': Note('E', 2),
    'A': Note('A', 2),
    'D': Note('D', 3),
    'G': Note('G', 3),
    'B': Note('B', 3),
    'e': Note('E', 4),
}
