import json
import warnings
from typing import Hashable, Optional, Literal

import numpy as np

from music import graph
from music.primitives import Note, Chord

DEFAULT_MAX_FRET_SPAN = 4


class InvalidParseError(Exception):
    pass


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
