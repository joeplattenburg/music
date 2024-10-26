import argparse
import time

from music import music


def guitar_positions(args: argparse.Namespace):
    guitar = music.Guitar(tuning=args.tuning, capo=args.capo, frets=args.frets)
    if args.notes:
        note_list = [music.Note.from_string(note) for note in args.notes.split(',')]
        chord = music.Chord(note_list)
        print(f'You input the chord: {chord}')
        positions_playable = chord.guitar_positions(
            guitar=guitar, include_unplayable=False, max_fret_span=args.max_fret_span
        )
        positions_all_count = chord.num_total_guitar_positions
    elif args.name:
        print(f'You input the chord: {args.name}')
        chord_name = music.ChordName(args.name)
        positions_all = music.get_all_guitar_positions_for_chord_name(
            chord_name=chord_name, guitar=guitar, max_fret_span=args.max_fret_span,
            allow_repeats=args.allow_repeats, allow_identical=args.allow_identical,
            parallel=args.parallel,
        )
        positions_playable = list(filter(lambda x: (x.playable and not x.redundant), positions_all))
        positions_all_count = len(positions_all)
    else:
        raise ValueError('Either `notes` or `name` is required')
    if args.allow_repeats:
        positions_playable = music.GuitarPosition.filter_subsets(positions_playable)
    chords_playable = sorted(list(set(p.chord for p in positions_playable)))
    positions = music.GuitarPosition.sorted(positions_playable)[:args.top_n]
    tuning_display = guitar.tuning_name if guitar.tuning_name == 'standard' else f'{guitar.tuning_name} ({guitar}):'
    print(
        f'There are {len(chords_playable)} playable voicings and {len(positions_playable)} guitar positions '
        f'(out of {positions_all_count} possible) for a guitar tuned to {tuning_display}.'
    )
    if args.top_n:
        print(f'Here are the top {args.top_n}:')
    for p in positions:
        print('\n' + '\n'.join(p.printable())) if args.graphical else print(p)


def guitar_optimal_progression(args: argparse.Namespace):
    print(f'You input the chord progression: {args.chords}')
    cp = music.ChordProgression([music.ChordName(n) for n in args.chords])
    result = cp.optimal_guitar_positions()
    print('The optimal positions for this progression are:')
    for chord, position in zip(args.chords, result):
        print(f'{chord}')
        print('\n' + '\n'.join(position.printable())) if args.graphical else print(position)


def voice_leading(args: argparse.Namespace):
    print(f'You input the chord progresssion: {args.chords}')
    cp = music.ChordProgression([music.ChordName(n) for n in args.chords])
    result = cp.optimal_voice_leading(
        lower=music.Note.from_string(args.lower),
        upper=music.Note.from_string(args.upper),
    )
    print('The optimal voicing for this progression is:')
    for chord, voicing in zip(args.chords, result):
        print(f'{chord}: {voicing}')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='General purpose helpers for music',
    )
    subparsers = parser.add_subparsers(title='subcommands')

    guitar_positions_parser = subparsers.add_parser(
        'guitar-positions', help='Given a chord, show the corresponding guitar positions'
    )
    guitar_positions_parser.add_argument(
        '--notes', type=str, help='A comma separated list of notes, e.g. `C3,G3,Eb4`'
    )
    guitar_positions_parser.add_argument(
        '--name', type=str,
        help='A chord name, like Bbmaj7/D; will return all possible voicings'
    )
    guitar_positions_parser.add_argument(
        '--top-n', '-n', type=int, default=None,
        help='How many positions to return'
    )
    guitar_positions_parser.add_argument(
        '--max-fret-span', '-f', type=int, default=music.DEFAULT_MAX_FRET_SPAN,
        help='Max fret span to consider playable'
    )
    guitar_positions_parser.add_argument(
        '--allow-repeats', '-r', action='store_true',
        help='Allow chord tones to appear more than once (different octaves)'
    )
    guitar_positions_parser.add_argument(
        '--allow-identical', '-i', action='store_true',
        help='Allow chord tones to appear more than once in the same octave'
    )
    guitar_positions_parser.add_argument(
        '--graphical', '-g', action='store_true',
        help='Show ASCII art for guitar positions'
    )
    guitar_positions_parser.add_argument(
        '--tuning', type=music.Guitar.parse_tuning, default=None,
        help='A json dict specifying a different guitar tuning, e.g.: {"D": "D2", "A": "A2", ...}'
    )
    guitar_positions_parser.add_argument(
        '--capo', type=int, default=0,
        help='An int specifying where to fret a capo'
    )
    guitar_positions_parser.add_argument(
        '--frets', type=int, default=music.Guitar.DEFAULT_FRETS,
        help='How many frets on the guitar'
    )
    guitar_positions_parser.add_argument(
        '--parallel', '-p', action='store_true',
        help='Use parallel processing for calculations'
    )
    guitar_positions_parser.set_defaults(func=guitar_positions)

    guitar_optimal_progression_parser = subparsers.add_parser(
        'guitar-chord-progression', help='Given a chord progression, show the optimal guitar positions'
    )
    guitar_optimal_progression_parser.add_argument(
        '--chords', nargs='+', help='A chord progression, e.g. `Dm7 G7 CM7`'
    )
    guitar_optimal_progression_parser.add_argument(
        '--graphical', '-g', action='store_true',
        help='Show ASCII art for guitar positions'
    )
    guitar_optimal_progression_parser.set_defaults(func=guitar_optimal_progression)

    voice_leading_parser = subparsers.add_parser(
        'voice-leading', help='Given a chord progression, compute the optimal voicings'
    )
    voice_leading_parser.add_argument(
        '--chords', nargs='+', help='A chord progression, e.g. `Dm7 G7 CM7`'
    )
    voice_leading_parser.add_argument(
        '--lower', type=str, help='Lower bound for voicings', default='C2'
    )
    voice_leading_parser.add_argument(
        '--upper', type=str, help='Upper bound for voicings', default='C5'
    )
    voice_leading_parser.set_defaults(func=voice_leading)

    args = parser.parse_args()
    t1 = time.time()
    args.func(args)
    t2 = time.time()
    print(f'(Computed in {(t2 - t1):.2f} seconds)')


if __name__ == "__main__":
    main()