import os
from functools import reduce
from operator import add

import pytest

from music import primitives, instruments, engines


def test_positions_found_with_lower_notes_on_higher_strings() -> None:
    chord = primitives.Chord([
        primitives.Note('A', 2), primitives.Note('C#', 3)
    ])
    expected = [
        {'E': 9, 'A': 0},
        {'E': 5, 'A': 4},
    ]
    engine = engines.FretboardEngine()
    actual = [p.positions_dict for p in engine.chord_to_guitar_positions(chord=chord)]
    assert actual == expected


@pytest.mark.parametrize(
    'frets,expected',
    [
        (10, {'E': 8, 'A': 3}),
        (5, {'A': 3})
    ]
)
def test_guitar_with_different_fret_count(frets: int, expected: dict[str, int]) -> None:
    guitar = instruments.Guitar(frets=frets)
    note = primitives.Note('C', 3)
    engine = engines.FretboardEngine()
    actual = engine.note_to_guitar_position(note=note, guitar=guitar).positions_dict
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
    guitar = instruments.Guitar(
        tuning={i: primitives.Note(*string) for i, string in enumerate(strings)},
        capo=capo
    )
    chord = primitives.Chord([primitives.Note(*string).add_semitones(capo) for string in strings])
    engine = engines.FretboardEngine()
    expected = {i: 0 for i in range(len(strings))}
    actual = engine.chord_to_guitar_positions(chord=chord, guitar=guitar, include_unplayable=True)[0].positions_dict
    assert actual == expected


@pytest.mark.parametrize('tuning_name,tuning', instruments.Guitar.TUNINGS.items())
def test_different_guitar_tuning_names(tuning_name: str, tuning: instruments.Guitar.Tuning) -> None:
    guitar = instruments.Guitar(tuning_name=tuning_name)
    chord = primitives.Chord([note for note in tuning.values()])
    engine = engines.FretboardEngine()
    expected = {s: 0 for s in guitar.string_names}
    actual = engine.chord_to_guitar_positions(chord=chord, guitar=guitar, include_unplayable=True)[0].positions_dict
    print(expected, actual)
    assert actual == expected


def test_validity_of_high_frets_with_capo() -> None:
    guitar = instruments.Guitar(frets=5, capo=4)
    engine = engines.FretboardEngine()
    assert engine.note_to_guitar_position(primitives.Note('A', 2), guitar, valid_only=True).positions_dict == {'E': 1}
    assert engine.note_to_guitar_position(primitives.Note('A#', 2), guitar, valid_only=True).positions_dict == {}


def test_bias_in_voicings() -> None:
    chord_name = primitives.ChordName('Dmaj7#11')
    engine = engines.FretboardEngine()
    assert chord_name.note_names == ['D', 'F#', 'A', 'C#']
    assert chord_name.extension_names == ['G#']
    for chord in engine.chord_name_to_guitar_chords(chord_name):
        names = set([n.name for n in chord.notes])
        assert names == {'D', 'F#', 'A', 'C#', 'G#'}
        for pos in engine.chord_to_guitar_positions(chord):
            assert pos.chord == chord
            assert set(n.name for n in pos.chord.notes) == names


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
    cp = primitives.ChordProgression([primitives.ChordName(n) for n in prog])
    engine = engines.FretboardEngine()
    actual = engine.chord_progression_to_optimal_guitar_positions(cp, respect_fingers=respect_fingers)
    assert  len(actual) == len(prog)


def test_write_wav(tmp_path) -> None:
    engine = engines.AudioEngine()
    d = tmp_path / "foo"
    d.mkdir()
    p = str(d / "audio.wav")
    assert not os.path.exists(p)
    chord = primitives.Chord([
        primitives.Note('C', 3),
        primitives.Note('E', 3),
        primitives.Note('G', 3),
    ])
    engine.chord_to_audio(chord=chord).write_wav(p)
    assert os.path.exists(p)


def test_audio_from_chord_list() -> None:
    engine = engines.AudioEngine(tempo=60)
    chords = [
        primitives.ChordName('G7').get_chord(),
        primitives.ChordName('C7').get_chord(),
        primitives.ChordName('F7').get_chord(),
    ]
    audios = [engine.chord_to_audio(chord=chord) for chord in chords]
    audio = reduce(add, audios)
    assert audio.duration == 3.0


def test_note_sequence_to_audio(tmp_path) -> None:
    (tmp_path / 'dir').mkdir()
    assert not (tmp_path / 'dir' / 'file.wav').exists()
    engine = engines.AudioEngine()
    sequence = primitives.NoteSequence(events=[
        primitives.NoteEvent(notes=[primitives.Note('C', 3)], duration_beats=0.25, offset_beats=0.),
        primitives.NoteEvent(notes=[primitives.Note('D', 3)], duration_beats=0.25, offset_beats=0.25),
        primitives.NoteEvent(notes=[primitives.Note('E', 3)], duration_beats=0.25, offset_beats=0.25),
    ])
    audio = engine.note_sequence_to_audio(sequence)
    audio.write_wav(str(tmp_path / 'dir' / 'file.wav'))
    assert (tmp_path / 'dir' / 'file.wav').exists()