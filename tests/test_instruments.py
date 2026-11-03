from typing import Optional, Literal, Hashable

import pytest

from music import primitives
from music import instruments


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
    assert instruments.GuitarPosition(position).max_interior_gap == expected


def test_sort_guitar_positions() -> None:
    positions = [
        instruments.GuitarPosition({"E": 5, "G": 5}),
        instruments.GuitarPosition({"E": 1, "A": 5}),
        instruments.GuitarPosition({"E": 7, "A": 7}),
        instruments.GuitarPosition({"E": 7, "G": 7}),
    ]
    expected = [
        instruments.GuitarPosition({"E": 7, "A": 7}),
        instruments.GuitarPosition({"E": 7, "G": 7}),
        instruments.GuitarPosition({"E": 5, "G": 5}),
        instruments.GuitarPosition({"E": 1, "A": 5}),
    ]
    actual = instruments.GuitarPosition.sorted(positions)
    assert actual == expected


def test_redundant_position() -> None:
    assert instruments.GuitarPosition({'E': 12, 'A': 13, 'b': 14}).redundant
    assert instruments.GuitarPosition({'E': 12, 'A': 0, 'b': 14}).redundant
    assert not instruments.GuitarPosition({'E': 11, 'A': 0, 'b': 14}).redundant


def test_guitar_extremes() -> None:
    guitar = instruments.Guitar(
        tuning={'E': primitives.Note('E', 2), 'A': primitives.Note('A', 2)},
        frets=3
    )
    assert guitar.lowest == primitives.Note('E', 2)
    assert guitar.highest == primitives.Note('C', 3)


def test_print() -> None:
    position = instruments.GuitarPosition({'A': 2, 'D': 2})
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


def test_print_with_fingers() -> None:
    position = instruments.GuitarPosition({'A': 2, 'D': 2})
    expected = [
        "e x|---|",
        "B x|---|",
        "G x|---|",
        "D  |-2-|",
        "A  |-1-|",
        "E x|---|",
        "    2fr",
    ]
    actual = position.printable(fingers=True)
    assert actual == expected


def test_print_more_complex() -> None:
    open_d = {"D": "D2", "A": "A2", "d": "D3", "F#": "F#3", "a": "A3", "dd": "D4"}
    guitar = instruments.Guitar(tuning={
        string: primitives.Note.from_string(note) for string, note in open_d.items()
    })
    position = instruments.GuitarPosition({'A': 2, 'd': 2, 'F#': 3, 'a': 4, 'dd': 0}, guitar=guitar)

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
    position = instruments.GuitarPosition({'E': 3, 'A': 5, 'D': 5, 'G': 4, 'B': 3, 'e': 3})
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
    position = instruments.GuitarPosition({'A': 10, 'D': 12, 'G': 10, 'B': 12, 'e': 10})
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
    expected = [
        "e  |-1-|---|---|",
        "B  |-|-|---|-4-|",
        "G  |-|-|---|---|",
        "D  |-|-|---|-3-|",
        "A  |-1-|---|---|",
        "E x|---|---|---|",
        "    10fr",
    ]
    actual = position.printable(fingers=True)
    assert actual == expected


def test_no_open_strings_along_barre() -> None:
    position = instruments.GuitarPosition({"E": 3, "D": 5, "G": 7, "B": 3, "e": 7})
    assert not position.barre
    expected = [
        "e  |---|---|---|---|-@-|",
        "B  |-@-|---|---|---|---|",
        "G  |---|---|---|---|-@-|",
        "D  |---|---|-@-|---|---|",
        "A x|---|---|---|---|---|",
        "E  |-@-|---|---|---|---|",
        "    3fr",
    ]
    assert position.printable() == expected
    position = instruments.GuitarPosition({"E": 3, "A": 0, "D": 5, "G": 7, "B": 3, "e": 7})
    assert not position.barre
    expected = [
        "e  |---|---|---|---|-4-|",
        "B  |-1-|---|---|---|---|",
        "G  |---|---|---|---|-3-|",
        "D  |---|---|-2-|---|---|",
        "A o|---|---|---|---|---|",
        "E  |-T-|---|---|---|---|",
        "    3fr",
    ]
    assert position.printable(fingers=True) == expected


@pytest.mark.parametrize(
    'string',
    [
        '{"E": "E2", "A": "A2"}',
        "{'E': 'E2', 'A': 'A2'}",
        str({"E": str(primitives.Note('E', 2)), "A": str(primitives.Note('A', 2))}),
    ]
)
def test_parse_tuning_json(string: str) -> None:
    expected = {
        "E": primitives.Note('E', 2),
        "A": primitives.Note('A', 2)
    }
    assert instruments.Guitar.parse_tuning(string) == expected


@pytest.mark.parametrize('how', ['csv', None])
def test_parse_tuning_csv(how: Optional[Literal['csv', 'json']]) -> None:
    expected = {
        "E": primitives.Note('E', 2),
        "A": primitives.Note('A', 2)
    }
    assert instruments.Guitar.parse_tuning('E,E2;A,A2', how=how) == expected


@pytest.mark.parametrize(
    'string,how,error',
    [
        ('{"foo"}', 'json', True),
        ('{"foo"}', 'csv', True),
        ('{"foo"}', None, True),
        ('a;b;c', 'json', True),
        ('a;b;c', 'csv', True),
        ('a;b;c', None, True),
        ('{"E": "E2"}', 'json', False),
        ('{"E": "E2"}', 'csv', True),
        ('{"E": "E2"}', None, False),
        ('E,E2;A,A2', 'json', True),
        ('E,E2;A,A2', 'csv', False),
        ('E,E2;A,A2', None, False),
        ('E,E2;A,A2', 'xml', True),
    ]
)
def test_parse_tuning_error(string: str, how: Optional[Literal['csv', 'json']], error: bool) -> None:
    if error:
        with pytest.raises(instruments.InvalidParseError):
            instruments.Guitar.parse_tuning(string, how)
    else:
        instruments.Guitar.parse_tuning(string, how)


def test_is_subset() -> None:
    a = instruments.GuitarPosition({'E': 3, 'A': 2})
    b = instruments.GuitarPosition({'E': 3, 'A': 2, 'D': 1})
    assert a.is_subset(b)
    assert not b.is_subset(a)


def test_filter_subsets() -> None:
    positions = [
        instruments.GuitarPosition({'E': 3, 'A': 2}),
        instruments.GuitarPosition({'E': 3, 'D': 1}),
        instruments.GuitarPosition({'E': 3, 'G': 1}),
        instruments.GuitarPosition({'E': 3, 'e': 1}),
        instruments.GuitarPosition({'E': 3, 'A': 2, 'D': 1}),
        instruments.GuitarPosition({'E': 3, 'A': 2, 'G': 1}),
    ]
    expected = [
        instruments.GuitarPosition({'E': 3, 'A': 2, 'D': 1}),
        instruments.GuitarPosition({'E': 3, 'A': 2, 'G': 1}),
        instruments.GuitarPosition({'E': 3, 'e': 1}),
    ]
    actual = instruments.GuitarPosition.filter_subsets(positions)
    assert actual == expected


def test_is_playable() -> None:
    assert instruments.GuitarPosition({'E': 3, 'A': 5, 'D': 5, 'G': 4, 'B': 3, 'e': 3}).playable
    assert instruments.GuitarPosition({'D': 0, 'G': 2, 'B': 3, 'e': 2}).playable
    assert not instruments.GuitarPosition({'E': 3, 'A': 5, 'D': 5, 'G': 4, 'B': 3, 'e': 1}).playable
    assert instruments.GuitarPosition({'E': 3, 'A': 2, 'D': 0, 'G': 0, 'B': 0, 'e': 3}).playable
    assert instruments.GuitarPosition({'E': 3, 'A': 2, 'D': 0, 'G': 0, 'B': 3, 'e': 3}).playable
    assert not instruments.GuitarPosition({'E': 3, 'A': 2, 'D': 0, 'G': 4, 'B': 3, 'e': 3}).playable


def test_is_barre() -> None:
    assert instruments.GuitarPosition({'E': 3, 'A': 5, 'D': 5, 'G': 4, 'B': 3, 'e': 3}).barre
    assert not instruments.GuitarPosition({'D': 0, 'G': 2, 'B': 3, 'e': 2}).barre
    assert not instruments.GuitarPosition({'E': 3, 'A': 5, 'D': 5, 'G': 4, 'B': 3, 'e': 1}).barre


def test_thumb_position_not_barre() -> None:
    position = instruments.GuitarPosition({
        'E': 3, 'A': 5, 'D': 3, 'G': 4, 'B': 6
    })
    assert position.use_thumb
    expected = [
        "e x|---|---|---|---|",
        "B  |---|---|---|-@-|",
        "G  |---|-@-|---|---|",
        "D  |-@-|---|---|---|",
        "A  |---|---|-@-|---|",
        "E  |-@-|---|---|---|",
        "    3fr",
    ]
    assert position.printable() == expected
    expected = [
        "e x|---|---|---|---|",
        "B  |---|---|---|-4-|",
        "G  |---|-2-|---|---|",
        "D  |-1-|---|---|---|",
        "A  |---|---|-3-|---|",
        "E  |-T-|---|---|---|",
        "    3fr",
    ]
    assert position.printable(fingers=True) == expected


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
    assert instruments.GuitarPosition(positions).fingers_dict == expected


@pytest.mark.parametrize(
    'positions,expected',
    [
        ({'A': 2, 'D': 4}, {'A': '1', 'D': '3'}),
        ({'A': 2, 'D': 5}, {'A': '1', 'D': '4'}),
        ({'A': 2, 'D': 5, 'G': 2}, {'A': '1', 'D': '4', 'G': '2'}),
    ]
)
def test_finger_skips(positions: dict[Hashable, int], expected: dict[Hashable, str]) -> None:
    position = instruments.GuitarPosition(positions=positions)
    assert position.fingers_dict == expected


@pytest.mark.parametrize(
    'positions',
    [{'E': 8, 'A': 7, 'D': 9, 'G': 0, 'B': 8, 'e': 7}]
)
def check_unplayable_positions(positions: dict[Hashable, int]) -> None:
    assert not instruments.GuitarPosition(positions=positions).playable


def test_guitar_notes() -> None:
    guitar = instruments.Guitar()
    expected_notes = [primitives.Note(*n) for n in [('G', 2), ('B', 2), ('D', 3)]]
    expected_chord = primitives.Chord(expected_notes)
    assert guitar.notes(position={'E': 3, 'A': 2, 'D': 0}) == expected_notes
    assert guitar.chord(position={'E': 3, 'A': 2, 'D': 0}) == expected_chord


@pytest.mark.parametrize(
    'p1,p2,expected',
    [
        ({'A': 2, 'G': 2}, {'A': 3, 'B': 3}, 3),
        ({'A': 2, 'G': 2, 'B': 3}, {'A': 3, 'B': 3}, 1),
        ({}, {'A': 3, 'B': 3}, 0),
    ]
)
def test_position_motion_distance(p1: dict[Hashable, int], p2: dict[Hashable, int], expected: int) -> None:
    p1_ = instruments.GuitarPosition(positions=p1)
    p2_ = instruments.GuitarPosition(positions=p2)
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
    p1_ = instruments.GuitarPosition(positions=p1)
    p2_ = instruments.GuitarPosition(positions=p2)
    assert p1_.motion_distance(p2_, respect_fingers=True) == expected