#! /usr/bin/python
from copy import deepcopy
from functools import total_ordering
from itertools import permutations, product, combinations
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

    def __repr__(self) -> str:
        return str(self.simple_name + self.modifier + str(self.octave))

    def __eq__(self, other: 'Note') -> bool:
        return self.semitones == other.semitones

    def __lt__(self, other: 'Note') -> bool:
        return self.semitones < other.semitones

    def __add__(self, other) -> 'Note':
        return self.add_semitones(other.semitones)

    def __sub__(self, other) -> int:
        return self.semitones - other.semitones


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

    @staticmethod
    def from_string(string: str) -> 'Chord':
        return Chord([Note.from_string(n) for n in string.split(',')])

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
        'maj': [0, 4, 7],
        'm': [0, 3, 7],
        'min': [0, 3, 7],
        'dim': [0, 3, 6],
        'aug': [0, 4, 8],
        'sus2': [0, 2, 7],
        'sus4': [0, 5, 7],
        'maj7': [0, 4, 7, 11],
        'M7': [0, 4, 7, 11],
        '7': [0, 4, 7, 10],
        'min7': [0, 3, 7, 10],
        'm7': [0, 3, 7, 10],
        'm7b5': [0, 3, 6, 10],
        'dim7': [0, 3, 6, 9],
        'aug7': [0, 4, 8, 10],
        '6': [0, 4, 7, 9],
    }
    DEGREE_SEMITONE_MAPPER = {
        1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11
    }
    EXTENSION_SEMITONE_MAPPER = {
        str((deg - 1) + 8): semitones + 12
        for deg, semitones in DEGREE_SEMITONE_MAPPER.items()
    }
    EXTENSION_SEMITONE_MAPPER = {
        mod + ext: semis + mod_semis
        for ext, semis in EXTENSION_SEMITONE_MAPPER.items()
        for mod, mod_semis in Note.MODIFIER_MAPPER.items()
    }
    FLAT_KEYS = ['C', 'F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Cb', 'Fb', 'Bbb', 'Ebb', 'Abb', 'Dbb']
    SHARP_KEYS = ['G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#', 'D#', 'A#', 'E#', 'B#', 'F##']
    KEY_BIAS = {
        **{k: 'b' for k in FLAT_KEYS},
        **{k: '#' for k in SHARP_KEYS},
    }

    def __init__(self, chord_name: str):
        self.chord_note, self.quality, self.extensions, self.root = self.parse_name(chord_name)
        self.chord_name = chord_name
        self.note_names: list[str] = [
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
        self.extension_names = []
        for ext in self.extensions:
            bias = ext[0] if len(ext) > 1 else 'b'
            self.extension_names.append(
                Note(self.chord_note, octave=1).add_semitones(
                    self.EXTENSION_SEMITONE_MAPPER[ext], bias=bias
                ).name
            )

    def parse_name(self, name: str) -> tuple[str, str, list[str], str]:
        chord_note = best_match(name, Note.ALL_NOTES_NAMES)
        if '/' in name:
            remainder, root = name.split('/')
        else:
            remainder = name
            root = chord_note
        remainder = remainder.replace(chord_note, '')
        quality = best_match(remainder, list(self.QUALITY_SEMITONE_MAPPER.keys()))
        remainder = remainder.replace(quality, '')
        extensions = []
        while remainder:
            extensions.append(best_match(remainder, list(self.EXTENSION_SEMITONE_MAPPER.keys())))
            remainder = remainder.replace(extensions[-1], '')
        assert not remainder
        return chord_note, quality, extensions, root

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
        for note_ind, note_name in enumerate(self.note_names):
            semitones_to_add = raise_octave.get(note_ind, 0) * 12
            notes.append(lower.nearest_above(note_name).add_semitones(semitones_to_add))
            lower = notes[0]  # each subsequent note must be above root
        upper_chord = max(notes)  # extensions must be above chord
        for note_ind_rel, note_name in enumerate(self.extension_names):
            note_ind = note_ind_rel + len(self.note_names)
            semitones_to_add = raise_octave.get(note_ind, 0) * 12
            notes.append(upper_chord.nearest_above(note_name).add_semitones(semitones_to_add))
        return Chord(notes)

    def get_all_chords(
            self, *, lower: 'Note' = Note('C', 0), upper: 'Note',
            allow_repeats: bool = False, max_notes: Optional[int] = None
    ) -> list['Chord']:
        """
        For a chord name, return all `Chord`s that can fit between `lower` and `upper`;
        If `allow_repeats`, chord notes (but not extensions) can be repeated
        E.g., a G (G, B, D) could also be (G, B, D, G, D)
        """

        def _is_valid(notes: list[Note]) -> bool:
            return (
                # All notes must fit between upper and lower
                all(lower <= note <= upper for note in notes) and
                # Root should be the lowest note (this should never be false based on `get_chord` definition)
                all(notes[0] <= other for other in notes[1:])
            )
        max_octaves = (upper - lower) // 12
        chord_list = []
        if allow_repeats:
            note_sets = []
            available_strings = max_notes - len(self.note_names + self.extension_names)
            for repeat in range(available_strings + 1):
                new_note_sets = [self.note_names + list(add) for add in combinations(self.note_names, r=repeat)]
                note_sets += new_note_sets
            for note_set in note_sets:
                mod_self = deepcopy(self)
                mod_self.note_names = note_set
                possible_raises = [
                    dict(zip(range(len(mod_self.note_names) + len(mod_self.extension_names)), combination))
                    for combination in
                    product(range(max_octaves + 1), repeat=len(mod_self.note_names) + len(mod_self.extension_names))
                ]
                for raise_octave in possible_raises:
                    test_chord = mod_self.get_chord(lower=lower, raise_octave=raise_octave)
                    if _is_valid(test_chord.notes):
                        chord_list.append(test_chord)
        else:
            # This is a list of dicts containing all the possible raise_octave combinations that might work
            # There are actually a lot of invalid ones but those get handled by _is_valid
            possible_raises = [
                dict(zip(range(len(self.note_names) + len(self.extension_names)), combination))
                for combination in product(range(max_octaves + 1), repeat=len(self.note_names) + len(self.extension_names))
            ]
            for raise_octave in possible_raises:
                test_chord = self.get_chord(lower=lower, raise_octave=raise_octave)
                if _is_valid(test_chord.notes):
                    chord_list.append(test_chord)
        # remove duplicates
        chord_list = [Chord.from_string(s) for s in set(str(chord) for chord in chord_list)]
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
            self.fret_span = highest_fret - self.lowest_fret + 1
        # Sort the position in order of the guitar strings
        self.positions_dict = {
            string: positions[string]
            for string in self.guitar.string_names
            if string in positions
        }
        self.open_strings = [string for string, position in self.positions_dict.items() if position == 0]
        self.muted_strings = [string for string in self.guitar.string_names if string not in self.positions_dict]
        self.fretted_strings = [string for string, position in self.positions_dict.items() if position > 0]
        self.max_interior_gap = self._max_interior_gap()
        self.playable = self.is_playable()
        self.barre = (
            self.playable and len(self.fretted_strings) > 4 and
            sum(fret == self.lowest_fret for fret in self.positions_dict.values()) > 1
        )
        # If all fretted notes are >= fret 12, this is a redundant position
        # there is an identical shape 12 frets below that gives (nearly) the same voicing
        self.redundant = all(fret >= 12 for fret in self.positions_dict.values() if fret != 0)

    def _max_interior_gap(self) -> int:
        if len(self.positions_dict) == 0:
            return 0
        lowest_fretted_string = list(self.positions_dict.keys())[0]
        highest_fretted_string = list(self.positions_dict.keys())[-1]
        gap = 0
        max_gap = 0
        for i in range(
                self.guitar.string_names.index(lowest_fretted_string),
                self.guitar.string_names.index(highest_fretted_string)
        ):
            if self.positions_dict.get(self.guitar.string_names[i], 0) == 0:
                gap += 1
            else:
                gap = 0
            max_gap = max(max_gap, gap)
        return max_gap

    def is_playable(self) -> bool:
        if self.fret_span is None:
            return False
        # Too wide
        if self.fret_span > 5:
            return False
        n_notes = len([val for val in self.positions_dict.values() if val > 0])
        n_frets = len(set(self.positions_dict.values()))
        # Can always play 4 fretted notes
        if n_notes <= 4:
            return True
        # Can always play a 5th note with thumb on bottom string
        if n_notes == 5 and self.positions_dict.get(self.guitar.string_names[0], 0) > 0:
            return True
        # Otherwise, cannot be on more than 4 frets (at least some notes must be barred)
        if n_frets > 4:
            return False
        # Cannot have more than 3 fretted notes above barred
        if sum(fret > self.lowest_fret for fret in self.positions_dict.values()) > 3:
            return False
        if sum(fret == self.lowest_fret for fret in self.positions_dict.values()) == 1:
            return False
        else:
            return True

    def __eq__(self, other: 'GuitarPosition') -> bool:
        return self.positions_dict == other.positions_dict

    def __repr__(self) -> str:
        return str(self.positions_dict)

    def is_subset(self, other: 'GuitarPosition') -> bool:
        return (
            (self.positions_dict.keys() <= other.positions_dict.keys()) and
            all(self_val == other.positions_dict[key] for key, self_val in self.positions_dict.items())
        )

    def printable(self) -> list[str]:
        """
        Given a chord position, return ASCII art for the position; each line is an item of the list
        (e.g., you can `print('\n'.join(position.printable()))`)
        """
        rows = []
        widest_name = max(len(str(string)) for string in self.guitar.string_names)
        for string in reversed(self.guitar.string_names):
            left_padding = ' ' * (widest_name - len(str(string)))
            frets = ['---'] * self.fret_span
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


def sort_guitar_positions(p: list[GuitarPosition], target_fret: int = 7) -> list[GuitarPosition]:
    return sorted(p, key=lambda x: (
        # Sort first on fret span
        x.fret_span,
        # Then, fewest interior gaps
        x.max_interior_gap,
        # Then nearest to target fret
        abs(x.lowest_fret - target_fret),
    ))


def filter_subset_guitar_positions(p: list[GuitarPosition]) -> list[GuitarPosition]:
    """
    Drop any positions that are subsets of another position,
    e.g. given [{"E": 3, "A": 2}, {"E": 3}], drop the last element
    """
    ps = sorted(p, key=lambda x: len(x.positions_dict), reverse=True)
    out: list[GuitarPosition] = []
    for test_pos in ps:
        if not any(test_pos.is_subset(selected_pos) for selected_pos in out):
            out.append(test_pos)
    return out


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
        self.tuning_name = 'standard' if self.tuning == self.STANDARD_TUNING else 'custom'
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


def _rotate_list(list_: list[Any], n: int) -> list[Any]:
    if n >= len(list_):
        raise ValueError
    return list_[n:] + list_[:n]


def best_match(s: str, choices: list[str]) -> str:
    matches = []
    for choice in choices:
        if s.startswith(choice):
            matches.append(choice)
    try:
        return max(matches, key=len)
    except ValueError:
        raise ValueError(f'Invalid Input: {s} did not match any of {choices}!')
