from itertools import product
from typing import Optional
from functools import partial
from multiprocessing import Pool
import os

import numpy as np

from music.primitives import Note, NoteEvent, NoteSequence, Chord, ChordName, ChordProgression, ControlPoint
from music.instruments import Guitar, GuitarPosition
from music.audio import Audio
from music import graph


class FretboardEngine:
    def __init__(
        self,
        max_fret_span: int = 4,
        allow_thumb: bool = True
    ):
        self.max_fret_span = max_fret_span
        self.allow_thumb = allow_thumb

    def note_to_guitar_position(self, note: Note, guitar: Optional['Guitar'] = None, valid_only: bool = True) -> GuitarPosition:
        """
        Return the set of all positions (string + fret) a note can be played on a guitar
        :param note: Note, The note to compute
        :param guitar: Guitar, defines the guitar (standard tuning by default)
        :param valid_only: bool, only include "valid" positions (above nut and below top fret)
        :return: GuitarPosition (essentially a dict of {string: fret}
        """
        guitar = guitar or Guitar()
        positions = {
            string: note - other_note
            for string, other_note in guitar.tuning.items()
            if (valid_only and note >= other_note and (note - other_note) <= guitar.frets)
               or not valid_only
        }
        return GuitarPosition(positions, guitar=guitar)

    def chord_to_guitar_positions(
            self,
            chord: Chord,
            guitar: Optional['Guitar'] = None,
            include_unplayable: bool = False,
    ) -> list['GuitarPosition']:
        """
        Return all guitar positions that can play a given `Chord`
        :param chord: Chord, the chord to compute
        :param guitar: Guitar, defining the tuning
        :param include_unplayable: bool
        :return: list[GuitarPosition]
        """
        guitar = guitar or Guitar()
        # This is a dict of dicts, {note: {string: fret for string in guitar} for note in chord}
        # of all the positions each note can be played on each string
        all_fret_positions = {
            str(note): self.note_to_guitar_position(note=note, guitar=guitar, valid_only=False).positions_dict
            for note in chord.notes
        }
        # Get just the valid positions
        valid_strings = [
            list(self.note_to_guitar_position(note=note, guitar=guitar, valid_only=True).positions_dict.keys())
            for note in chord.notes
        ]
        valid_combinations = [comb for comb in product(*valid_strings) if len(set(comb)) == len(chord.notes)]
        playable_positions = []
        for comb in valid_combinations:
            positions_dict = {
                string: all_fret_positions[str(note)][string]
                for note, string in zip(chord.notes, comb)
            }
            guitar_position = GuitarPosition(
                positions_dict, notes=chord.notes, guitar=guitar, max_fret_span=self.max_fret_span
            )
            assert guitar_position.valid  # This should be true from above
            if (guitar_position.playable and not guitar_position.redundant) or include_unplayable:
                if self.allow_thumb or (not self.allow_thumb and not guitar_position.use_thumb):
                    playable_positions.append(guitar_position)
        num_playable_guitar_positions = len(playable_positions)
        return sorted(playable_positions, key=lambda x: x.fret_span)

    def chord_name_to_guitar_chords(
            self,
            chord_name: ChordName,
            guitar: Optional['Guitar'] = None,
            allow_repeats: bool = False,
            allow_identical: bool = False
    ) -> list['Chord']:
        guitar = guitar or Guitar()
        return chord_name.get_all_chords(
            lower=guitar.lowest, upper=guitar.highest, max_notes=len(guitar.string_names),
            allow_repeats=allow_repeats, allow_identical=allow_identical
        )

    def chord_name_to_all_guitar_positions(
            self,
            chord_name: ChordName,
            guitar: Guitar,
            allow_repeats: bool,
            allow_identical: bool,
            parallel: bool = False,
    ) -> list[GuitarPosition]:
        chords = chord_name.get_all_chords(
            lower=guitar.lowest, upper=guitar.highest, max_notes=len(guitar.tuning),
            allow_repeats=allow_repeats, allow_identical=allow_identical,
        )
        if parallel:
            pass
            with Pool(os.cpu_count()) as p:
                nested = p.map(partial(self.chord_to_guitar_positions, guitar=guitar, include_unplayable=True), chords)
            positions = [pos for poss in nested for pos in poss]
        else:
            positions = []
            for chord in chords:
                positions += self.chord_to_guitar_positions(chord=chord, guitar=guitar, include_unplayable=True)
        return positions

    def chord_progression_to_optimal_guitar_positions(
            self,
            chord_progression: ChordProgression,
            guitar: Optional['Guitar'] = None,
            allow_repeats: bool = False,
            respect_fingers: bool = False,
            allow_identical: bool = False,
    ) -> list['GuitarPosition']:
        guitar = guitar or Guitar()
        positions = [
            self.chord_name_to_all_guitar_positions(
                chord_name=chord,
                guitar=guitar,
                allow_repeats=allow_repeats,
                allow_identical=allow_identical,
            )
            for chord in chord_progression.chords
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
        initial, terminal = (-1, None), (chord_progression.n_chords, None)
        nodes: list[position_node] = [initial, *positions_flat, terminal]
        edges: list[graph.Edge] = []
        initial_edges = [
            graph.Edge(start=initial, end=(0, p), weight=0.)
            for p in positions[0]
        ]
        terminal_edges = [
            graph.Edge(start=(chord_progression.n_chords - 1, p), end=terminal, weight=0.)
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


class AudioEngine:
    def __init__(self, sample_rate: int = 44_100, tempo: float = 120.):
        self.sample_rate = sample_rate
        self.tempo = tempo

    def beats_to_seconds(self, beats: float) -> float:
        return (60 / self.tempo) * beats

    def beats_to_index(self, beats: float) -> int:
        return int(self.sample_rate * self.beats_to_seconds(beats))

    def seconds_to_beats(self, seconds: float) -> float:
        return seconds * self.tempo / 60

    def note_sequence_to_audio(self, note_sequence: NoteSequence) -> Audio:
        duration = self.beats_to_seconds(note_sequence.duration_beats + note_sequence.first_offset)
        n = int(self.sample_rate * duration)
        waveform = np.zeros(n)
        for event in note_sequence.events:
            duration_event = self.beats_to_seconds(event.duration_beats)
            offset_event = self.beats_to_seconds(event.offset_beats)
            n_event = int(self.sample_rate * duration_event)
            n_offset = int(self.sample_rate * offset_event)
            t_event = np.linspace(0.0, duration_event, num=n_event)
            signal_event = np.zeros(n_event)
            for note in event.notes:
                n_harmonics = min(10, int((self.sample_rate / 2) // note.frequency))
                for harmonic in range(1, n_harmonics + 1):
                    w = 2 * np.pi * note.frequency * harmonic
                    phase = 0.05 * note.frequency * np.sin(0.5 * t_event)
                    amp = 1 / 1.5 ** harmonic
                    signal_event += amp * np.sin(w * t_event + phase)
            if (scale_factor := 2 * np.max(np.abs(signal_event))) > 0:
                signal_event /= scale_factor
            waveform[n_offset:(n_offset + n_event)] += signal_event
        envelope = self.construct_envelope(n, control_points=note_sequence.volume_control_points)
        waveform *= envelope
        waveform /= (2 * np.max(np.abs(waveform)))
        return Audio(sample_rate=self.sample_rate, waveform=waveform)

    def construct_envelope(self, n: int, control_points: list[ControlPoint]) -> np.ndarray:
        envelope = np.ones(n)
        total_beats = self.seconds_to_beats(n / self.sample_rate)
        last_point = ControlPoint(beat=total_beats, level=0.)
        for point, next_point in zip(control_points, [*control_points[1:], last_point]):
            index = self.beats_to_index(point.beat)
            next_index = self.beats_to_index(next_point.beat)
            start_level = envelope[index - 1] if index > 0 else 1.
            if point.mode == 'step':
                envelope[index:next_index] = point.level
            elif point.mode == 'linear':
                if point.duration_beats:
                    int_index = self.beats_to_index(point.beat + point.duration_beats)
                else:
                    int_index = next_index
                envelope[index:int_index] = np.interp(
                    x=np.linspace(0, 1, int_index - index), xp=[0, 1], fp=[start_level, point.level]
                )
                envelope[int_index:next_index] = point.level
            elif point.mode == 'exponential':
                n = next_index - index
                duration = self.beats_to_seconds(next_point.beat - point.beat)
                t = np.linspace(0., duration, n)
                envelope[index:next_index] = (start_level - point.level) * np.exp(-t / (point.tau * duration)) + point.level
        return envelope


    def chord_to_audio(self, chord: Chord, duration_beats: float = 1.0, delay: bool = True) -> 'Audio':
        """
        Convert a chord to an `Audio` waveform;
        the chord is arpeggiated over the first half of the `duration`, and then rings for the second half
        :param sample_rate: int
        :param duration_beats: float, total duration [s] of audio
        :param delay: bool, whether to apreggiate the chord
        """
        if delay:
            n_notes = len(chord.notes)
            durations = list(reversed([duration_beats / 2 + i * (duration_beats / 2) / n_notes for i in range(n_notes)]))
            offsets = [duration_beats - d for d in durations]
            note_sequence = NoteSequence(
                events=[
                    NoteEvent(notes=[note], duration_beats=d, offset_beats=o)
                    for note, d, o in zip(chord.notes, durations, offsets)
                ],
            )
            for o in offsets:
                note_sequence.add_volume_control_point(beat=o, mode='step', level=1.)
                note_sequence.add_volume_control_point(beat=o + 0.01, mode='exponential', level=0., tau=0.2)
        else:
            note_sequence = NoteSequence(
                events=[
                    NoteEvent(notes=[note], duration_beats=duration_beats, offset_beats=0.)
                    for note in chord.notes
                ],
                volume_control_points=[ControlPoint(level=0., beat=0.01, mode='exponential', tau=0.1)]
            )
        return self.note_sequence_to_audio(note_sequence)