import os

import pytest

from music import primitives, graphics


def test_write_png(tmp_path) -> None:
    d = tmp_path / "foo"
    d.mkdir()
    p = str(d / "audio.png")
    assert not os.path.exists(p)
    graphics.Staff(chords=[
        primitives.Chord([
            primitives.Note('C', 3),
            primitives.Note('E', 3),
            primitives.Note('G', 3),
        ])
    ]).write_png(p)
    assert os.path.exists(p)


@pytest.mark.parametrize(
    'note,line', [('C4', 0), ('C5', 7), ('E4', 2), ('Eb4', 2), ('E#4', 2)]
)
def test_staff_line(note: str, line: int) -> None:
    assert primitives.Note.from_string(note).staff_line == line


@pytest.mark.parametrize(
    'notes,gaps',
    [
        ([], []),
        ([primitives.Note('C', 4)], [None]),
        ([primitives.Note('C', 4), primitives.Note('C', 4)], [None, 0]),
        ([primitives.Note('C', 4), primitives.Note('D', 4)], [None, 1]),
    ]
)
def test_staff_line_gaps(notes: list[primitives.Note], gaps: list[int]) -> None:
    assert primitives.Chord(notes=notes).staff_line_gaps == gaps


@pytest.mark.parametrize(
    'notes,lowest_line,highest_line',
    [
        ([primitives.Note(*note) for note in [('C', 5), ('D', 5)]], 2, 10),
        ([primitives.Note(*note) for note in [('D', 4)]], 2, 10),
        ([primitives.Note(*note) for note in [('C', 4)]], 0, 10),
        ([primitives.Note(*note) for note in [('G', 5)]], 2, 10),
        ([primitives.Note(*note) for note in [('A', 5)]], 2, 12),
        ([primitives.Note(*note) for note in [('C', 4), ('A', 5)]], 0, 12),
    ]
)
def test_staff_extreme_lines(notes: list[primitives.Note], lowest_line: int, highest_line: int) -> None:
    staff = graphics.Staff(chords=[primitives.Chord(notes)])
    assert staff.ledger_lines[0] == (lowest_line, highest_line)
