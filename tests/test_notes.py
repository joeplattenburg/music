import pytest

import notes


@pytest.mark.parametrize(
    'semitones,expected',
    [
        (0, notes.Note('C', 0)),
        (12, notes.Note('C', 1)),
        (39, notes.Note('Eb', 3)),
    ]
)
def test_note_from_semitones(semitones: int, expected: notes.Note) -> None:
    actual = notes.Note.from_semitones(semitones=semitones)
    assert actual == expected


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


def test_both_sharps_work() -> None:
    assert (
        notes.Note('F#', 3) ==
        notes.Note('Fs', 3) ==
        notes.Note('Gb', 3)
    )
    assert (
        notes.Note('C##', 2) ==
        notes.Note('Css', 2) ==
        notes.Note('D', 2)
    )


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


def test_validity_of_high_frets_with_capo() -> None:
    guitar = notes.Guitar(frets=5, capo=4)
    assert notes.Note('A', 2).guitar_positions(guitar, valid_only=True).positions_dict == {'E': 1}
    assert notes.Note('A#', 2).guitar_positions(guitar, valid_only=True).positions_dict == {}


def test_print() -> None:
    position = notes.GuitarPosition({'A': 2, 'D': 2})
    expected = (
        "e x|---|\n"
        "B x|---|\n"
        "G x|---|\n"
        "D  |-@-|\n"
        "A  |-@-|\n"
        "E x|---|\n"
        "  1fr"
    )
    actual = position.print()
    print(actual)
    assert actual == expected
