from dataclasses import dataclass

from functools import total_ordering, partial
from itertools import product, chain, combinations, combinations_with_replacement
from typing import Optional, Literal, Callable

import numpy as np
import scipy

from music import graph, utils
from music.audio import Audio


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

    @classmethod
    def set(cls, notes: list['Note']) -> set['Note']:
        return set(Note(note.name, 0) for note in notes)

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


class NoteEvent:
    """
    One or more Note(s) coupled with a duration (number of beats) and offset
    """
    def __init__(self, notes: list[Note], duration_beats: float = 1., offset_beats: float = 0.):
        self.notes = notes
        self.duration_beats = duration_beats
        self.offset_beats = offset_beats


@dataclass
class ControlPoint:
    beat: float
    level: float
    mode: Literal['step', 'linear', 'exponential'] = 'step'
    duration_beats: Optional[float] = None
    tau: Optional[float] = None


class NoteSequence:
    """
    A sequence of note events
    """
    def __init__(
            self,
            events: list[NoteEvent],
            voice: Optional['Voice'] = None,
            volume_control_points: Optional[list[ControlPoint]] = None
    ):
        self.events = events
        self.first_offset = min(e.offset_beats for e in events)
        self.duration_beats = (
            max(e.offset_beats + e. duration_beats for e in events) - self.first_offset
        )
        self.voice = voice or PureVoice
        self.volume_control_points: list[ControlPoint] = volume_control_points or []

    def add_volume_control_point(
            self, *,
            beat: float,
            level: float,
            mode: Literal['step', 'linear', 'exponential'] = 'step',
            duration_beats: float = None,
            tau: float = None,
    ):
        self.volume_control_points.append(ControlPoint(beat=beat, level=level, mode=mode, duration_beats=duration_beats, tau=tau))
        self.volume_control_points.sort(key=lambda x: x.beat)


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
        if notes:
            self.staff_line_gaps = [None]
            for note, next_note in zip(self.notes[:-1], self.notes[1:]):
                self.staff_line_gaps.append(next_note.staff_line - note.staff_line)
        else:
            self.staff_line_gaps = []

    @staticmethod
    def from_string(string: str) -> 'Chord':
        return Chord([Note.from_string(n) for n in string.split(',')])

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
            self.note_names = utils.rotate_list(self.note_names, root_index)
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
        chord_note = utils.best_match(name, list(self.KEY_BIAS.keys()))
        if '/' in name:
            remainder, root = name.split('/')
        else:
            remainder = name
            root = chord_note
        remainder = remainder.replace(chord_note, '')
        quality = utils.best_match(remainder, list(self.QUALITY_SEMITONE_MAPPER.keys()))
        remainder = remainder.replace(quality, '')
        extensions = []
        while remainder:
            extensions.append(utils.best_match(remainder, list(self.EXTENSION_SEMITONE_MAPPER.keys())))
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


@dataclass
class Voice:
    name: str
    wave: Literal['sine', 'triange', 'sawtooth']
    harmonics: list[tuple[float, float]]
    decay: Optional[float] = None
    gain: float = 1.

    @property
    def wave_func(self) -> Callable[[np.ndarray], np.ndarray]:
        return {
            'sine': np.sin,
            'triangle': partial(scipy.signal.sawtooth, width=0.5),
            'sawtooth': partial(scipy.signal.sawtooth, width=1.0),
        }[self.wave]


PureVoice = Voice(
    name='pure_tone',
    wave='sine',
    harmonics=[(1., 1.)]
)

CleanGuitarVoice = Voice(
    name='clean_guitar',
    wave='sine',
    harmonics=[
        (float(i), 1 / (1.5 ** i))
        for i in range(1, 10)
    ],
    decay=0.3,
)

BrassVoice = Voice(
    name='clean_guitar',
    wave='sine',
    harmonics=[
        (float(i), 1 / i)
        for i in range(1, 10)
    ],
    decay=None,
)

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
    required_notes = required_notes or Note.set(note_list)
    func = combinations_with_replacement if allow_identical else combinations
    powerset = chain.from_iterable(func(note_list, r) for r in range(max_len + 1))
    if allow_repeats:
        subset = [s for s in powerset if Note.set(s) >= required_notes]
    else:
        subset = [s for s in powerset if Note.set(s) >= required_notes and len(Note.set(s)) == len(s)]
    return subset
