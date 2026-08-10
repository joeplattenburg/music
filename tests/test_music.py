from functools import reduce
from operator import add
import os
from typing import Hashable

import pytest

import music.primitives


def test_write_wav(tmp_path) -> None:
    d = tmp_path / "foo"
    d.mkdir()
    p = str(d / "audio.wav")
    assert not os.path.exists(p)
    music.primitives.Chord([
        music.primitives.Note('C', 3),
        music.primitives.Note('E', 3),
        music.primitives.Note('G', 3),
    ]).to_audio().write_wav(p)
    assert os.path.exists(p)


def test_write_png(tmp_path) -> None:
    d = tmp_path / "foo"
    d.mkdir()
    p = str(d / "audio.png")
    assert not os.path.exists(p)
    music.graphics.Staff(chords=[
        music.primitives.Chord([
            music.primitives.Note('C', 3),
            music.primitives.Note('E', 3),
            music.primitives.Note('G', 3),
        ])
    ]).write_png(p)
    assert os.path.exists(p)


@pytest.mark.parametrize(
    'note,line', [('C4', 0), ('C5', 7), ('E4', 2), ('Eb4', 2), ('E#4', 2)]
)
def test_staff_line(note: str, line: int) -> None:
    assert music.primitives.Note.from_string(note).staff_line == line


@pytest.mark.parametrize(
    'notes,gaps',
    [
        ([], []),
        ([music.primitives.Note('C', 4)], [None]),
        ([music.primitives.Note('C', 4), music.primitives.Note('C', 4)], [None, 0]),
        ([music.primitives.Note('C', 4), music.primitives.Note('D', 4)], [None, 1]),
    ]
)
def test_staff_line_gaps(notes: list[music.primitives.Note], gaps: list[int]) -> None:
    assert music.primitives.Chord(notes=notes).staff_line_gaps == gaps


@pytest.mark.parametrize(
    'notes,lowest_line,highest_line',
    [
        ([music.primitives.Note(*note) for note in [('C', 5), ('D', 5)]], 2, 10),
        ([music.primitives.Note(*note) for note in [('D', 4)]], 2, 10),
        ([music.primitives.Note(*note) for note in [('C', 4)]], 0, 10),
        ([music.primitives.Note(*note) for note in [('G', 5)]], 2, 10),
        ([music.primitives.Note(*note) for note in [('A', 5)]], 2, 12),
        ([music.primitives.Note(*note) for note in [('C', 4), ('A', 5)]], 0, 12),
    ]
)
def test_staff_extreme_lines(notes: list[music.primitives.Note], lowest_line: int, highest_line: int) -> None:
    staff = music.graphics.Staff(chords=[music.primitives.Chord(notes)])
    assert staff.ledger_lines[0] == (lowest_line, highest_line)


def test_chord_comparison() -> None:
    assert music.primitives.Chord([music.primitives.Note('C', 0)]) == music.primitives.Chord([music.primitives.Note('C', 0)])
    assert music.primitives.Chord([music.primitives.Note('C', 0)]) < music.primitives.Chord([music.primitives.Note('D', 0)])
    assert music.primitives.Chord([music.primitives.Note('C', 0)]) < music.primitives.Chord([music.primitives.Note('C', 0), music.primitives.Note('D', 1)])
    assert music.primitives.Chord([music.primitives.Note('C', 0), music.primitives.Note('D', 1)]) < music.primitives.Chord([
                                                                                                                               music.primitives.Note('C', 0), music.primitives.Note('E', 1)])


def test_guitar_notes() -> None:
    guitar = music.instruments.Guitar()
    expected_notes = [music.primitives.Note(*n) for n in [('G', 2), ('B', 2), ('D', 3)]]
    expected_chord = music.primitives.Chord(expected_notes)
    assert guitar.notes(position={'E': 3, 'A': 2, 'D': 0}) == expected_notes
    assert guitar.chord(position={'E': 3, 'A': 2, 'D': 0}) == expected_chord


def test_bias_in_voicings() -> None:
    chord_name = music.primitives.ChordName('Dmaj7#11')
    assert chord_name.note_names == ['D', 'F#', 'A', 'C#']
    assert chord_name.extension_names == ['G#']
    for chord in chord_name.get_all_guitar_chords():
        names = set([n.name for n in chord.notes])
        assert names == {'D', 'F#', 'A', 'C#', 'G#'}
        for pos in chord.guitar_positions():
            assert pos.chord == chord
            assert set(n.name for n in pos.chord.notes) == names


def test_semitone_distance() -> None:
    c1 = music.primitives.Chord([
        music.primitives.Note('C', 3),
        music.primitives.Note('Eb', 3),
        music.primitives.Note('F', 3),
        music.primitives.Note('A', 3)
    ])
    c2 = music.primitives.Chord([
        music.primitives.Note('C', 3),
        music.primitives.Note('E', 3),
        music.primitives.Note('G', 3),
        music.primitives.Note('Bb', 3),
    ])
    assert c1.semitone_distance(c2) == 4
    assert c2.semitone_distance(c1) == 4


def test_semitone_distance_different_cardinality() -> None:
    c1 = music.primitives.Chord([
        music.primitives.Note('C', 3),
        music.primitives.Note('F', 3),
        music.primitives.Note('A', 3)
    ])
    c2 = music.primitives.Chord([
        music.primitives.Note('C', 3),
        music.primitives.Note('E', 3),
        music.primitives.Note('G', 3),
        music.primitives.Note('Bb', 3),
    ])
    assert c1.semitone_distance(c2) == 4
    assert c2.semitone_distance(c1) == 4


def test_voice_leading() -> None:
    cp = music.primitives.ChordProgression([
        music.primitives.ChordName(n) for n in ['Em7', 'A7', 'Dm7', 'G7', 'CM7']]
    )
    result1 = cp.optimal_voice_leading(
        lower=music.primitives.Note('C', 2),
        upper=music.primitives.Note('C', 4),
        use_dijkstra=True
    )
    result2 = cp.optimal_voice_leading(
        lower=music.primitives.Note('C', 2),
        upper=music.primitives.Note('C', 4),
        use_dijkstra=False
    )
    assert result1 == result2


def test_audio_add() -> None:
    import numpy as np
    t = np.linspace(0, 1, 100)
    sample_rate = 100
    x1 = music.audio.Audio(sample_rate=sample_rate, waveform=np.sin(t))
    x2 = music.audio.Audio(sample_rate=sample_rate, waveform=np.sin(2 * t))
    x3 = x1 + x2
    assert x3.duration == 2.0


def test_audio_from_chord_list() -> None:
    chords = [
        music.primitives.ChordName('G7').get_chord(),
        music.primitives.ChordName('C7').get_chord(),
        music.primitives.ChordName('F7').get_chord(),
    ]
    audio = reduce(add, (chord.to_audio() for chord in chords))
    assert audio.duration == 3.0


@pytest.mark.parametrize(
    'p1,p2,expected',
    [
        ({'A': 2, 'G': 2}, {'A': 3, 'B': 3}, 3),
        ({'A': 2, 'G': 2, 'B': 3}, {'A': 3, 'B': 3}, 1),
        ({}, {'A': 3, 'B': 3}, 0),
    ]
)
def test_position_motion_distance(p1: dict[Hashable, int], p2: dict[Hashable, int], expected: int) -> None:
    p1_ = music.instruments.GuitarPosition(positions=p1)
    p2_ = music.instruments.GuitarPosition(positions=p2)
    assert p1_.motion_distance(p2_) == expected


@pytest.mark.parametrize(
    'p1,p2,expected',
    [
        ({'A': 2, 'G': 2}, {'A': 3, 'B': 3}, 3),
        # Here, we move from second finger on the G string to the B string
        ({'A': 2, 'G': 2, 'B': 3}, {'A': 3, 'B': 3}, 3),
        ({}, {'A': 3, 'B': 3}, 0),
        # # For barre chord, index only costs 1
        ({'A': 2, 'D': 4, 'G': 2, 'B': 4, 'e': 2}, {'A': 3, 'D': 5, 'G': 3, 'B': 5, 'e': 3}, 3),
    ]
)
def test_position_motion_distance_respect_fingers(
        p1: dict[Hashable, int], p2: dict[Hashable, int], expected: int
) -> None:
    p1_ = music.instruments.GuitarPosition(positions=p1)
    p2_ = music.instruments.GuitarPosition(positions=p2)
    assert p1_.motion_distance(p2_, respect_fingers=True) == expected


@pytest.mark.parametrize('respect_fingers', [True, False])
@pytest.mark.parametrize(
    'prog', [
        ['Dm7', 'G7', 'CM7'],
        ['Dm7', 'G7b9', 'C'],
        ['Dm7#13', 'G7', 'C'],
        ['Em7', 'A7', 'Dm7', 'G7', 'CM7'],
    ]
)
def test_optimal_progression(prog: list[str], respect_fingers: bool) -> None:
    cp = music.primitives.ChordProgression([music.primitives.ChordName(n) for n in prog])
    actual = cp.optimal_guitar_positions(respect_fingers=respect_fingers)
    assert  len(actual) == len(prog)


@pytest.mark.parametrize(
    'positions,expected',
    [
        (
            {'A': 3, 'D': 2, 'G': 0, 'B': 1, 'e': 0},
            {'A': '3', 'D': '2', 'B': '1'}
        ),
        (
            {'E': 0, 'A': 2, 'D': 2, 'G': 1, 'B': 0, 'e': 0},
            {'A': '2', 'D': '3', 'G': '1'}
        ),
        (
            {'E': 3, 'A': 2, 'D': 0, 'G': 0, 'B': 3, 'e': 3},
            {'E': '2', 'A': '1', 'B': '3', 'e': '4'},
        ),
        (
            {'E': 3, 'D': 3, 'G': 4, 'B': 3, 'e': 4},
            {'E': 'T', 'D': '1', 'G': '3', 'B': '2', 'e': '4'},
        ),
        (
            {'E': 3, 'A': 5, 'D': 5, 'G': 4, 'B': 3, 'e': 3},
            {'E': '1', 'A': '3', 'D': '4', 'G': '2', 'B': '1', 'e': '1'},
        ),
    ]
)
def test_fingers_dict(positions: dict[Hashable, int], expected: dict[Hashable, str]) -> None:
    assert music.instruments.GuitarPosition(positions).fingers_dict == expected


@pytest.mark.parametrize(
    'positions,expected',
    [
        ({'A': 2, 'D': 4}, {'A': '1', 'D': '3'}),
        ({'A': 2, 'D': 5}, {'A': '1', 'D': '4'}),
        ({'A': 2, 'D': 5, 'G': 2}, {'A': '1', 'D': '4', 'G': '2'}),
    ]
)
def test_finger_skips(positions: dict[Hashable, int], expected: dict[Hashable, str]) -> None:
    position = music.instruments.GuitarPosition(positions=positions)
    assert position.fingers_dict == expected


@pytest.mark.parametrize(
    'positions',
    [{'E': 8, 'A': 7, 'D': 9, 'G': 0, 'B': 8, 'e': 7}]
)
def check_unplayable_positions(positions: dict[Hashable, int]) -> None:
    assert not music.instruments.GuitarPosition(positions=positions).playable
