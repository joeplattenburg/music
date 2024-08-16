import pytest

import notes


@pytest.mark.parametrize(
    'semitones,bias,expected',
    [
        (0, 'b', notes.Note('C', 0)),
        (12, 'b', notes.Note('C', 1)),
        (39, 'b', notes.Note('Eb', 3)),
        (39, '#', notes.Note('D#', 3)),
    ]
)
def test_note_from_semitones(semitones: int, bias: str, expected: notes.Note) -> None:
    actual = notes.Note.from_semitones(semitones=semitones, bias=bias)
    assert actual == expected


def test_add_and_subtract() -> None:
    assert notes.Note('C', 0) + notes.Note('G', 1) == notes.Note('G', 1)
    assert notes.Note('C', 1) + notes.Note('G', 1) == notes.Note('G', 2)
    assert notes.Note('D', 0) + notes.Note('G', 1) == notes.Note('A', 1)
    assert notes.Note('C', 0) - notes.Note('C', 0) == 0
    assert notes.Note('C', 1) - notes.Note('C', 0) == 12
    assert notes.Note('G', 0) - notes.Note('C', 0) == 7


@pytest.mark.parametrize(
    'name,expected',
    [
        ('C0', notes.Note('C', 0)),
        ('C1', notes.Note('C', 1)),
        ('Eb3', notes.Note('Eb', 3)),
        ('Ebb3', notes.Note('Ebb', 3)),
    ]
)
def test_note_from_string(name: str, expected: notes.Note) -> None:
    actual = notes.Note.from_string(note=name)
    assert actual == expected


@pytest.mark.parametrize(
    'semitones,expected',
    [
        (0, notes.Note('C', 3)),
        (12, notes.Note('C', 4)),
        (8, notes.Note('Ab', 3)),
    ]
)
def test_add_semitones(semitones: int, expected: notes.Note) -> None:
    actual = notes.Note('C', 3).add_semitones(semitones)
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
    assert notes.Note(*self).same_name(notes.Note(*other))


def test_positions_found_with_lower_notes_on_higher_strings() -> None:
    chord = notes.Chord([
        notes.Note('A', 2), notes.Note('C#', 3)
    ])
    expected = [
        {'E': 9, 'A': 0},
        {'E': 5, 'A': 4},
    ]
    actual = [p.positions_dict for p in chord.guitar_positions()]
    assert actual == expected


@pytest.mark.parametrize(
    'frets,expected',
    [
        (10, {'E': 8, 'A': 3}),
        (5, {'A': 3})
    ]
)
def test_guitar_with_different_fret_count(frets: int, expected: dict[str, int]) -> None:
    guitar = notes.Guitar(frets=frets)
    note = notes.Note('C', 3)
    actual = note.guitar_positions(guitar).positions_dict
    assert actual == expected


@pytest.mark.parametrize(
    'strings',
    [
        [('E', 2), ('A', 2), ('D', 3), ('G', 3), ('B', 3), ('E', 4)],
        [('D', 2), ('A', 2), ('D', 3), ('G', 3), ('A', 3), ('D', 4)],
        [('B', 1), ('E', 2), ('A', 2), ('D', 3), ('G', 3), ('B', 3), ('E', 4), ('A', 4)],
    ]
)
@pytest.mark.parametrize('capo', [0, 2, 10])
def test_different_guitar_tunings(strings: list[tuple[str, int]], capo: int) -> None:
    guitar = notes.Guitar(
        tuning={i: notes.Note(*string) for i, string in enumerate(strings)},
        capo=capo
    )
    chord = notes.Chord([notes.Note(*string).add_semitones(capo) for string in strings])
    expected = {i: 0 for i in range(len(strings))}
    actual = chord.guitar_positions(guitar=guitar)[0].positions_dict
    assert actual == expected


@pytest.mark.parametrize(
    'position,expected',
    [
        ({"E": 3, "e": 3}, 4),
        ({"E": 3, "D": 1, "e": 3}, 2),
        ({"E": 3, "D": 1, "b": 0, "e": 3}, 2),
        ({"E": 3, "D": 1}, 1),
        ({"E": 3, "A": 2, "D": 1}, 0),
    ]
)
def test_guitar_position_gaps(position: dict, expected: int) -> None:
    assert notes.GuitarPosition(position).max_interior_gap == expected


def test_sort_guitar_positions() -> None:
    positions = [
        notes.GuitarPosition({"E": 5, "G": 5}),
        notes.GuitarPosition({"E": 1, "A": 5}),
        notes.GuitarPosition({"E": 7, "A": 7}),
        notes.GuitarPosition({"E": 7, "G": 7}),
    ]
    expected = [
        notes.GuitarPosition({"E": 7, "A": 7}),
        notes.GuitarPosition({"E": 7, "G": 7}),
        notes.GuitarPosition({"E": 5, "G": 5}),
        notes.GuitarPosition({"E": 1, "A": 5}),
    ]
    actual = notes.sort_guitar_positions(positions)
    assert actual == expected


def test_guitar_extremes() -> None:
    guitar = notes.Guitar(
        tuning={'E': notes.Note('E', 2), 'A': notes.Note('A', 2)},
        frets=3
    )
    assert guitar.lowest == notes.Note('E', 2)
    assert guitar.highest == notes.Note('C', 3)


def test_validity_of_high_frets_with_capo() -> None:
    guitar = notes.Guitar(frets=5, capo=4)
    assert notes.Note('A', 2).guitar_positions(guitar, valid_only=True).positions_dict == {'E': 1}
    assert notes.Note('A#', 2).guitar_positions(guitar, valid_only=True).positions_dict == {}


def test_print() -> None:
    position = notes.GuitarPosition({'A': 2, 'D': 2})
    expected = [
        "e x|---|",
        "B x|---|",
        "G x|---|",
        "D  |-@-|",
        "A  |-@-|",
        "E x|---|",
        "  1fr",
    ]
    actual = position.printable()
    assert actual == expected


def test_print_more_complex() -> None:
    open_d = {"D": "D2", "A": "A2", "d": "D3", "F#": "F#3", "a": "A3", "dd": "D4"}
    guitar = notes.Guitar(tuning={
        string: notes.Note.from_string(note) for string, note in open_d.items()
    })
    position = notes.GuitarPosition({'A': 2, 'd': 2, 'F#': 3, 'a': 4, 'dd': 0}, guitar=guitar)

    expected = [
        "dd o|---|---|---|",
        " a  |---|---|-@-|",
        "F#  |---|-@-|---|",
        " d  |-@-|---|---|",
        " A  |-@-|---|---|",
        " D x|---|---|---|",
        "   1fr",
    ]
    actual = position.printable()
    assert actual == expected


@pytest.mark.parametrize(
    'string',
    [
        '{"E": "E2", "A": "A2"}',
        "{'E': 'E2', 'A': 'A2'}",
        str({"E": str(notes.Note('E', 2)), "A": str(notes.Note('A', 2))}),
    ]
)
def test_parse_tuning(string: str) -> None:
    expected = {
        "E": notes.Note('E', 2),
        "A": notes.Note('A', 2)
    }
    assert notes.Guitar.parse_tuning(string) == expected


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
    chord_name = notes.ChordName(name)
    assert chord_name.root == expected['root']
    assert chord_name.chord_note == expected['chord_note']
    assert chord_name.quality == expected['quality']
    assert chord_name.note_names + chord_name.extension_names == expected['notes']
    assert chord_name.extensions == expected.get('extensions', [])


def test_chord_name_error() -> None:
    with pytest.raises(ValueError):
        notes.ChordName('Hb7')


@pytest.mark.parametrize(
    'name,expected',
    [
        ('C', [('C', 0), ('E', 0), ('G', 0)]),
        ('C7', [('C', 0), ('E', 0), ('G', 0), ('Bb', 0)]),
        ('Bbmaj7/D', [('D', 0), ('F', 0), ('A', 0), ('Bb', 0)]),
    ]
)
def test_chord_name_to_chord(name: str, expected: list) -> None:
    chord_name = notes.ChordName(name)
    expected = notes.Chord([notes.Note(*n) for n in expected])
    actual = chord_name.get_chord()
    assert actual == expected


def test_chord_name_to_chord_different_lower() -> None:
    actual = notes.ChordName('C').get_chord(lower=notes.Note('E', 2))
    expected = notes.Chord([
        notes.Note('C', 3),
        notes.Note('E', 3),
        notes.Note('G', 3),
    ])
    assert actual == expected


@pytest.mark.parametrize(
    'raise_octave,expected',
    [
        ({}, [notes.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('Bb', 0)]]),
        ({'C': 0, 'G': 0}, [notes.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('Bb', 0)]]),
        ({'C': 1}, [notes.Note(*note) for note in [('C', 1), ('E', 1), ('G', 1), ('Bb', 1)]]),
        ({'C': 1, 'G': 2}, [notes.Note(*note) for note in [('C', 1), ('E', 1), ('Bb', 1), ('G', 3)]]),
    ]
)
def test_get_chord_with_add_octave(raise_octave: dict[str, int], expected: list[notes.Note]) -> None:
    chord = notes.ChordName('C7').get_chord(raise_octave=raise_octave)
    assert chord.notes == expected


def test_get_all_chords() -> None:
    actual = notes.ChordName('C').get_all_chords(
        lower=notes.Note('C', 0), upper=notes.Note('E', 2)
    )
    expected = [
        notes.Chord([notes.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0)]]),
        notes.Chord([notes.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0)]]),
        notes.Chord([notes.Note(*note) for note in [('C', 0), ('E', 0), ('G', 1)]]),
        notes.Chord([notes.Note(*note) for note in [('C', 0), ('E', 1), ('G', 1)]]),
        notes.Chord([notes.Note(*note) for note in [('C', 0), ('E', 2), ('G', 0)]]),
        notes.Chord([notes.Note(*note) for note in [('C', 0), ('E', 2), ('G', 1)]]),
        notes.Chord([notes.Note(*note) for note in [('C', 1), ('E', 1), ('G', 1)]]),
        notes.Chord([notes.Note(*note) for note in [('C', 1), ('E', 2), ('G', 1)]]),
    ]
    assert sorted(expected, key=str) == sorted(actual, key=str)

def test_get_all_chords_extension() -> None:
    actual = notes.ChordName('C9').get_all_chords(
        lower=notes.Note('C', 0), upper=notes.Note('E', 2)
    )
    expected = [
        notes.Chord([notes.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('D', 1)]]),
        notes.Chord([notes.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('D', 2)]]),
        notes.Chord([notes.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0), ('D', 2)]]),
        notes.Chord([notes.Note(*note) for note in [('C', 0), ('E', 0), ('G', 1), ('D', 2)]]),
        notes.Chord([notes.Note(*note) for note in [('C', 0), ('E', 1), ('G', 1), ('D', 2)]]),
        notes.Chord([notes.Note(*note) for note in [('C', 1), ('E', 1), ('G', 1), ('D', 2)]]),
    ]
    assert sorted(expected, key=str) == sorted(actual, key=str)

@pytest.mark.parametrize(
    'note,other,allow_equal,octave',
    [
        (notes.Note('C', 3), 'E', True, 3),
        (notes.Note('C', 3), 'C', True, 3),
        (notes.Note('C', 3), 'C', False, 4),
        (notes.Note('G', 3), 'D', True, 4),
    ]
)
def test_nearest_above(note: notes.Note, other: str, allow_equal: bool, octave: int) -> None:
    expected = notes.Note(other, octave)
    actual = note.nearest_above(other, allow_equal=allow_equal)
    assert actual == expected


@pytest.mark.parametrize(
    'note,other,allow_equal,octave',
    [
        (notes.Note('C', 3), 'E', True, 2),
        (notes.Note('C', 3), 'C', True, 3),
        (notes.Note('C', 3), 'C', False, 2),
        (notes.Note('G', 3), 'D', True, 3),
    ]
)
def test_nearest_above(note: notes.Note, other: str, allow_equal: bool, octave: int) -> None:
    expected = notes.Note(other, octave)
    actual = note.nearest_below(other, allow_equal=allow_equal)
    assert actual == expected


@pytest.mark.parametrize(
    'l,n,expected',
    [
        ([1, 2, 3, 4], 0, [1, 2, 3, 4]),
        ([1, 2, 3, 4], 1, [2, 3, 4, 1]),
        ([1, 2, 3, 4], 3, [4, 1, 2, 3]),
        ([1, 2, 3, 4], 5, None),
    ]
)
def test_rotate_list(l: list[int], n: int, expected: list[int]) -> None:

    if expected is None:
        with pytest.raises(ValueError):
            notes._rotate_list(l, n)
    else:
        actual = notes._rotate_list(l, n)
        assert actual == expected


def test_best_match() -> None:
    s = 'hello there'
    choices = ['h', 'hi', 'hello', 'hello bob']
    assert notes.best_match(s, choices) == 'hello'
    with pytest.raises(ValueError):
        notes.best_match(s, [choices[1], choices[3]])
