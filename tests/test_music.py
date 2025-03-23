from functools import reduce
from operator import add
import os

import pytest

from music import music


@pytest.mark.parametrize(
    'semitones,bias,expected',
    [
        (0, 'b', music.Note('C', 0)),
        (12, 'b', music.Note('C', 1)),
        (39, 'b', music.Note('Eb', 3)),
        (39, '#', music.Note('D#', 3)),
    ]
)
def test_note_from_semitones(semitones: int, bias: str, expected: music.Note) -> None:
    actual = music.Note.from_semitones(semitones=semitones, bias=bias)
    assert actual == expected


def test_add_and_subtract() -> None:
    assert music.Note('C', 0) + music.Note('G', 1) == music.Note('G', 1)
    assert music.Note('C', 1) + music.Note('G', 1) == music.Note('G', 2)
    assert music.Note('D', 0) + music.Note('G', 1) == music.Note('A', 1)
    assert music.Note('C', 0) - music.Note('C', 0) == 0
    assert music.Note('C', 1) - music.Note('C', 0) == 12
    assert music.Note('G', 0) - music.Note('C', 0) == 7


@pytest.mark.parametrize(
    'name,expected',
    [
        ('C0', music.Note('C', 0)),
        ('C1', music.Note('C', 1)),
        ('Eb3', music.Note('Eb', 3)),
        ('Ebb3', music.Note('Ebb', 3)),
    ]
)
def test_note_from_string(name: str, expected: music.Note) -> None:
    actual = music.Note.from_string(note=name)
    assert actual == expected


@pytest.mark.parametrize(
    'semitones,expected',
    [
        (0, music.Note('C', 3)),
        (12, music.Note('C', 4)),
        (8, music.Note('Ab', 3)),
    ]
)
def test_add_semitones(semitones: int, expected: music.Note) -> None:
    actual = music.Note('C', 3).add_semitones(semitones)
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
    assert music.Note(*self).same_name(music.Note(*other))


def test_positions_found_with_lower_notes_on_higher_strings() -> None:
    chord = music.Chord([
        music.Note('A', 2), music.Note('C#', 3)
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
    guitar = music.Guitar(frets=frets)
    note = music.Note('C', 3)
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
    guitar = music.Guitar(
        tuning={i: music.Note(*string) for i, string in enumerate(strings)},
        capo=capo
    )
    chord = music.Chord([music.Note(*string).add_semitones(capo) for string in strings])
    expected = {i: 0 for i in range(len(strings))}
    actual = chord.guitar_positions(guitar=guitar, include_unplayable=True)[0].positions_dict
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
    assert music.GuitarPosition(position).max_interior_gap == expected


def test_sort_guitar_positions() -> None:
    positions = [
        music.GuitarPosition({"E": 5, "G": 5}),
        music.GuitarPosition({"E": 1, "A": 5}),
        music.GuitarPosition({"E": 7, "A": 7}),
        music.GuitarPosition({"E": 7, "G": 7}),
    ]
    expected = [
        music.GuitarPosition({"E": 7, "A": 7}),
        music.GuitarPosition({"E": 7, "G": 7}),
        music.GuitarPosition({"E": 5, "G": 5}),
        music.GuitarPosition({"E": 1, "A": 5}),
    ]
    actual = music.GuitarPosition.sorted(positions)
    assert actual == expected


def test_redundant_position() -> None:
    assert music.GuitarPosition({'E': 12, 'A': 13, 'b': 14}).redundant
    assert music.GuitarPosition({'E': 12, 'A': 0, 'b': 14}).redundant
    assert not music.GuitarPosition({'E': 11, 'A': 0, 'b': 14}).redundant


def test_guitar_extremes() -> None:
    guitar = music.Guitar(
        tuning={'E': music.Note('E', 2), 'A': music.Note('A', 2)},
        frets=3
    )
    assert guitar.lowest == music.Note('E', 2)
    assert guitar.highest == music.Note('C', 3)


def test_validity_of_high_frets_with_capo() -> None:
    guitar = music.Guitar(frets=5, capo=4)
    assert music.Note('A', 2).guitar_positions(guitar, valid_only=True).positions_dict == {'E': 1}
    assert music.Note('A#', 2).guitar_positions(guitar, valid_only=True).positions_dict == {}


def test_print() -> None:
    position = music.GuitarPosition({'A': 2, 'D': 2})
    expected = [
        "e x|---|",
        "B x|---|",
        "G x|---|",
        "D  |-@-|",
        "A  |-@-|",
        "E x|---|",
        "    2fr",
    ]
    actual = position.printable()
    assert actual == expected


def test_print_more_complex() -> None:
    open_d = {"D": "D2", "A": "A2", "d": "D3", "F#": "F#3", "a": "A3", "dd": "D4"}
    guitar = music.Guitar(tuning={
        string: music.Note.from_string(note) for string, note in open_d.items()
    })
    position = music.GuitarPosition({'A': 2, 'd': 2, 'F#': 3, 'a': 4, 'dd': 0}, guitar=guitar)

    expected = [
        "dd o|---|---|---|",
        " a  |---|---|-@-|",
        "F#  |---|-@-|---|",
        " d  |-@-|---|---|",
        " A  |-@-|---|---|",
        " D x|---|---|---|",
        "     2fr",
    ]
    actual = position.printable()
    assert actual == expected


def test_print_barre() -> None:
    # G
    position = music.GuitarPosition({'E': 3, 'A': 5, 'D': 5, 'G': 4, 'B': 3, 'e': 3})
    assert position.barre
    expected = [
        "e  |-@-|---|---|",
        "B  |-|-|---|---|",
        "G  |-|-|-@-|---|",
        "D  |-|-|---|-@-|",
        "A  |-|-|---|-@-|",
        "E  |-@-|---|---|",
        "    3fr",
    ]
    actual = position.printable()
    assert actual == expected
    # G7
    position = music.GuitarPosition({'A': 10, 'D': 12, 'G': 10, 'B': 12, 'e': 10})
    assert position.barre
    expected = [
        "e  |-@-|---|---|",
        "B  |-|-|---|-@-|",
        "G  |-|-|---|---|",
        "D  |-|-|---|-@-|",
        "A  |-@-|---|---|",
        "E x|---|---|---|",
        "    10fr",
    ]
    actual = position.printable()
    assert actual == expected


def test_no_open_strings_along_barre() -> None:
    position = music.GuitarPosition({"E": 3, "D": 5, "G": 7, "B": 3, "e": 7})
    assert not position.barre
    expected = [
        "e  |---|---|---|---|-@-|",
        "B  |-@-|---|---|---|---|",
        "G  |---|---|---|---|-@-|",
        "D  |---|---|-@-|---|---|",
        "A x|---|---|---|---|---|",
        "E  |-T-|---|---|---|---|",
        "    3fr",
    ]
    assert position.printable() == expected
    position = music.GuitarPosition({"E": 3, "A": 0, "D": 5, "G": 7, "B": 3, "e": 7})
    assert not position.barre
    expected = [
        "e  |---|---|---|---|-@-|",
        "B  |-@-|---|---|---|---|",
        "G  |---|---|---|---|-@-|",
        "D  |---|---|-@-|---|---|",
        "A o|---|---|---|---|---|",
        "E  |-T-|---|---|---|---|",
        "    3fr",
    ]
    assert position.printable() == expected

@pytest.mark.parametrize(
    'string',
    [
        '{"E": "E2", "A": "A2"}',
        "{'E': 'E2', 'A': 'A2'}",
        str({"E": str(music.Note('E', 2)), "A": str(music.Note('A', 2))}),
    ]
)
def test_parse_tuning(string: str) -> None:
    expected = {
        "E": music.Note('E', 2),
        "A": music.Note('A', 2)
    }
    assert music.Guitar.parse_tuning(string) == expected


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
    chord_name = music.ChordName(name)
    assert chord_name.root == expected['root']
    assert chord_name.chord_note == expected['chord_note']
    assert chord_name.quality == expected['quality']
    assert chord_name.note_names + chord_name.extension_names == expected['notes']
    assert chord_name.extensions == expected.get('extensions', [])


def test_chord_name_error() -> None:
    with pytest.raises(ValueError):
        music.ChordName('Hb7')


@pytest.mark.parametrize(
    'name,expected',
    [
        ('C', [('C', 0), ('E', 0), ('G', 0)]),
        ('C7', [('C', 0), ('E', 0), ('G', 0), ('Bb', 0)]),
        ('Bbmaj7/D', [('D', 0), ('F', 0), ('A', 0), ('Bb', 0)]),
    ]
)
def test_chord_name_to_chord(name: str, expected: list) -> None:
    chord_name = music.ChordName(name)
    expected = music.Chord([music.Note(*n) for n in expected])
    actual = chord_name.get_chord()
    assert actual == expected


def test_chord_name_to_chord_different_lower() -> None:
    actual = music.ChordName('C').get_chord(lower=music.Note('E', 2))
    expected = music.Chord([
        music.Note('C', 3),
        music.Note('E', 3),
        music.Note('G', 3),
    ])
    assert actual == expected


@pytest.mark.parametrize(
    'raise_octave,expected',
    [
        ({}, [music.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('Bb', 0)]]),
        ({0: 0, 2: 0}, [music.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('Bb', 0)]]),
        ({0: 1}, [music.Note(*note) for note in [('C', 1), ('E', 1), ('G', 1), ('Bb', 1)]]),
        ({0: 1, 2: 2}, [music.Note(*note) for note in [('C', 1), ('E', 1), ('Bb', 1), ('G', 3)]]),
    ]
)
def test_get_chord_with_add_octave(raise_octave: dict[str, int], expected: list[music.Note]) -> None:
    chord = music.ChordName('C7').get_chord(raise_octave=raise_octave)
    assert chord.notes == expected


def test_get_chord_with_repeats() -> None:
    chord = music.ChordName('C')
    chord.note_names += ['E']
    actual = chord.get_chord(raise_octave={3: 1})
    expected = music.Chord([
        music.Note('C', 0),
        music.Note('E', 0),
        music.Note('G', 0),
        music.Note('E', 1),
    ])
    assert actual == expected


def test_get_all_chords() -> None:
    actual = music.ChordName('C').get_all_chords(
        lower=music.Note('C', 0), upper=music.Note('E', 2)
    )
    expected = [
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 0), ('G', 1)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 1), ('G', 1)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 2), ('G', 0)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 2), ('G', 1)]]),
        music.Chord([music.Note(*note) for note in [('C', 1), ('E', 1), ('G', 1)]]),
        music.Chord([music.Note(*note) for note in [('C', 1), ('E', 2), ('G', 1)]]),
    ]
    assert sorted(expected, key=str) == sorted(actual, key=str)


def test_get_all_chords_with_repeats() -> None:
    actual = music.ChordName('C').get_all_chords(
        lower=music.Note('C', 0), upper=music.Note('E', 1),
        allow_repeats=True, allow_identical=True, max_notes=4
    )
    expected = [
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('C', 0)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('E', 0)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('G', 0)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('C', 1)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('E', 1)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0), ('C', 0)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0), ('G', 0)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0), ('C', 1)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0), ('E', 1)]]),
    ]
    assert sorted(expected, key=str) == sorted(actual, key=str)


def test_is_subset() -> None:
    a = music.GuitarPosition({'E': 3, 'A': 2})
    b = music.GuitarPosition({'E': 3, 'A': 2, 'D': 1})
    assert a.is_subset(b)
    assert not b.is_subset(a)


def test_filter_subsets() -> None:
    positions = [
        music.GuitarPosition({'E': 3, 'A': 2}),
        music.GuitarPosition({'E': 3, 'D': 1}),
        music.GuitarPosition({'E': 3, 'G': 1}),
        music.GuitarPosition({'E': 3, 'e': 1}),
        music.GuitarPosition({'E': 3, 'A': 2, 'D': 1}),
        music.GuitarPosition({'E': 3, 'A': 2, 'G': 1}),
    ]
    expected = [
        music.GuitarPosition({'E': 3, 'A': 2, 'D': 1}),
        music.GuitarPosition({'E': 3, 'A': 2, 'G': 1}),
        music.GuitarPosition({'E': 3, 'e': 1}),
    ]
    actual = music.GuitarPosition.filter_subsets(positions)
    assert actual == expected


def test_get_all_chords_extension() -> None:
    actual = music.ChordName('C9').get_all_chords(
        lower=music.Note('C', 0), upper=music.Note('E', 2)
    )
    expected = [
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('D', 1)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 0), ('G', 0), ('D', 2)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 1), ('G', 0), ('D', 2)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 0), ('G', 1), ('D', 2)]]),
        music.Chord([music.Note(*note) for note in [('C', 0), ('E', 1), ('G', 1), ('D', 2)]]),
        music.Chord([music.Note(*note) for note in [('C', 1), ('E', 1), ('G', 1), ('D', 2)]]),
    ]
    assert sorted(expected, key=str) == sorted(actual, key=str)

@pytest.mark.parametrize(
    'note,other,allow_equal,octave',
    [
        (music.Note('C', 3), 'E', True, 3),
        (music.Note('C', 3), 'C', True, 3),
        (music.Note('C', 3), 'C', False, 4),
        (music.Note('G', 3), 'D', True, 4),
    ]
)
def test_nearest_above(note: music.Note, other: str, allow_equal: bool, octave: int) -> None:
    expected = music.Note(other, octave)
    actual = note.nearest_above(other, allow_equal=allow_equal)
    assert actual == expected


@pytest.mark.parametrize(
    'note,other,allow_equal,octave',
    [
        (music.Note('C', 3), 'E', True, 2),
        (music.Note('C', 3), 'C', True, 3),
        (music.Note('C', 3), 'C', False, 2),
        (music.Note('G', 3), 'D', True, 3),
    ]
)
def test_nearest_below(note: music.Note, other: str, allow_equal: bool, octave: int) -> None:
    expected = music.Note(other, octave)
    actual = note.nearest_below(other, allow_equal=allow_equal)
    assert actual == expected


@pytest.mark.parametrize(
    'list_,n,expected',
    [
        ([1, 2, 3, 4], 0, [1, 2, 3, 4]),
        ([1, 2, 3, 4], 1, [2, 3, 4, 1]),
        ([1, 2, 3, 4], 3, [4, 1, 2, 3]),
        ([1, 2, 3, 4], 5, None),
    ]
)
def test_rotate_list(list_: list[int], n: int, expected: list[int]) -> None:

    if expected is None:
        with pytest.raises(ValueError):
            music._rotate_list(list_, n)
    else:
        actual = music._rotate_list(list_, n)
        assert actual == expected


def test_best_match() -> None:
    s = 'hello there'
    choices = ['h', 'hi', 'hello', 'hello bob']
    assert music.best_match(s, choices) == 'hello'
    with pytest.raises(ValueError):
        music.best_match(s, [choices[1], choices[3]])


def test_is_playable() -> None:
    assert music.GuitarPosition({'E': 3, 'A': 5, 'D': 5, 'G': 4, 'B': 3, 'e': 3}).playable
    assert music.GuitarPosition({'D': 0, 'G': 2, 'B': 3, 'e': 2}).playable
    assert not music.GuitarPosition({'E': 3, 'A': 5, 'D': 5, 'G': 4, 'B': 3, 'e': 1}).playable
    assert music.GuitarPosition({'E': 3, 'A': 2, 'D': 0, 'G': 0, 'B': 0, 'e': 3}).playable
    assert music.GuitarPosition({'E': 3, 'A': 2, 'D': 0, 'G': 0, 'B': 3, 'e': 3}).playable
    assert not music.GuitarPosition({'E': 3, 'A': 2, 'D': 0, 'G': 4, 'B': 3, 'e': 3}).playable


def test_is_barre() -> None:
    assert music.GuitarPosition({'E': 3, 'A': 5, 'D': 5, 'G': 4, 'B': 3, 'e': 3}).barre
    assert not music.GuitarPosition({'D': 0, 'G': 2, 'B': 3, 'e': 2}).barre
    assert not music.GuitarPosition({'E': 3, 'A': 5, 'D': 5, 'G': 4, 'B': 3, 'e': 1}).barre


def test_thumb_position_not_barre() -> None:
    position = music.GuitarPosition({
        'E': 3, 'A': 5, 'D': 3, 'G': 4, 'B': 6
    })
    assert position.use_thumb
    expected = [
        "e x|---|---|---|---|",
        "B  |---|---|---|-@-|",
        "G  |---|-@-|---|---|",
        "D  |-@-|---|---|---|",
        "A  |---|---|-@-|---|",
        "E  |-T-|---|---|---|",
        "    3fr",
    ]
    assert position.printable() == expected


def test_constrained_powerset_same_len() -> None:
    note_list = [
        music.Note('C', 0),
        music.Note('E', 0),
        music.Note('G', 0),
        music.Note('C', 1),
        music.Note('E', 1),
        music.Note('G', 1),
    ]
    expected = [
        [music.Note.from_string(s) for s in ['C0', 'E0', 'G0']],
        [music.Note.from_string(s) for s in ['C0', 'E0', 'G1']],
        [music.Note.from_string(s) for s in ['C0', 'G0', 'E1']],
        [music.Note.from_string(s) for s in ['C0', 'E1', 'G1']],
        [music.Note.from_string(s) for s in ['E0', 'G0', 'C1']],
        [music.Note.from_string(s) for s in ['E0', 'C1', 'G1']],
        [music.Note.from_string(s) for s in ['G0', 'C1', 'E1']],
        [music.Note.from_string(s) for s in ['C1', 'E1', 'G1']],
    ]
    actual = sorted(
        [sorted(s) for s in music.constrained_powerset(note_list, max_len=3)],
    )
    assert len(actual) == len(expected)
    assert set(''.join(str(x)) for x in actual) == set(''.join(str(x)) for x in expected)


def test_constrained_powerset_different_len() -> None:
    note_list = [
        music.Note('C', 0),
        music.Note('E', 0),
        music.Note('C', 1),
        music.Note('E', 1),
    ]
    expected = [
        [music.Note.from_string(s) for s in ['C0', 'E0']],
        [music.Note.from_string(s) for s in ['C0', 'E1']],
        [music.Note.from_string(s) for s in ['E0', 'C1']],
        [music.Note.from_string(s) for s in ['C1', 'E1']],
        [music.Note.from_string(s) for s in ['C0', 'E0', 'C1']],
        [music.Note.from_string(s) for s in ['C0', 'E0', 'E1']],
        [music.Note.from_string(s) for s in ['C0', 'C1', 'E1']],
        [music.Note.from_string(s) for s in ['E0', 'C1', 'E1']],
    ]
    actual = sorted(
        [sorted(s) for s in music.constrained_powerset(note_list, max_len=3)],
    )
    assert len(actual) == len(expected)
    assert set(''.join(str(x)) for x in actual) == set(''.join(str(x)) for x in expected)


def test_constrained_powerset_different_required_notes() -> None:
    note_list = [
        music.Note('C', 0),
        music.Note('E', 0),
        music.Note('G', 0),
        music.Note('C', 1),
    ]
    expected = [
        [music.Note.from_string(s) for s in ['C0', 'E0']],
        [music.Note.from_string(s) for s in ['E0', 'C1']],
        [music.Note.from_string(s) for s in ['C0', 'E0', 'C1']],
        [music.Note.from_string(s) for s in ['C0', 'E0', 'G0']],
        [music.Note.from_string(s) for s in ['E0', 'G0', 'C1']],
    ]
    temp = music.constrained_powerset(
        note_list, max_len=3,
        required_notes=music.note_set([music.Note('C', 0), music.Note('E', 0)])
    )
    actual = [sorted(s) for s in temp]
    print(actual)
    assert len(actual) == len(expected)
    assert set(''.join(str(x)) for x in actual) == set(''.join(str(x)) for x in expected)


def test_constrained_powerset_allow_identical() -> None:
    note_list = [
        music.Note('C', 0),
        music.Note('E', 0),
        music.Note('G', 0),
        music.Note('C', 1),
    ]
    expected = [
        [music.Note.from_string(s) for s in ['C0', 'E0']],
        [music.Note.from_string(s) for s in ['E0', 'C1']],
        [music.Note.from_string(s) for s in ['C0', 'C0', 'E0']],
        [music.Note.from_string(s) for s in ['C0', 'E0', 'E0']],
        [music.Note.from_string(s) for s in ['C0', 'E0', 'C1']],
        [music.Note.from_string(s) for s in ['E0', 'E0', 'C1']],
        [music.Note.from_string(s) for s in ['E0', 'C1', 'C1']],
        [music.Note.from_string(s) for s in ['C0', 'E0', 'G0']],
        [music.Note.from_string(s) for s in ['E0', 'G0', 'C1']],
    ]
    temp = music.constrained_powerset(
        note_list, max_len=3,
        required_notes=music.note_set([music.Note('C', 0), music.Note('E', 0)]),
        allow_identical=True
    )
    actual = [sorted(s) for s in temp]
    print(actual)
    assert len(actual) == len(expected)
    assert set(''.join(str(x)) for x in actual) == set(''.join(str(x)) for x in expected)


def test_constrained_powerset_dont_allow_repeats() -> None:
    note_list = [
        music.Note('C', 0),
        music.Note('E', 0),
        music.Note('G', 0),
        music.Note('C', 1),
    ]
    expected = [
        [music.Note.from_string(s) for s in ['C0', 'E0']],
        [music.Note.from_string(s) for s in ['E0', 'C1']],
        [music.Note.from_string(s) for s in ['C0', 'E0', 'G0']],
        [music.Note.from_string(s) for s in ['E0', 'G0', 'C1']],
    ]
    temp = music.constrained_powerset(
        note_list, max_len=3,
        required_notes=music.note_set([music.Note('C', 0), music.Note('E', 0)]),
        allow_repeats=False
    )
    actual = [sorted(s) for s in temp]
    print(actual)
    assert len(actual) == len(expected)
    assert set(''.join(str(x)) for x in actual) == set(''.join(str(x)) for x in expected)


@pytest.mark.parametrize('max_notes', [3, 4, 5, 6])
def test_get_all_chords_again(max_notes: int) -> None:
    c = music.ChordName('C')
    expected = [
        music.Chord.from_string('C0,E0,G0'),
        music.Chord.from_string('C0,E0,G1'),
        music.Chord.from_string('C0,E1,G0'),
        music.Chord.from_string('C0,E1,G1'),
        music.Chord.from_string('C1,E1,G1'),
    ]
    actual = c.get_all_chords(upper=music.Note('G', 1), max_notes=max_notes, allow_repeats=False)
    assert set(actual) == set(expected)


def test_get_all_chords_allow_repeats() -> None:
    c = music.ChordName('C')
    expected = [
        music.Chord.from_string('C0,E0,G0'),
        music.Chord.from_string('C0,E0,G1'),
        music.Chord.from_string('C0,E1,G0'),
        music.Chord.from_string('C0,E1,G1'),
        music.Chord.from_string('C1,E1,G1'),
        music.Chord.from_string('C0,E0,G0,C1'),
        music.Chord.from_string('C0,E0,G1,C1'),
        music.Chord.from_string('C0,E1,G0,C1'),
        music.Chord.from_string('C0,E1,G1,C1'),
        music.Chord.from_string('C0,E0,G0,E1'),
        music.Chord.from_string('C0,E0,G1,E1'),
        music.Chord.from_string('C0,E1,G0,G1'),
        music.Chord.from_string('C0,E0,G0,G1'),
    ]
    actual = c.get_all_chords(upper=music.Note('G', 1), max_notes=4, allow_repeats=True)
    assert set(actual) == set(expected)


def test_get_all_chords_allow_identical() -> None:
    c = music.ChordName('C')
    expected = [
        music.Chord.from_string('C0,E0,G0'),
        music.Chord.from_string('C0,E0,G1'),
        music.Chord.from_string('C0,E1,G0'),
        music.Chord.from_string('C0,E1,G1'),
        music.Chord.from_string('C1,E1,G1'),

        music.Chord.from_string('C0,E0,G0,C1'),
        music.Chord.from_string('C0,E0,G1,C1'),
        music.Chord.from_string('C0,E1,G0,C1'),
        music.Chord.from_string('C0,E1,G1,C1'),
        music.Chord.from_string('C0,E0,G0,E1'),
        music.Chord.from_string('C0,E0,G1,E1'),
        music.Chord.from_string('C0,E1,G0,G1'),
        music.Chord.from_string('C0,E0,G0,G1'),

        music.Chord.from_string('C0,E0,G0,C0'),
        music.Chord.from_string('C0,E0,G1,C0'),
        music.Chord.from_string('C0,E1,G0,C0'),
        music.Chord.from_string('C0,E1,G1,C0'),
        music.Chord.from_string('C0,E0,G0,E0'),
        music.Chord.from_string('C0,E0,G1,E0'),
        music.Chord.from_string('C0,E1,G0,G0'),
        music.Chord.from_string('C0,E0,G0,G0'),
        music.Chord.from_string('C0,E1,G1,G1'),
        music.Chord.from_string('C1,C1,E1,G1'),
        music.Chord.from_string('C0,E0,G1,G1'),
        music.Chord.from_string('C1,E1,E1,G1'),
        music.Chord.from_string('C0,E1,E1,G1'),
        music.Chord.from_string('C0,G0,E1,E1'),
        music.Chord.from_string('C1,E1,G1,G1'),
    ]
    actual = c.get_all_chords(
        upper=music.Note('G', 1), max_notes=4,
        allow_repeats=True, allow_identical=True
    )
    assert set(actual) == set(expected)


def test_get_all_chords_extension_again() -> None:
    c = music.ChordName('Cmaj79')
    expected = [
        music.Chord.from_string('C0,E0,G0,B0,D1'),
        music.Chord.from_string('C0,E0,G0,B0,C1,D1'),
    ]
    actual = c.get_all_chords(
        upper=music.Note('C', 2), max_notes=6,
        allow_repeats=True, allow_identical=False
    )
    assert set(actual) == set(expected)


def test_parse_all_chord_names() -> None:
    for name in music.ChordName.ALL_CHORD_NAMES:
        music.ChordName(name)


@pytest.mark.parametrize('name,frequency', [('A4', 440.), ('A3', 220.), ('C4', 261.626)])
def test_frequency(name: str, frequency: float) -> None:
    assert music.Note.from_string(name).frequency == pytest.approx(frequency, rel=1e-3)


def test_write_wav(tmp_path) -> None:
    d = tmp_path / "foo"
    d.mkdir()
    p = str(d / "audio.wav")
    assert not os.path.exists(p)
    music.Chord([
        music.Note('C', 3),
        music.Note('E', 3),
        music.Note('G', 3),
    ]).to_audio().write_wav(p)
    assert os.path.exists(p)


def test_write_png(tmp_path) -> None:
    d = tmp_path / "foo"
    d.mkdir()
    p = str(d / "audio.png")
    assert not os.path.exists(p)
    music.Staff(chords=[
        music.Chord([
            music.Note('C', 3),
            music.Note('E', 3),
            music.Note('G', 3),
        ])
    ]).write_png(p)
    assert os.path.exists(p)


@pytest.mark.parametrize(
    'note,line', [('C4', 0), ('C5', 7), ('E4', 2), ('Eb4', 2), ('E#4', 2)]
)
def test_staff_line(note: str, line: int) -> None:
    assert music.Note.from_string(note).staff_line == line


@pytest.mark.parametrize(
    'notes,gaps',
    [
        ([], []),
        ([music.Note('C', 4)], [None]),
        ([music.Note('C', 4), music.Note('C', 4)], [None, 0]),
        ([music.Note('C', 4), music.Note('D', 4)], [None, 1]),
    ]
)
def test_staff_line_gaps(notes: list[music.Note], gaps: list[int]) -> None:
    assert music.Chord(notes=notes).staff_line_gaps == gaps


@pytest.mark.parametrize(
    'notes,lowest_line,highest_line',
    [
        ([music.Note(*note) for note in [('C', 5), ('D', 5)]], 2, 10),
        ([music.Note(*note) for note in [('D', 4)]], 2, 10),
        ([music.Note(*note) for note in [('C', 4)]], 0, 10),
        ([music.Note(*note) for note in [('G', 5)]], 2, 10),
        ([music.Note(*note) for note in [('A', 5)]], 2, 12),
        ([music.Note(*note) for note in [('C', 4), ('A', 5)]], 0, 12),
    ]
)
def test_staff_extreme_lines(notes: list[music.Note], lowest_line: int, highest_line: int) -> None:
    staff = music.Staff(chords=[music.Chord(notes)])
    assert staff.ledger_lines[0] == (lowest_line, highest_line)


def test_chord_comparison() -> None:
    assert music.Chord([music.Note('C', 0)]) == music.Chord([music.Note('C', 0)])
    assert music.Chord([music.Note('C', 0)]) < music.Chord([music.Note('D', 0)])
    assert music.Chord([music.Note('C', 0)]) < music.Chord([music.Note('C', 0), music.Note('D', 1)])
    assert music.Chord([music.Note('C', 0), music.Note('D', 1)]) < music.Chord([music.Note('C', 0), music.Note('E', 1)])


def test_guitar_notes() -> None:
    guitar = music.Guitar()
    expected_notes = [music.Note(*n) for n in [('G', 2), ('B', 2), ('D', 3)]]
    expected_chord = music.Chord(expected_notes)
    assert guitar.notes(position={'E': 3, 'A': 2, 'D': 0}) == expected_notes
    assert guitar.chord(position={'E': 3, 'A': 2, 'D': 0}) == expected_chord


def test_bias_in_voicings() -> None:
    chord_name = music.ChordName('Dmaj7#11')
    assert chord_name.note_names == ['D', 'F#', 'A', 'C#']
    assert chord_name.extension_names == ['G#']
    for chord in chord_name.get_all_guitar_chords():
        names = set([n.name for n in chord.notes])
        assert names == {'D', 'F#', 'A', 'C#', 'G#'}
        for pos in chord.guitar_positions():
            assert pos.chord == chord
            assert set(n.name for n in pos.chord.notes) == names


def test_semitone_distance() -> None:
    c1 = music.Chord([
        music.Note('C', 3),
        music.Note('Eb', 3),
        music.Note('F', 3),
        music.Note('A', 3)
    ])
    c2 = music.Chord([
        music.Note('C', 3),
        music.Note('E', 3),
        music.Note('G', 3),
        music.Note('Bb', 3),
    ])
    assert c1.semitone_distance(c2) == 4
    assert c2.semitone_distance(c1) == 4


def test_semitone_distance_different_cardinality() -> None:
    c1 = music.Chord([
        music.Note('C', 3),
        music.Note('F', 3),
        music.Note('A', 3)
    ])
    c2 = music.Chord([
        music.Note('C', 3),
        music.Note('E', 3),
        music.Note('G', 3),
        music.Note('Bb', 3),
    ])
    assert c1.semitone_distance(c2) == 4
    assert c2.semitone_distance(c1) == 4


def test_voice_leading() -> None:
    cp = music.ChordProgression([
        music.ChordName(n) for n in ['Em7', 'A7', 'Dm7', 'G7', 'CM7']]
    )
    result1 = cp.optimal_voice_leading(
        lower=music.Note('C', 2),
        upper=music.Note('C', 4),
        use_dijkstra=True
    )
    result2 = cp.optimal_voice_leading(
        lower=music.Note('C', 2),
        upper=music.Note('C', 4),
        use_dijkstra=False
    )
    assert result1 == result2


def test_audio_add() -> None:
    import numpy as np
    t = np.linspace(0, 1, 100)
    sample_rate = 100
    x1 = music.Audio(sample_rate=sample_rate, waveform=np.sin(t))
    x2 = music.Audio(sample_rate=sample_rate, waveform=np.sin(2 * t))
    x3 = x1 + x2
    assert x3.duration == 2.0


def test_audio_from_chord_list() -> None:
    chords = [
        music.ChordName('G7').get_chord(),
        music.ChordName('C7').get_chord(),
        music.ChordName('F7').get_chord(),
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
def test_position_motion_distance(p1: dict[str, int], p2: dict[str, int], expected: int) -> None:
    p1 = music.GuitarPosition(positions=p1)
    p2 = music.GuitarPosition(positions=p2)
    assert p1.motion_distance(p2) == expected


def test_optimal_progression() -> None:
    cp = music.ChordProgression([
        music.ChordName(n) for n in ['Dm7', 'G7', 'CM7']
    ])
    result = cp.optimal_guitar_positions()
    print(result)