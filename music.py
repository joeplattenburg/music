#! /usr/bin/python
from functools import total_ordering, partial
from itertools import product, combinations_with_replacement, combinations, chain
import json
from multiprocessing import Pool
import os
from typing import Hashable, Optional, Any, Literal

DEFAULT_MAX_FRET_SPAN = 4


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
            string: self - note
            for string, note in guitar.tuning.items()
            if (valid_only and self >= note and (self - note) <= guitar.frets)
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
        interval = (Note(note, 0) - self) % 12
        if not allow_equal and interval == 0:
            interval = 12
        return self.add_semitones(interval)

    def nearest_below(self, note: str, allow_equal: bool = True) -> 'Note':
        interval = (self - Note(note, 0)) % 12
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

    def __hash__(self):
        return self.semitones


class Chord:
    def __init__(self, notes: list[Note]):
        self.notes = sorted(notes)
        self.num_total_guitar_positions = None
        self.num_playable_guitar_positions = None

    def guitar_positions(
            self,
            guitar: 'Guitar' = None,
            max_fret_span: int = 4,
            include_unplayable: bool = False,
            allow_thumb: bool = True
    ) -> list['GuitarPosition']:
        guitar = guitar or Guitar()
        # This is a dict of dicts, {note: {string: fret for string in guitar} for note in chord}
        # of all the positions each note can be played on each string
        all_fret_positions = {
            str(note): note.guitar_positions(guitar=guitar, valid_only=False).positions_dict
            for note in self.notes
        }
        # Get just the valid positions
        valid_strings = [
            list(note.guitar_positions(guitar=guitar, valid_only=True).positions_dict.keys())
            for note in self.notes
        ]
        valid_combinations = [comb for comb in product(*valid_strings) if len(set(comb)) == len(self.notes)]
        self.num_total_guitar_positions = len(valid_combinations)
        playable_positions = []
        for comb in valid_combinations:
            positions_dict = {
                string: all_fret_positions[str(note)][string]
                for note, string in zip(self.notes, comb)
            }
            guitar_position = GuitarPosition(positions_dict, guitar=guitar, max_fret_span=max_fret_span)
            assert guitar_position.valid  # This should be true from above
            if (guitar_position.playable and not guitar_position.redundant) or include_unplayable:
                if allow_thumb or (not allow_thumb and not guitar_position.use_thumb):
                    playable_positions.append(guitar_position)
        self.num_playable_guitar_positions = len(playable_positions)
        return sorted(playable_positions, key=lambda x: x.fret_span)

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

    def __hash__(self):
        return hash(tuple(note.semitones for note in self.notes))


class ChordName:

    QUALITY_SEMITONE_MAPPER = {
        '': [0, 4, 7],
        'maj': [0, 4, 7],
        'M': [0, 4, 7],
        'min': [0, 3, 7],
        'm': [0, 3, 7],
        'dim': [0, 3, 6],
        'aug': [0, 4, 8],
        'sus2': [0, 2, 7],
        'sus4': [0, 5, 7],
        'maj7': [0, 4, 7, 11],
        'M7': [0, 4, 7, 11],
        '7': [0, 4, 7, 10],
        'minmaj7': [0, 3, 7, 11],
        'mM7': [0, 3, 7, 11],
        'mmaj7': [0, 3, 7, 11],
        'minM7': [0, 3, 7, 11],
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
        if deg in (2, 4, 6)
    }
    EXTENSION_SEMITONE_MAPPER = {
        mod + ext: semis + mod_semis
        for ext, semis in EXTENSION_SEMITONE_MAPPER.items()
        for mod, mod_semis in Note.MODIFIER_MAPPER.items()
        if len(mod) <= 1
    }
    FLAT_KEYS = ['C', 'F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Cb', 'Fb', 'Bbb', 'Ebb', 'Abb', 'Dbb']
    SHARP_KEYS = ['G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#', 'D#', 'A#', 'E#', 'B#', 'F##']
    KEY_BIAS = {
        **{k: 'b' for k in FLAT_KEYS},
        **{k: '#' for k in SHARP_KEYS},
    }
    ALL_CHORD_NAMES = [
        f'{note}{quality}{ext}'
        for note, quality, ext in product(
            KEY_BIAS.keys(), QUALITY_SEMITONE_MAPPER.keys(), EXTENSION_SEMITONE_MAPPER.keys()
        )
    ]

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
            bias = ext[0] if ext[0] in ('#', 'b') else 'b'
            self.extension_names.append(
                Note(self.chord_note, octave=1).add_semitones(
                    self.EXTENSION_SEMITONE_MAPPER[ext], bias=bias
                ).name
            )

    def parse_name(self, name: str) -> tuple[str, str, list[str], str]:
        chord_note = best_match(name, list(self.KEY_BIAS.keys()))
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
            max_notes: Optional[int] = None,
            allow_repeats: bool = False,
            allow_identical: bool = False,
    ) -> list['Chord']:
        """
        For a chord name, return all `Chord`s that can fit between `lower` and `upper`;
        If `allow_repeats`, chord notes (but not extensions) can be repeated
        (and if allow_identical, repeats can be in the same octave)
        E.g., a G (G, B, D) could also be (G, B, D, G, D)
        """
        max_notes = max_notes or len(self.note_names) + len(self.extension_names)
        max_octaves = (upper - lower) // 12 + 1
        root_notes = [lower.nearest_above(self.root).add_semitones(12 * octave) for octave in range(max_octaves)]
        required_notes = set(Note(name, 0) for name in self.note_names[1:])
        possible_notes = [
            lower.nearest_above(note).add_semitones(12 * octave)
            for octave in range(max_octaves)
            for note in self.note_names
            if lower.nearest_above(note).add_semitones(12 * octave) <= upper
        ]
        possible_extensions = [
            lower.nearest_above(ext).add_semitones(12 * octave)
            for octave in range(1, max_octaves)
            for ext in self.extension_names
            if lower.nearest_above(ext).add_semitones(12 * octave) <= upper
        ]
        extensions = constrained_powerset(
            possible_extensions, max_len=len(self.extension_names), allow_repeats=False
        )
        chord_list = []
        for root_note, ext in product(root_notes, extensions):
            upper_ = min(ext) if ext else upper
            if allow_identical:
                note_list = filter(lambda x: root_note <= x <= upper_, possible_notes)
            elif allow_repeats:
                note_list = filter(lambda x: root_note < x <= upper_, possible_notes)
            else:
                note_list = filter(lambda x: (root_note < x <= upper_) and not x.same_name(root_note), possible_notes)
            available_notes = max_notes - 1 - len(ext)  # root and extensions are already taken
            mid_notes_list = constrained_powerset(
                list(note_list),
                required_notes=required_notes,
                max_len=available_notes,
                allow_repeats=allow_repeats,
                allow_identical=allow_identical
            )
            chord_list += [
                Chord([root_note, *mid_notes, *ext])
                for mid_notes in mid_notes_list
            ]
        return chord_list

    def get_all_guitar_chords(
            self, guitar: Optional['Guitar'] = None, allow_repeats: bool = False, allow_identical: bool = False
    ) -> list['Chord']:
        guitar = guitar or Guitar()
        return self.get_all_chords(
            lower=guitar.lowest, upper=guitar.highest, max_notes=len(guitar.string_names),
            allow_repeats=allow_repeats, allow_identical=allow_identical
        )


class GuitarPosition:

    def __init__(self, positions: dict[Hashable, int], guitar: 'Guitar' = None, max_fret_span: int = DEFAULT_MAX_FRET_SPAN):
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
        # Indices of open, muted, and fretted strings
        self.open_strings = [
            i for i, string in enumerate(self.guitar.string_names)
            if self.positions_dict.get(string, -1) == 0
        ]
        self.muted_strings = [
            i for i, string in enumerate(self.guitar.string_names)
            if self.positions_dict.get(string, -1) == -1
        ]
        self.fretted_strings = [
            i for i, string in enumerate(self.guitar.string_names)
            if self.positions_dict.get(string, -1) > 0
        ]
        lowest_fret_strings = [
            i for i, string in enumerate(self.guitar.string_names)
            if self.positions_dict.get(string, -1) == self.lowest_fret
        ]
        # Can play a 5th note with thumb on bottom string
        self.use_thumb = (
            (len(self.fretted_strings) == 5) and
            (self.positions_dict.get(self.guitar.string_names[0], -1) == self.lowest_fret)
        )
        self.max_interior_gap = self._max_interior_gap()
        self.playable = self.is_playable(max_fret_span=max_fret_span)
        # Barre chord needs
        self.barre = (
            self.playable and
            # more than 4 fretted strings
            len(self.fretted_strings) > 4 and
            # no open strings
            len(self.open_strings) == 0 and
            len(lowest_fret_strings) > 1 and
            not self.use_thumb and
            # No open or muted strings inside the barre position
            not any(
                min(lowest_fret_strings) < string < max(lowest_fret_strings)
                for string in self.muted_strings + self.open_strings
            )
        )
        if self.barre:
            # All strings along the barre position
            self.barred_strings_inds = list(range(min(lowest_fret_strings), max(lowest_fret_strings) + 1))
        else:
            self.barred_strings_inds = []
        # If all fretted notes are >= fret 12, this is a redundant position
        # there is an identical shape 12 frets below that gives (nearly) the same voicing
        self.redundant = all(fret >= 12 for fret in self.positions_dict.values() if fret != 0)

    def _max_interior_gap(self) -> int:
        if len(self.fretted_strings) == 0:
            return 0
        gap = 0
        max_gap = 0
        for i in range(self.fretted_strings[0], self.fretted_strings[-1]):
            if self.positions_dict.get(self.guitar.string_names[i], 0) == 0:
                gap += 1
            else:
                gap = 0
            max_gap = max(max_gap, gap)
        return max_gap

    def is_playable(self, max_fret_span: int = DEFAULT_MAX_FRET_SPAN) -> bool:
        if self.fret_span is None:
            return False
        # Too wide
        if self.fret_span > max_fret_span:
            return False
        n_notes = len(self.fretted_strings)
        n_frets = len(set(self.positions_dict.values()))
        # Can always play 4 fretted notes
        if n_notes <= 4:
            return True
        if self.use_thumb:
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
        for i, string in reversed(list(enumerate(self.guitar.string_names))):
            fret_marker = '-T-' if string == self.guitar.string_names[0] and self.use_thumb else '-@-'
            left_padding = ' ' * (widest_name - len(str(string)))
            frets = ['---'] * self.fret_span
            fret = self.positions_dict.get(string, -1)
            if fret > 0:
                frets[fret - self.lowest_fret] = fret_marker
                ring_status = ' '
            else:
                ring_status = 'o' if fret == 0 else 'x'
            if self.barre:
                if min(self.barred_strings_inds) < i < max(self.barred_strings_inds):
                    frets[0] = '-|-'
            row = f'{left_padding}{string} {ring_status}|{"|".join(frets)}|'
            rows.append(row)
        if self.lowest_fret > 0:
            left_padding = ' ' * widest_name
            rows.append(f'{left_padding}   {self.lowest_fret}fr')
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
    DEFAULT_FRETS = 22

    def __init__(self, tuning: dict[Hashable, 'Note'] = None, frets: int = DEFAULT_FRETS, capo: int = 0):
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
        raise ValueError(f'Invalid Input: {s} did not match any of {choices}')


def note_set(note_list: list[Note]) -> set[Note]:
    return set(Note(note.name, 0) for note in note_list)


def constrained_powerset(
        note_list: list[Note],
        max_len: int = 0,
        required_notes: set[Note] = None,
        allow_repeats: bool = True,
        allow_identical: bool = False
) -> list[list[Note]]:
    """
    Given a list a notes, return the powerset (list of lists of notes) such that:
    - the sets are <= max_len
    - the sets contain at least required_notes (same name, even if different octave)
    if allow_repeats, the same note name can appear multiple times (different octave)
    if allow_identical, it can appear multiple times (same octave)
    """
    max_len = max_len or len(note_list)
    required_notes = required_notes or note_set(note_list)
    func = combinations_with_replacement if allow_identical else combinations
    powerset = chain.from_iterable(func(note_list, r) for r in range(max_len + 1))
    if allow_repeats:
        subset = [s for s in powerset if note_set(s) >= required_notes]
    else:
        subset = [s for s in powerset if note_set(s) >= required_notes and len(note_set(s)) == len(s)]
    return subset


def get_all_guitar_positions_for_chord_name(
        chord_name: 'ChordName',
        guitar: 'Guitar',
        allow_repeats: bool,
        allow_identical: bool,
        max_fret_span: int = DEFAULT_MAX_FRET_SPAN,
        allow_thumb: bool = True,
        parallel: bool = False,
) -> list['GuitarPosition']:
    chords = chord_name.get_all_chords(
        lower=guitar.lowest, upper=guitar.highest, max_notes=len(guitar.tuning),
        allow_repeats=allow_repeats, allow_identical=allow_identical,
    )
    kwargs = {
        'guitar': guitar,
        'allow_thumb': allow_thumb,
        'max_fret_span': max_fret_span
    }
    if parallel:
        with Pool(os.cpu_count()) as p:
            nested = p.map(partial(_parallel_helper, **kwargs), chords)
        positions = [pos for poss in nested for pos in poss]
    else:
        positions = []
        for chord in chords:
            positions += chord.guitar_positions(include_unplayable=True, **kwargs)
    return positions


def _parallel_helper(chord: 'Chord', guitar: 'Guitar', allow_thumb: bool, max_fret_span: int):
    return chord.guitar_positions(
        guitar=guitar, include_unplayable=True,
        allow_thumb=allow_thumb, max_fret_span=max_fret_span
    )
