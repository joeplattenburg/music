#! /usr/bin/python
from functools import total_ordering, partial
from importlib import util as importlib_util
from itertools import product, combinations_with_replacement, combinations, chain
import json
from multiprocessing import Pool
import numpy as np
import os
from typing import Hashable, Optional, Any, Literal, Iterable
import warnings

from music import graph

MEDIA_PACKAGES = ['matplotlib', 'wave']
media_installed = all(importlib_util.find_spec(p) for p in MEDIA_PACKAGES)
DEFAULT_MAX_FRET_SPAN = 4
IMAGE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static')


class MissingMultimediaError(Exception):
    pass

class InvalidParseError(Exception):
    pass

@total_ordering
class Note:
    """
    This class defines a music note by its name and octave, e.g. Note(name="G#", octave=3)
    Notes can be compared, where equality is based on enharmonic equivalence (e.g. G# == Ab)

    Attributes:
        - simple_name: Literal['C', 'D', 'E', 'F', 'G', 'A', 'B']
        - modifier: Literal['bb', 'b', '', '#', '##']
        - name: str, the note's name (e.g. 'G#')
        - octave: int, the number of octaves above C0
        - semitones: int, the number of semitones above C0
        - frequency: float, the frequency [Hz] of the note, using A4=440 convention
        - staff_line: int, the number of lines/spaces above middle C (C4); e.g., E4 = 2 (1 space + 1 line)
    """

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
    STAFF_LINE_OFFSET = dict(zip(SEMITONE_MAPPER.keys(), range(len(SEMITONE_MAPPER))))

    def __init__(self, name: str, octave: int):
        self.simple_name, self.modifier = self.parse_name(name)
        self.name = name
        self.octave = octave
        self.semitones = (
            12 * self.octave +
            self.SEMITONE_MAPPER[self.simple_name] +
            self.MODIFIER_MAPPER[self.modifier]
        )
        self.frequency: float = 440 * 2 ** ((self.semitones - 57) / 12)
        self.staff_line: int = (
            self.STAFF_LINE_OFFSET[self.simple_name] +
            len(self.SEMITONE_MAPPER) * (self.octave - 4)
        )

    def parse_name(self, name: str) -> tuple[str, str]:
        """Init a note from a string, e.g. 'C#4'"""
        assert len(name) <= 3
        simple_name = name[0].upper()
        assert simple_name in self.SEMITONE_MAPPER.keys()
        if len(name) > 1:
            modifier = name[1:]
            assert modifier in self.MODIFIER_MAPPER.keys()
        else:
            modifier = ''
        return simple_name, modifier

    def guitar_positions(self, guitar: Optional['Guitar'] = None, valid_only: bool = True) -> 'GuitarPosition':
        """
        Return the set of all positions (string + fret) a note can be played on a guitar
        :param guitar: Guitar, defines the guitar (standard tuning by default)
        :param valid_only: bool, only include "valid" positions (above nut and below top fret)
        :return: GuitarPosition (essentially a dict of {string: fret}
        """
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

    def add_semitones(self, semitones: int, bias: Optional[Literal['b', '#']] = None) -> 'Note':
        if bias is None:
            bias = self.modifier[0] if self.modifier else 'b'
        return self.from_semitones(self.semitones + semitones, bias)

    def same_name(self, other: 'Note') -> bool:
        return self.semitones % 12 == other.semitones % 12

    def nearest_above(self, note: str, allow_equal: bool = True) -> 'Note':
        bias = note[1] if len(note) > 1 else None
        interval = (Note(note, 0) - self) % 12
        if not allow_equal and interval == 0:
            interval = 12
        return self.add_semitones(interval, bias)

    def nearest_below(self, note: str, allow_equal: bool = True) -> 'Note':
        bias = note[1] if len(note) > 1 else None
        interval = (self - Note(note, 0)) % 12
        if not allow_equal and interval == 0:
            interval = 12
        return self.add_semitones(-interval, bias)

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


@total_ordering
class Chord:
    """
    This class defines a music chord as a list of `Note`s.
    Note, a `Chord` does not imply quality or extensions, e.g.; these notions exist in a `ChordName`.
    A Chord is simply an ordered list of `Note`s agnostic to any of these notions.
    Chords can be compared, where equality means the same number of notes and all notes are enharmonically equivalent.

    Attributes:
        - notes: list[Note], sorted by semitone
        - num_total_guitar_positions: int, a mutable value that is populated after running the `guitar_positions` method
        - num_playable_guitar_positions: int, a mutable value that is populated after running the `guitar_positions` method
        - staff_line_gaps: list[int], same length as `notes`, where the first element is None,
            and subsequent values (ith) are the diff between staff line of the ith and (i-1)th note
    """

    def __init__(self, notes: list[Note]):
        self.notes = sorted(notes)
        self.num_total_guitar_positions = None
        self.num_playable_guitar_positions = None
        if notes:
            self.staff_line_gaps = [None]
            for note, next_note in zip(self.notes[:-1], self.notes[1:]):
                self.staff_line_gaps.append(next_note.staff_line - note.staff_line)
        else:
            self.staff_line_gaps = []

    def guitar_positions(
            self,
            guitar: Optional['Guitar'] = None,
            max_fret_span: int = 4,
            include_unplayable: bool = False,
            allow_thumb: bool = True
    ) -> list['GuitarPosition']:
        """
        Return all guitar positions that can play a given `Chord`
        :param guitar: Guitar, defining the tuning
        :param max_fret_span: int, max space between lowest and highest fret to be considered "playable"
        :param include_unplayable: bool
        :param allow_thumb: bool
        :return: list[GuitarPosition]
        """
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
            guitar_position = GuitarPosition(
                positions_dict, notes=self.notes, guitar=guitar, max_fret_span=max_fret_span
            )
            assert guitar_position.valid  # This should be true from above
            if (guitar_position.playable and not guitar_position.redundant) or include_unplayable:
                if allow_thumb or (not allow_thumb and not guitar_position.use_thumb):
                    playable_positions.append(guitar_position)
        self.num_playable_guitar_positions = len(playable_positions)
        return sorted(playable_positions, key=lambda x: x.fret_span)

    @staticmethod
    def from_string(string: str) -> 'Chord':
        return Chord([Note.from_string(n) for n in string.split(',')])

    def to_audio(self, sample_rate: int = 44_100, duration: float = 1.0, delay: bool = True) -> 'Audio':
        """
        Convert a chord to an `Audio` waveform;
        the chord is arpeggiated over the first half of the `duration`, and then rings for the second half
        :param sample_rate: int
        :param duration: float, total duration [s] of audio
        :param delay: bool, whether to apreggiate the chord
        """
        n = int(sample_rate * duration)
        t = np.linspace(0.0, duration, num=n)
        tau = duration * 0.2
        waveform = np.zeros(n)
        delay_duration = duration / (2 * len(self.notes)) if delay else 0
        for i, note in enumerate(self.notes):
            signal = np.zeros(n)
            n_harmonics = min(10, int((sample_rate / 2) // note.frequency))
            for harmonic in range(1, n_harmonics + 1):
                w = 2 * np.pi * note.frequency * harmonic
                phase = 0.05 * note.frequency * np.sin(0.5 * t)
                signal += np.sin(w * t + phase) / 1.5 ** harmonic
            signal /= (2 * np.max(np.abs(signal)))
            delay_samples = int(sample_rate * delay_duration * i)
            envelope = np.exp(-(t - delay_duration * i) / tau)
            envelope[:delay_samples] = 0
            signal *= envelope
            waveform += signal
        waveform /= (2 * np.max(np.abs(waveform)))
        return Audio(sample_rate=sample_rate, waveform=waveform)

    def semitone_distance(self, other: 'Chord') -> int:
        """
        It might not be that the case that each note resolves to its same-index counterpart in the other chord;
        so we need to check all the pairings
        """
        cost_matrix = np.zeros(shape=(len(self.notes), len(other.notes)))
        for row, s in enumerate(self.notes):
            for col, o in enumerate(other.notes):
                cost_matrix[row, col] = abs(s - o)
        if col > row:
            cost_matrix = cost_matrix.transpose()
        assignments = graph.assign(cost_matrix)
        return int(sum(cost_matrix[row, col] for row, col in enumerate(assignments)))

    def __repr__(self):
        return ','.join(str(n) for n in self.notes)

    def __eq__(self, other: 'Chord') -> bool:
        return (
            (len(self.notes) == len(other.notes)) and
            all(s == o for s, o in zip(self.notes, other.notes))
        )

    def __lt__(self, other) -> bool:
        for s, o in zip(self.notes, other.notes):
            if s != o:
                return s < o
        return len(self.notes) < len(other.notes)

    def __hash__(self):
        return hash(tuple(note.semitones for note in self.notes))


class ChordName:
    """
    This class defines a chord name by "chord note", root note, quality, and extensions.
    A `ChordName` is inited by a human readable string (e.g. Cmaj7#11/E), where the above elements are parsed out.
    A `ChordName` contains all the note names defining the chord, but unlike a `Chord`,
    it doesn't imply their order (except for the root) or octave

    Attributes:
        - chord_note: str
        - quality: str
        - extensions: list[str]
        - root: str
        - chord_name: str
        - key_bias: Literal['b', '#']
        - note_names: list[str]
        - extension_nams: list[str]
    """

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
        self.key_bias = self.KEY_BIAS[self.chord_note]
        self.note_names: list[str] = [
            Note(self.chord_note, octave=0).add_semitones(s, bias=self.key_bias).name
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
            bias = ext[0] if ext[0] in ('#', 'b') else self.key_bias
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
            self, *,
            lower: 'Note' = Note('C', 0),
            raise_octave: Optional[dict[int, int]] = None
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
            if lower.nearest_above(note).add_semitones(12 * octave) <= upper  # type: ignore
        ]
        possible_extensions = [
            lower.nearest_above(ext).add_semitones(12 * octave)
            for octave in range(1, max_octaves)
            for ext in self.extension_names
            if lower.nearest_above(ext).add_semitones(12 * octave) <= upper  # type: ignore
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


class ChordProgression:
    """
    This class defines a chord progression (essentially a list of `ChordName`),
    which allows for computing optimal voice leading

    Attributes:
        - chords: list[ChordName]
    """
    def __init__(self, chords: list[ChordName]):
        self.chords = chords
        self.n_chords = len(chords)

    def optimal_voice_leading(self, lower: Note, upper: Note, use_dijkstra: bool = True) -> list[Chord]:
        voicings = [
            chord.get_all_chords(lower=lower, upper=upper)
            for chord in self.chords
        ]
        if use_dijkstra:
            # for each chord, add the index to ensure the nodes are unique
            chord_node = tuple[int, Optional[Chord]]
            voicings_flat = [(i, vv) for i, v in enumerate(voicings) for vv in v]
            initial: chord_node = (-1, None)
            terminal: chord_node = (self.n_chords, None)
            nodes: list[chord_node] = [initial, *voicings_flat, terminal]
            edges: list[graph.Edge] = []
            initial_edges = [
                graph.Edge(start=initial, end=(0, v), weight=0.)
                for v in voicings[0]
            ]
            terminal_edges = [
                graph.Edge(start=(self.n_chords - 1, v), end=terminal, weight=0.)
                for v in voicings[-1]
            ]
            for i, v in enumerate(voicings[:-1]):
                v_next = voicings[i + 1]
                for start, end in product(v, v_next):
                    edge = graph.Edge(start=(i, start), end=(i + 1, end), weight=start.semitone_distance(end))
                    edges.append(edge)
            edges = initial_edges + edges + terminal_edges
            g = graph.Graph(nodes=nodes, edges=edges)
            prog: list[chord_node] = g.shortest_path(initial, terminal)  # type: ignore
            return [c for _, c in prog[1:-1]]
        else:
            motions = []
            for prog_ in product(*voicings):
                prog: list[Chord] = list(prog_)
                motion = sum([
                    c.semitone_distance(prog[i + 1])
                    for i, c in enumerate(prog[:-1])
                ])
                motions.append({
                    'progression': prog,
                    'motion': motion
                })
            motions = sorted(motions, key=lambda x: x['motion'])
            return motions[0]['progression']

    def optimal_guitar_positions(
            self,
            guitar: Optional['Guitar'] = None,
            allow_repeats: bool = False,
            respect_fingers: bool = False,
            allow_identical: bool = False,
            allow_thumb: bool = True,
    ) -> list['GuitarPosition']:
        guitar = guitar or Guitar()
        positions = [
            get_all_guitar_positions_for_chord_name(
                chord_name=chord,
                guitar=guitar,
                allow_repeats=allow_repeats,
                allow_identical=allow_identical,
                allow_thumb=allow_thumb,
            )
            for chord in self.chords
        ]
        positions = [
            list(filter(lambda x: (x.playable and not x.redundant), p))
            for p in positions
        ]
        if any(len(p) == 0 for p in positions):
            return []
        position_node = tuple[int, Optional[GuitarPosition]]
        # for each chord, add the index to ensure the nodes are unique
        positions_flat = [(i, pp) for i, p in enumerate(positions) for pp in p]
        initial, terminal = (-1, None), (self.n_chords, None)
        nodes: list[position_node] = [initial, *positions_flat, terminal]
        edges: list[graph.Edge] = []
        initial_edges = [
            graph.Edge(start=initial, end=(0, p), weight=0.)
            for p in positions[0]
        ]
        terminal_edges = [
            graph.Edge(start=(self.n_chords - 1, p), end=terminal, weight=0.)
            for p in positions[-1]
        ]
        for i, p in enumerate(positions[:-1]):
            p_next = positions[i + 1]
            for start, end in product(p, p_next):
                edge = graph.Edge(
                    start=(i, start),
                    end=(i + 1, end),
                    weight=start.motion_distance(end, respect_fingers=respect_fingers)
                )
                edges.append(edge)
        edges = initial_edges + edges + terminal_edges
        g = graph.Graph(nodes=nodes, edges=edges)
        prog: list[position_node] = g.shortest_path(initial, terminal)  # type: ignore
        return [p for _, p in prog[1:-1]]


class Audio:
    """
    Class to define an audio signal. Attributes:
        sample_rate: int, sampling frequency in Hz
        duration: float, total duration [s] of audio
        waveform: the waveform of the audio signal
    """
    def __init__(self, sample_rate: int, waveform: Iterable[float]):
        self.sample_rate = sample_rate
        self.waveform = list(waveform)
        self.duration = len(self.waveform) / sample_rate

    def write_wav(self, path: str) -> None:
        """
        Write a wave file of the audio signal
        :param path: str, path to write to
        """
        if not media_installed:
            raise MissingMultimediaError('Missing multimedia packages; use `--extra media` on install')
        import wave
        audio = np.array([self.waveform, self.waveform]).T
        # Convert to (little-endian) 16 bit integers.
        audio_norm = (audio * (2 ** 15 - 1)).astype("<h")
        with wave.open(path, "w") as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(self.sample_rate)
            f.writeframes(audio_norm.tobytes())

    def __add__(self, other: 'Audio') -> 'Audio':
        assert self.sample_rate == other.sample_rate
        return Audio(
            sample_rate=self.sample_rate,
            waveform=self.waveform + other.waveform
        )


class Staff:
    """
    This class defines a (grand) music staff, which contains a sequence of zero or more chords.
    This implies how many additional ledger lines are needed for each chord in the sequence.
    At present, there is no notion of "time" or "meter", and all chords are whole notes with no bar lines.

    Attributes:
        - chords: list[Chord]
        - ledger_lines: list[tuple[int, int]], for each chord, the number of additional ledger lines
            above or below the grand staff that are needed
    """
    def __init__(self, chords: Optional[list[Chord]] = None):
        # ledger line 0 is middle C, one int index for each line or space
        self.chords = chords or []
        self.ledger_lines = []
        for chord in self.chords:
            self.ledger_lines.append((
                min((min(chord.notes).staff_line + 1) & ~1, 2),
                max(max(chord.notes).staff_line & ~1, 10)
            ))

    def write_png(self, path: str) -> None:
        """Write a png of the staff to a file"""
        if not media_installed:
            raise MissingMultimediaError('Missing multimedia packages; use `--extra media` on install')
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        figsize = (len(self.chords) + 1, 1.75)
        fig, ax = plt.subplots(figsize=figsize)
        # matplotlib axes will have origin (0, 0) at left of staff, middle c, so staff goes from y = 2 to 10
        xlim = [0.5, 10 + 6 * len(self.chords) - 3]
        ylim = [2, 10]  # noqa: F841
        note_positions = [10 + 6 * n for n in range(len(self.chords))]
        note_rad = 1
        # clef
        im = plt.imread(os.path.join(IMAGE_DIR, 'treble_clef.png'))
        ax.imshow(im, extent=(1, 5, -1, 12))
        im = plt.imread(os.path.join(IMAGE_DIR, 'bass_clef.png'))
        ax.imshow(im, extent=(1, 6, -9, -2))
        # staff
        for line in range(2, 12, 2):
            ax.plot(xlim, [line] * 2, 'k-')
        for line in range(-2, -12, -2):
            ax.plot(xlim, [line] * 2, 'k-')
        for chord, (lowest_line, highest_line), note_pos in zip(self.chords, self.ledger_lines, note_positions):
            if lowest_line < -10:
                for line in range(lowest_line, 10, 2):
                    ax.plot([note_pos - 2 * note_rad, note_pos + 2 * note_rad], [line] * 2, 'k-')
            if highest_line > 10:
                for line in range(12, highest_line + 2, 2):
                    ax.plot([note_pos - 2 * note_rad, note_pos + 2 * note_rad], [line] * 2, 'k-')
            shift = 0
            for note, gap in zip(chord.notes, chord.staff_line_gaps):
                if shift == 0 and gap is not None and gap < 2:
                    shift = 1.75 * note_rad
                else:
                    shift = 0
                note_pos_ = note_pos + shift
                ax.add_patch(plt.Circle(xy=(note_pos_, note.staff_line), radius=0.9 * note_rad, facecolor="none", edgecolor='k'))
                ax.annotate(note.modifier, xy=(note_pos_ - 2.25 * note_rad, note.staff_line - 0.6), fontsize=12, family='arial')
                if note.staff_line == 0:
                    ax.plot([note_pos_ - 2 * note_rad, note_pos_ + 2 * note_rad], [0, 0], 'k-')
        ax.set_aspect(0.9)
        ax.axis('off')
        plt.tight_layout()
        fig.savefig(path, bbox_inches='tight', pad_inches=0)


class Guitar:
    """
    This class is used to represent a guitar.

    Attributes:
        - open_tuning: dict[Hashable, Note], the tuning of the guitar with no capo or fretted notes
        - capo: int, fret position of capo (if any)
        - tuning: dict[Hashable, Note], the tuning of the guitar (including capo)
        - tuning_name: Literal['standard', 'custom']
        - string_names: List[Hashable], the tuning keys
        - frets: int, the number of playable frets (above the capo)
        - lowest: Note, lowest playable note
        - highest: Note, highest playable note
    """

    Tuning = dict[Hashable, Note]
    TUNINGS: dict[str, Tuning] = {
        'standard': {
            'E': Note('E', 2),
            'A': Note('A', 2),
            'D': Note('D', 3),
            'G': Note('G', 3),
            'B': Note('B', 3),
            'e': Note('E', 4),
        },
        'drop_d': {
            'D': Note('D', 2),
            'A': Note('A', 2),
            'd': Note('D', 3),
            'G': Note('G', 3),
            'B': Note('B', 3),
            'e': Note('E', 4),
        },
        'open_d': {
            'D': Note('D', 2),
            'A': Note('A', 2),
            'd': Note('D', 3),
            'F#': Note('F#', 3),
            'a': Note('A', 3),
            'dd': Note('D', 4),
        },
        'open_g': {
            'D': Note('D', 2),
            'G': Note('G', 2),
            'd': Note('D', 3),
            'g': Note('G', 3),
            'B': Note('B', 3),
            'dd': Note('D', 4),
        },
        'open_a': {
            'E': Note('E', 2),
            'A': Note('A', 2),
            'C#': Note('C#', 3),
            'e': Note('E', 3),
            'a': Note('A', 3),
            'ee': Note('E', 4),
        },
    }
    DEFAULT_FRETS = 22

    def __init__(
            self,
            tuning_name: Optional[str] = None,
            tuning: Optional[Tuning] = None,
            frets: int = DEFAULT_FRETS,
            capo: int = 0
    ):
        if tuning_name:
            assert tuning_name in self.TUNINGS, f"Invalid `tuning_name` ({tuning_name}); choose from {self.TUNINGS.keys()}"
            self.tuning_name = tuning_name
            self.open_tuning = self.TUNINGS[self.tuning_name]
        elif tuning:
            self.tuning_name = 'custom'
            self.open_tuning = tuning
        else:
            self.tuning_name = 'standard'
            self.open_tuning = self.TUNINGS[self.tuning_name]
        self.capo = capo
        self.tuning = {name: note.add_semitones(capo) for name, note in self.open_tuning.items()}
        self.string_names = list(self.tuning.keys())
        self.frets = frets - capo
        self.lowest = min(note for note in self.tuning.values())
        self.highest = max(note for note in self.tuning.values()).add_semitones(self.frets)

    def __repr__(self):
        return str(self.tuning)

    @staticmethod
    def parse_tuning(tuning: Optional[str] = None, how: Optional[Literal['json', 'csv']] = None) -> Tuning:
        if not tuning:
            return Guitar.TUNINGS['standard']
        how = how or ('json' if tuning.startswith('{') else 'csv')
        if how == 'json':
            try:
                return {
                    string: Note.from_string(note)
                    for string, note in json.loads(tuning.replace("'", '"')).items()
                }
            except Exception:
                raise InvalidParseError(f'Invalid json string ({tuning})')
        elif how == 'csv':
            try:
                out = dict()
                for pair in tuning.split(';'):
                    string, note = pair.split(',')
                    out[string.strip()] = Note.from_string(note.strip())
                return out
            except Exception:
                raise InvalidParseError(f'Invalid csv string ({tuning})')
        else:
            raise InvalidParseError(f'Unsupported `how` ({how}); choose `json` or `csv`')


    def notes(self, position: dict[Hashable, int]) -> list[Note]:
        return [self.tuning[string].add_semitones(fret) for string, fret in position.items()]

    def chord(self, position: dict[Hashable, int]) -> Chord:
        return Chord(self.notes(position))


class GuitarPosition:
    """
    This class defines a "guitar position", which is essentially a dict describing where strings should be fretted
    for a given guitar to play one or more notes.
    A guitar position can also be inited including a list of notes (these must match the positions) in order to
    keep track of the `Chord` (and enharmonics) associated with the `GuitarPosition`.

    Attributes:
        - guitar: Guitar
        - valid: bool, whether the position is theoretically playable
        - lowest_fret: int, the lowest fret needed to finger the position
        - fret_span: int, the span from lowest to highest fret (inclusive, e.g. span from 1 to 3 = 3)
        - position_dict: dict[Hashable, int], specifying the fret for each string of the guitar
        - open_strings: list[int], indices of strings that are open (relative to the string order of the Guitar)
        - muted_strings: list[int], indices of strings that are muted
        - fretted_strings: list[int], indices of strings that are fretted
            (note, open_strings, muted_strings, and fretted_strings must partition the guitar strings)
        - use_thumb: bool, whether thumb is needed to finger the position
        - max_interior_gap: int, largest gap between fretted strings (exclusive), used for sorting
        - playable: bool, whether the position is considered playable
        - barre: bool, whether the chord needs to be played as a barre chord
        - barred_strings_inds: the string indices that are barred
        - redundant: whether the fingering is exactly one (or more) octaves transposed from an equivalent fingering
        - chord: the `Chord` corresponding to the fingering
    """

    def __init__(
            self,
            positions: dict[Hashable, int],
            *,
            notes: Optional[list['Note']] = None,
            guitar: Optional['Guitar'] = None,
            max_fret_span: int = DEFAULT_MAX_FRET_SPAN
    ):
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
        self.positions_dict: dict[Hashable, int] = {
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
        self.fingers_dict: dict[Hashable, str] = dict()
        # Can play a 5th note with thumb on bottom string
        self.use_thumb = (
            (len(self.fretted_strings) == 5) and
            (self.positions_dict.get(self.guitar.string_names[0], -1) == self.lowest_fret)
        )
        if self.use_thumb:
            self.fingers_dict[self.guitar.string_names[0]] = 'T'
        self.max_interior_gap = self._max_interior_gap()
        # Barre chord needs
        self.barre = (
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
        self.playable = self.is_playable(max_fret_span=max_fret_span)
        if self.barre:
            # All strings along the barre position
            self.barred_strings_inds = list(range(min(lowest_fret_strings), max(lowest_fret_strings) + 1))
            for string in self.barred_strings_inds:
                self.fingers_dict[self.guitar.string_names[string]] = '1'
            available_fingers = ['2', '3', '4']
        else:
            self.barred_strings_inds = []
            available_fingers = ['1', '2', '3', '4']
        # If all fretted notes are >= fret 12, this is a redundant position
        # there is an identical shape 12 frets below that gives (nearly) the same voicing
        self.redundant = all(fret >= 12 for fret in self.positions_dict.values() if fret != 0)
        chord = self.guitar.chord(self.positions_dict)
        if notes:
            enharmonic_chord = Chord(notes)
            assert enharmonic_chord == chord
            self.chord = enharmonic_chord
        else:
            self.chord = chord
        sorted_positions = self._get_sorted_positions()
        finger_skip = 0
        excess_fingers = len(available_fingers) - len(sorted_positions)
        for (fret, string), finger in zip(sorted_positions, available_fingers):
            # If there is a fret gap, skip a finger if there are excess
            fret_gap = fret - self.lowest_fret
            if fret_gap >= int(finger) and excess_fingers > finger_skip:
                finger_skip += min(fret_gap - 1, excess_fingers)
            finger_ = str(int(finger) + finger_skip)
            self.fingers_dict[self.guitar.string_names[string]] = finger_
        self.fingers_positions_dict: dict[Hashable, tuple[str, int]] = {
            string: (finger, self.positions_dict[string])
            for string, finger in self.fingers_dict.items()
        }
        if len(self.fingers_dict) < len(self.fretted_strings) and self.playable:
            self.playable = False
            warnings.warn(f'Unplayable position not flagged by `is_playable` method: {self}')

    def _get_sorted_positions(self) -> list[tuple[int, int]]:
        """
        Sort positions by fret ascending, string ascending
        (this should generally correspond with the ordering of fingers)
        skip positions that are open, already accounted for with thumb, or barred
        """
        return sorted([
            (fret, self.guitar.string_names.index(string))
            for string, fret in self.positions_dict.items()
            if fret > 0 and not (
                self.fingers_dict.get(string) == 'T' or
                (self.barre and self.fingers_dict.get(string) == '1' and fret == self.lowest_fret)
            )
        ])

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
        if not self.barre and n_notes > 4:
            return False
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

    def __hash__(self):
        return hash(tuple(self.positions_dict.items()))

    def is_subset(self, other: 'GuitarPosition') -> bool:
        return (
            (self.positions_dict.keys() <= other.positions_dict.keys()) and
            all(self_val == other.positions_dict[key] for key, self_val in self.positions_dict.items())
        )

    def printable(self, fingers: bool = False) -> list[str]:
        """
        Given a chord position, return ASCII art for the position; each line is an item of the list
        (e.g., you can `print('\n'.join(position.printable()))`)
        """
        rows = []
        widest_name = max(len(str(string)) for string in self.guitar.string_names)
        for i, string in reversed(list(enumerate(self.guitar.string_names))):
            left_padding = ' ' * (widest_name - len(str(string)))
            frets = ['---'] * self.fret_span
            fret = self.positions_dict.get(string, -1)
            if fret > 0:
                fret_marker = f'-{self.fingers_dict[string]}-' if fingers else '-@-'
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

    def motion_distance(self, other: 'GuitarPosition', respect_fingers: bool = False) -> float:
        """
        A measure of the "distance" required to move from one guitar position to another;
        If `respect_fingers`, distance is computed as the total distance each recommended finger needs to move;
        Otherwise, equal to the total number of frets and strings that need moved for minimum motion.
        Assume moving from unfretted to fretted is zero cost
        """
        if respect_fingers:
            moving_fingers = set(self.fingers_dict.values()).intersection(set(other.fingers_dict.values()))
            cost = 0
            for finger in moving_fingers:
                start = [(string, fret) for string, (finger_, fret) in self.fingers_positions_dict.items() if finger == finger_]
                end = [(string, fret) for string, (finger_, fret) in other.fingers_positions_dict.items() if finger == finger_]
                # if a finger is barring multiple strings, only count the cost of moving from
                # the lowest string-fret pair of self to other
                cost += self.motion_helper(start=start[0], end=end[0])
        else:
            cost_matrix = np.zeros((len(self.positions_dict), len(other.positions_dict)))
            for row, s in enumerate(self.positions_dict.items()):
                for col, o in enumerate(other.positions_dict.items()):
                    cost_matrix[row, col] = self.motion_helper(start=s, end=o)
            if cost_matrix.shape[0] < cost_matrix.shape[1]:
                cost_matrix = cost_matrix.transpose()
            assignments = graph.assign(cost_matrix, assign_surplus=False)
            cost = int(sum(cost_matrix[row, col] for row, col in enumerate(assignments) if col is not None))
        return cost

    def motion_helper(self, start: tuple[Hashable, int], end: tuple[Hashable, int]) -> int:
        """
        Compute the Manhattan distance between two fretted positions on a fretboard
        (unfretted positions have zero distance)
        """
        if start[1] == 0 or end[1] == 0:
            return 0
        string_motion = abs(self.guitar.string_names.index(start[0]) - self.guitar.string_names.index(end[0]))
        fret_motion = abs(start[1] - end[1])
        return string_motion + fret_motion

    @staticmethod
    def sorted(p: list['GuitarPosition'], target_fret: int = 7) -> list['GuitarPosition']:
        """Sort a list of GuitarPositions on fret span, then interior gaps, then near a target fret"""
        return sorted(p, key=lambda x: (
            # Sort first on fret span
            x.fret_span,
            # Then, fewest interior gaps
            x.max_interior_gap,
            # Then nearest to target fret
            abs(x.lowest_fret - target_fret),
        ))

    @staticmethod
    def filter_subsets(p: list['GuitarPosition']) -> list['GuitarPosition']:
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
        required_notes: Optional[set[Note]] = None,
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
