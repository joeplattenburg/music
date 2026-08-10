from itertools import product
from typing import Optional
from functools import partial
from multiprocessing import Pool
import os

from music.primitives import Note, Chord, ChordName, ChordProgression
from music.instruments import Guitar, GuitarPosition
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
        num_total_guitar_positions = len(valid_combinations)
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