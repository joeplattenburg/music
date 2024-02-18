import notes


def test_positions_found_with_lower_notes_on_higher_strings() -> None:
    chord = notes.Chord([
        notes.Note('A', 2), notes.Note('C#', 3)
    ])
    expected = [
        {'E': 9, 'A': 0},
        {'E': 5, 'A': 4},
    ]
    actual = chord.guitar_positions()
    assert actual == expected
