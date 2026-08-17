from typing import Literal

import pytest

from music import primitives


@pytest.mark.parametrize(
    'semitones,bias,expected',
    [
        (0, 'b', primitives.Note('C', 0)),
        (12, 'b', primitives.Note('C', 1)),
        (39, 'b', primitives.Note('Eb', 3)),
        (39, '#', primitives.Note('D#', 3)),
    ]
)
def test_note_from_semitones(semitones: int, bias: Literal['b', '#'], expected: primitives.Note) -> None:
    actual = primitives.Note.from_semitones(semitones=semitones, bias=bias)
    assert actual == expected


def test_add_and_subtract() -> None:
    assert primitives.Note('C', 0) + primitives.Note('G', 1) == primitives.Note('G', 1)
    assert primitives.Note('C', 1) + primitives.Note('G', 1) == primitives.Note('G', 2)
    assert primitives.Note('D', 0) + primitives.Note('G', 1) == primitives.Note('A', 1)
    assert primitives.Note('C', 0) - primitives.Note('C', 0) == 0
    assert primitives.Note('C', 1) - primitives.Note('C', 0) == 12
    assert primitives.Note('G', 0) - primitives.Note('C', 0) == 7


@pytest.mark.parametrize(
    'name,expected',
    [
        ('C0', primitives.Note('C', 0)),
        ('C1', primitives.Note('C', 1)),
        ('Eb3', primitives.Note('Eb', 3)),
        ('Ebb3', primitives.Note('Ebb', 3)),
    ]
)
def test_note_from_string(name: str, expected: primitives.Note) -> None:
    actual = primitives.Note.from_string(note=name)
    assert actual == expected


@pytest.mark.parametrize(
    'semitones,expected',
    [
        (0, primitives.Note('C', 3)),
        (12, primitives.Note('C', 4)),
        (8, primitives.Note('Ab', 3)),
    ]
)
def test_add_semitones(semitones: int, expected: primitives.Note) -> None:
    actual = primitives.Note('C', 3).add_semitones(semitones)
    assert actual == expected


@pytest.mark.parametrize(
    'self,other',
    [
        (('C', 0), ('C', 0)),
        (('C', 0), ('C', 1)),
        (('C', 10), ('C', -3)),
        (('F#', 0), ('Gb', 0)),
        (('F#', 0), ('Gb', 3)),
        (('C##', 3), ('D', 0)),
    ]
)
def test_same_name(self, other) -> None:
    assert primitives.Note(*self).same_name(primitives.Note(*other))


@pytest.mark.parametrize(
    'name,expected',
    [
        # TODO: this gets some enharmonics wrong, but it shouldn't double count the root note at least
        # all qualities
        ('C', {'chord_note': 'C', 'root': 'C', 'quality': '', 'notes': ['C', 'E', 'G']}),
        ('Cmaj', {'chord_note': 'C', 'root': 'C', 'quality': 'maj', 'notes': ['C', 'E', 'G']}),
        ('Cm', {'chord_note': 'C', 'root': 'C', 'quality': 'm', 'notes': ['C', 'Eb', 'G']}),
        ('Cmin', {'chord_note': 'C', 'root': 'C', 'quality': 'min', 'notes': ['C', 'Eb', 'G']}),
        ('Cdim', {'chord_note': 'C', 'root': 'C', 'quality': 'dim', 'notes': ['C', 'Eb', 'Gb']}),
        ('Caug', {'chord_note': 'C', 'root': 'C', 'quality': 'aug', 'notes': ['C', 'E', 'Ab']}),
        ('Csus2', {'chord_note': 'C', 'root': 'C', 'quality': 'sus2', 'notes': ['C', 'D', 'G']}),
        ('Csus4', {'chord_note': 'C', 'root': 'C', 'quality': 'sus4', 'notes': ['C', 'F', 'G']}),
        ('Cmaj7', {'chord_note': 'C', 'root': 'C', 'quality': 'maj7', 'notes': ['C', 'E', 'G', 'B']}),
        ('C7', {'chord_note': 'C', 'root': 'C', 'quality': '7', 'notes': ['C', 'E', 'G', 'Bb']}),
        ('Cm7', {'chord_note': 'C', 'root': 'C', 'quality': 'm7', 'notes': ['C', 'Eb', 'G', 'Bb']}),
        ('Cm7b5', {'chord_note': 'C', 'root': 'C', 'quality': 'm7b5', 'notes': ['C', 'Eb', 'Gb', 'Bb']}),
        ('Cdim7', {'chord_note': 'C', 'root': 'C', 'quality': 'dim7', 'notes': ['C', 'Eb', 'Gb', 'A']}),
        ('Caug7', {'chord_note': 'C', 'root': 'C', 'quality': 'aug7', 'notes': ['C', 'E', 'Ab', 'Bb']}),
        ('C6', {'chord_note': 'C', 'root': 'C', 'quality': '6', 'notes': ['C', 'E', 'G', 'A']}),
        # other keys
        ('F#', {'chord_note': 'F#', 'root': 'F#', 'quality': '', 'notes': ['F#', 'A#', 'C#']}),
        ('F#m7b5', {'chord_note': 'F#', 'root': 'F#', 'quality': 'm7b5', 'notes': ['F#', 'A', 'C', 'E']}),
        # inversions
        ('Bbmaj7/D', {'chord_note': 'Bb', 'root': 'D', 'quality': 'maj7', 'notes': ['D', 'F', 'A', 'Bb']}),
        ('F#m7b5/E', {'chord_note': 'F#', 'root': 'E', 'quality': 'm7b5', 'notes': ['E', 'F#', 'A', 'C']}),
        ('C/D', {'chord_note': 'C', 'root': 'D', 'quality': '', 'notes': ['D', 'C', 'E', 'G']}),
        ('C/C', {'chord_note': 'C', 'root': 'C', 'quality': '', 'notes': ['C', 'E', 'G']}),
        ('Gm/Bb', {'chord_note': 'G', 'root': 'Bb', 'quality': 'm', 'notes': ['A#', 'D', 'G']}),
        ('Gm/A#', {'chord_note': 'G', 'root': 'A#', 'quality': 'm', 'notes': ['A#', 'D', 'G']}),
        # Extensions
        ('C9', {'chord_note': 'C', 'root': 'C', 'quality': '', 'extensions': ['9'], 'notes': ['C', 'E', 'G', 'D']}),
        ('Cm#11', {'chord_note': 'C', 'root': 'C', 'quality': 'm', 'extensions': ['#11'], 'notes': ['C', 'Eb', 'G', 'F#']}),
        ('D7b13/F#', {'chord_note': 'D', 'root': 'F#', 'quality': '7', 'extensions': ['b13'], 'notes': ['F#', 'A', 'C', 'D', 'Bb']}),
    ]
)
def test_chord_name(name: str, expected: dict) -> None:
    chord_name = primitives.ChordName(name)
    assert chord_name.root == expected['root']
    assert chord_name.chord_note == expected['chord_note']
    assert chord_name.quality == expected['quality']
    assert chord_name.note_names + chord_name.extension_names == expected['notes']
    assert chord_name.extensions == expected.get('extensions', [])


def test_chord_name_error() -> None:
    with pytest.raises(ValueError):
        primitives.ChordName('Hb7')


@pytest.mark.parametrize(
    'name,expected',
    [
        ('C', [('C', 0), ('E', 0), ('G', 0)]),
        ('C7', [('C', 0), ('E', 0), ('G', 0), ('Bb', 0)]),
        ('Bbmaj7/D', [('D', 0), ('F', 0), ('A', 0), ('Bb', 0)]),
    ]
)
def test_chord_name_to_chord(name: str, expected: list[tuple[str, int]]) -> None:
    chord_name = primitives.ChordName(name)
    expected_ = primitives.Chord([primitives.Note(*n) for n in expected])
    actual = chord_name.get_chord()
    assert actual == expected_


def test_chord_name_to_chord_different_lower() -> None:
    actual = primitives.ChordName('C').get_chord(lower=primitives.Note('E', 2))
    expected = primitives.Chord([
        primitives.Note('C', 3),
        primitives.Note('E', 3),
        primitives.Note('G', 3),
    ])
    assert actual == expected


@pytest.mark.parametrize(
    'raise_octave,expected',
    [
        ({}, [primitives.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('Bb', 0)]]),
        ({0: 0, 2: 0}, [primitives.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('Bb', 0)]]),
        ({0: 1}, [primitives.Note(*note) for note in [('C', 1), ('E', 1), ('G', 1), ('Bb', 1)]]),
        ({0: 1, 2: 2}, [primitives.Note(*note) for note in [('C', 1), ('E', 1), ('Bb', 1), ('G', 3)]]),
    ]
)
def test_get_chord_with_add_octave(raise_octave: dict[int, int], expected: list[primitives.Note]) -> None:
    chord = primitives.ChordName('C7').get_chord(raise_octave=raise_octave)
    assert chord.notes == expected


def test_get_chord_with_repeats() -> None:
    chord = primitives.ChordName('C')
    chord.note_names += ['E']
    actual = chord.get_chord(raise_octave={3: 1})
    expected = primitives.Chord([
        primitives.Note('C', 0),
        primitives.Note('E', 0),
        primitives.Note('G', 0),
        primitives.Note('E', 1),
    ])
    assert actual == expected


def test_get_all_chords() -> None:
    actual = primitives.ChordName('C').get_all_chords(
        lower=primitives.Note('C', 0), upper=primitives.Note('E', 2)
    )
    expected = [
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 0), ('G', 1)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 1), ('G', 1)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 2), ('G', 0)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 2), ('G', 1)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 1), ('E', 1), ('G', 1)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 1), ('E', 2), ('G', 1)]]),
    ]
    assert sorted(expected, key=str) == sorted(actual, key=str)


def test_get_all_chords_with_repeats() -> None:
    actual = primitives.ChordName('C').get_all_chords(
        lower=primitives.Note('C', 0), upper=primitives.Note('E', 1),
        allow_repeats=True, allow_identical=True, max_notes=4
    )
    expected = [
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('C', 0)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('E', 0)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('G', 0)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('C', 1)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('E', 1)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0), ('C', 0)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0), ('G', 0)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0), ('C', 1)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0), ('E', 1)]]),
    ]
    assert sorted(expected, key=str) == sorted(actual, key=str)


def test_get_all_chords_extension() -> None:
    actual = primitives.ChordName('C9').get_all_chords(
        lower=primitives.Note('C', 0), upper=primitives.Note('E', 2)
    )
    expected = [
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('D', 1)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('D', 2)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0), ('D', 2)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 0), ('G', 1), ('D', 2)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 0), ('E', 1), ('G', 1), ('D', 2)]]),
        primitives.Chord([primitives.Note(*note) for note in [('C', 1), ('E', 1), ('G', 1), ('D', 2)]]),
    ]
    assert sorted(expected, key=str) == sorted(actual, key=str)


@pytest.mark.parametrize(
    'note,other,allow_equal,octave',
    [
        (primitives.Note('C', 3), 'E', True, 3),
        (primitives.Note('C', 3), 'C', True, 3),
        (primitives.Note('C', 3), 'C', False, 4),
        (primitives.Note('G', 3), 'D', True, 4),
    ]
)
def test_nearest_above(note: primitives.Note, other: str, allow_equal: bool, octave: int) -> None:
    expected = primitives.Note(other, octave)
    actual = note.nearest_above(other, allow_equal=allow_equal)
    assert actual == expected


@pytest.mark.parametrize(
    'note,other,allow_equal,octave',
    [
        (primitives.Note('C', 3), 'E', True, 2),
        (primitives.Note('C', 3), 'C', True, 3),
        (primitives.Note('C', 3), 'C', False, 2),
        (primitives.Note('G', 3), 'D', True, 3),
    ]
)
def test_nearest_below(note: primitives.Note, other: str, allow_equal: bool, octave: int) -> None:
    expected = primitives.Note(other, octave)
    actual = note.nearest_below(other, allow_equal=allow_equal)
    assert actual == expected


def test_constrained_powerset_same_len() -> None:
    note_list = [
        primitives.Note('C', 0),
        primitives.Note('E', 0),
        primitives.Note('G', 0),
        primitives.Note('C', 1),
        primitives.Note('E', 1),
        primitives.Note('G', 1),
    ]
    expected = [
        [primitives.Note.from_string(s) for s in ['C0', 'E0', 'G0']],
        [primitives.Note.from_string(s) for s in ['C0', 'E0', 'G1']],
        [primitives.Note.from_string(s) for s in ['C0', 'G0', 'E1']],
        [primitives.Note.from_string(s) for s in ['C0', 'E1', 'G1']],
        [primitives.Note.from_string(s) for s in ['E0', 'G0', 'C1']],
        [primitives.Note.from_string(s) for s in ['E0', 'C1', 'G1']],
        [primitives.Note.from_string(s) for s in ['G0', 'C1', 'E1']],
        [primitives.Note.from_string(s) for s in ['C1', 'E1', 'G1']],
    ]
    actual = sorted(
        [sorted(s) for s in primitives.constrained_powerset(note_list, max_len=3)],
    )
    assert len(actual) == len(expected)
    assert set(''.join(str(x)) for x in actual) == set(''.join(str(x)) for x in expected)


def test_constrained_powerset_different_len() -> None:
    note_list = [
        primitives.Note('C', 0),
        primitives.Note('E', 0),
        primitives.Note('C', 1),
        primitives.Note('E', 1),
    ]
    expected = [
        [primitives.Note.from_string(s) for s in ['C0', 'E0']],
        [primitives.Note.from_string(s) for s in ['C0', 'E1']],
        [primitives.Note.from_string(s) for s in ['E0', 'C1']],
        [primitives.Note.from_string(s) for s in ['C1', 'E1']],
        [primitives.Note.from_string(s) for s in ['C0', 'E0', 'C1']],
        [primitives.Note.from_string(s) for s in ['C0', 'E0', 'E1']],
        [primitives.Note.from_string(s) for s in ['C0', 'C1', 'E1']],
        [primitives.Note.from_string(s) for s in ['E0', 'C1', 'E1']],
    ]
    actual = sorted(
        [sorted(s) for s in primitives.constrained_powerset(note_list, max_len=3)],
    )
    assert len(actual) == len(expected)
    assert set(''.join(str(x)) for x in actual) == set(''.join(str(x)) for x in expected)


def test_constrained_powerset_different_required_notes() -> None:
    note_list = [
        primitives.Note('C', 0),
        primitives.Note('E', 0),
        primitives.Note('G', 0),
        primitives.Note('C', 1),
    ]
    expected = [
        [primitives.Note.from_string(s) for s in ['C0', 'E0']],
        [primitives.Note.from_string(s) for s in ['E0', 'C1']],
        [primitives.Note.from_string(s) for s in ['C0', 'E0', 'C1']],
        [primitives.Note.from_string(s) for s in ['C0', 'E0', 'G0']],
        [primitives.Note.from_string(s) for s in ['E0', 'G0', 'C1']],
    ]
    temp = primitives.constrained_powerset(
        note_list, max_len=3,
        required_notes=primitives.Note.set([primitives.Note('C', 0), primitives.Note('E', 0)])
    )
    actual = [sorted(s) for s in temp]
    print(actual)
    assert len(actual) == len(expected)
    assert set(''.join(str(x)) for x in actual) == set(''.join(str(x)) for x in expected)


def test_constrained_powerset_allow_identical() -> None:
    note_list = [
        primitives.Note('C', 0),
        primitives.Note('E', 0),
        primitives.Note('G', 0),
        primitives.Note('C', 1),
    ]
    expected = [
        [primitives.Note.from_string(s) for s in ['C0', 'E0']],
        [primitives.Note.from_string(s) for s in ['E0', 'C1']],
        [primitives.Note.from_string(s) for s in ['C0', 'C0', 'E0']],
        [primitives.Note.from_string(s) for s in ['C0', 'E0', 'E0']],
        [primitives.Note.from_string(s) for s in ['C0', 'E0', 'C1']],
        [primitives.Note.from_string(s) for s in ['E0', 'E0', 'C1']],
        [primitives.Note.from_string(s) for s in ['E0', 'C1', 'C1']],
        [primitives.Note.from_string(s) for s in ['C0', 'E0', 'G0']],
        [primitives.Note.from_string(s) for s in ['E0', 'G0', 'C1']],
    ]
    temp = primitives.constrained_powerset(
        note_list, max_len=3,
        required_notes=primitives.Note.set([primitives.Note('C', 0), primitives.Note('E', 0)]),
        allow_identical=True
    )
    actual = [sorted(s) for s in temp]
    print(actual)
    assert len(actual) == len(expected)
    assert set(''.join(str(x)) for x in actual) == set(''.join(str(x)) for x in expected)


def test_constrained_powerset_dont_allow_repeats() -> None:
    note_list = [
        primitives.Note('C', 0),
        primitives.Note('E', 0),
        primitives.Note('G', 0),
        primitives.Note('C', 1),
    ]
    expected = [
        [primitives.Note.from_string(s) for s in ['C0', 'E0']],
        [primitives.Note.from_string(s) for s in ['E0', 'C1']],
        [primitives.Note.from_string(s) for s in ['C0', 'E0', 'G0']],
        [primitives.Note.from_string(s) for s in ['E0', 'G0', 'C1']],
    ]
    temp = primitives.constrained_powerset(
        note_list, max_len=3,
        required_notes=primitives.Note.set([primitives.Note('C', 0), primitives.Note('E', 0)]),
        allow_repeats=False
    )
    actual = [sorted(s) for s in temp]
    print(actual)
    assert len(actual) == len(expected)
    assert set(''.join(str(x)) for x in actual) == set(''.join(str(x)) for x in expected)


@pytest.mark.parametrize('max_notes', [3, 4, 5, 6])
def test_get_all_chords_again(max_notes: int) -> None:
    c = primitives.ChordName('C')
    expected = [
        primitives.Chord.from_string('C0,E0,G0'),
        primitives.Chord.from_string('C0,E0,G1'),
        primitives.Chord.from_string('C0,E1,G0'),
        primitives.Chord.from_string('C0,E1,G1'),
        primitives.Chord.from_string('C1,E1,G1'),
    ]
    actual = c.get_all_chords(upper=primitives.Note('G', 1), max_notes=max_notes, allow_repeats=False)
    assert set(actual) == set(expected)


def test_get_all_chords_allow_repeats() -> None:
    c = primitives.ChordName('C')
    expected = [
        primitives.Chord.from_string('C0,E0,G0'),
        primitives.Chord.from_string('C0,E0,G1'),
        primitives.Chord.from_string('C0,E1,G0'),
        primitives.Chord.from_string('C0,E1,G1'),
        primitives.Chord.from_string('C1,E1,G1'),
        primitives.Chord.from_string('C0,E0,G0,C1'),
        primitives.Chord.from_string('C0,E0,G1,C1'),
        primitives.Chord.from_string('C0,E1,G0,C1'),
        primitives.Chord.from_string('C0,E1,G1,C1'),
        primitives.Chord.from_string('C0,E0,G0,E1'),
        primitives.Chord.from_string('C0,E0,G1,E1'),
        primitives.Chord.from_string('C0,E1,G0,G1'),
        primitives.Chord.from_string('C0,E0,G0,G1'),
    ]
    actual = c.get_all_chords(upper=primitives.Note('G', 1), max_notes=4, allow_repeats=True)
    assert set(actual) == set(expected)


def test_get_all_chords_allow_identical() -> None:
    c = primitives.ChordName('C')
    expected = [
        primitives.Chord.from_string('C0,E0,G0'),
        primitives.Chord.from_string('C0,E0,G1'),
        primitives.Chord.from_string('C0,E1,G0'),
        primitives.Chord.from_string('C0,E1,G1'),
        primitives.Chord.from_string('C1,E1,G1'),

        primitives.Chord.from_string('C0,E0,G0,C1'),
        primitives.Chord.from_string('C0,E0,G1,C1'),
        primitives.Chord.from_string('C0,E1,G0,C1'),
        primitives.Chord.from_string('C0,E1,G1,C1'),
        primitives.Chord.from_string('C0,E0,G0,E1'),
        primitives.Chord.from_string('C0,E0,G1,E1'),
        primitives.Chord.from_string('C0,E1,G0,G1'),
        primitives.Chord.from_string('C0,E0,G0,G1'),

        primitives.Chord.from_string('C0,E0,G0,C0'),
        primitives.Chord.from_string('C0,E0,G1,C0'),
        primitives.Chord.from_string('C0,E1,G0,C0'),
        primitives.Chord.from_string('C0,E1,G1,C0'),
        primitives.Chord.from_string('C0,E0,G0,E0'),
        primitives.Chord.from_string('C0,E0,G1,E0'),
        primitives.Chord.from_string('C0,E1,G0,G0'),
        primitives.Chord.from_string('C0,E0,G0,G0'),
        primitives.Chord.from_string('C0,E1,G1,G1'),
        primitives.Chord.from_string('C1,C1,E1,G1'),
        primitives.Chord.from_string('C0,E0,G1,G1'),
        primitives.Chord.from_string('C1,E1,E1,G1'),
        primitives.Chord.from_string('C0,E1,E1,G1'),
        primitives.Chord.from_string('C0,G0,E1,E1'),
        primitives.Chord.from_string('C1,E1,G1,G1'),
    ]
    actual = c.get_all_chords(
        upper=primitives.Note('G', 1), max_notes=4,
        allow_repeats=True, allow_identical=True
    )
    assert set(actual) == set(expected)


def test_get_all_chords_extension_again() -> None:
    c = primitives.ChordName('Cmaj79')
    expected = [
        primitives.Chord.from_string('C0,E0,G0,B0,D1'),
        primitives.Chord.from_string('C0,E0,G0,B0,C1,D1'),
    ]
    actual = c.get_all_chords(
        upper=primitives.Note('C', 2), max_notes=6,
        allow_repeats=True, allow_identical=False
    )
    assert set(actual) == set(expected)


def test_parse_all_chord_names() -> None:
    for name in primitives.ChordName.ALL_CHORD_NAMES:
        primitives.ChordName(name)


@pytest.mark.parametrize('name,frequency', [('A4', 440.), ('A3', 220.), ('C4', 261.626)])
def test_frequency(name: str, frequency: float) -> None:
    assert primitives.Note.from_string(name).frequency == pytest.approx(frequency, rel=1e-3)


def test_chord_comparison() -> None:
    assert primitives.Chord([primitives.Note('C', 0)]) == primitives.Chord([primitives.Note('C', 0)])
    assert primitives.Chord([primitives.Note('C', 0)]) < primitives.Chord([primitives.Note('D', 0)])
    assert primitives.Chord([primitives.Note('C', 0)]) < primitives.Chord([primitives.Note('C', 0), primitives.Note('D', 1)])
    assert primitives.Chord([primitives.Note('C', 0), primitives.Note('D', 1)]) < primitives.Chord([
                                                                                                                               primitives.Note('C', 0), primitives.Note('E', 1)])


def test_semitone_distance() -> None:
    c1 = primitives.Chord([
        primitives.Note('C', 3),
        primitives.Note('Eb', 3),
        primitives.Note('F', 3),
        primitives.Note('A', 3)
    ])
    c2 = primitives.Chord([
        primitives.Note('C', 3),
        primitives.Note('E', 3),
        primitives.Note('G', 3),
        primitives.Note('Bb', 3),
    ])
    assert c1.semitone_distance(c2) == 4
    assert c2.semitone_distance(c1) == 4


def test_semitone_distance_different_cardinality() -> None:
    c1 = primitives.Chord([
        primitives.Note('C', 3),
        primitives.Note('F', 3),
        primitives.Note('A', 3)
    ])
    c2 = primitives.Chord([
        primitives.Note('C', 3),
        primitives.Note('E', 3),
        primitives.Note('G', 3),
        primitives.Note('Bb', 3),
    ])
    assert c1.semitone_distance(c2) == 4
    assert c2.semitone_distance(c1) == 4


def test_voice_leading() -> None:
    cp = primitives.ChordProgression([
        primitives.ChordName(n) for n in ['Em7', 'A7', 'Dm7', 'G7', 'CM7']]
    )
    result1 = cp.optimal_voice_leading(
        lower=primitives.Note('C', 2),
        upper=primitives.Note('C', 4),
        use_dijkstra=True
    )
    result2 = cp.optimal_voice_leading(
        lower=primitives.Note('C', 2),
        upper=primitives.Note('C', 4),
        use_dijkstra=False
    )
    assert result1 == result2


def test_note_event() -> None:
    event = primitives.NoteEvent(notes=[primitives.Note('C', 3)], duration_beats=0.25)


def test_note_sequence() -> None:
    sequence = primitives.NoteSequence(
        events=[
            primitives.NoteEvent(notes=[primitives.Note('C', 3)], duration_beats=0.25, offset_beats=0.),
            primitives.NoteEvent(notes=[primitives.Note('D', 3)], duration_beats=0.25, offset_beats=0.25),
            primitives.NoteEvent(notes=[primitives.Note('E', 3)], duration_beats=0.25, offset_beats=0.25),
            primitives.NoteEvent(notes=[primitives.Note('F', 3)], duration_beats=0.25, offset_beats=0.5),
        ],
        volume_control_points=[
            primitives.ControlPoint(level=1., beat=0., mode='step'),
            primitives.ControlPoint(level=0.5, beat=0.25, mode='step'),
            primitives.ControlPoint(level=0.75, beat=0.5, mode='step'),
        ]
    )
