import argparse
import time

import music

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Given a chord, show the corresponding guitar positions',
    )
    parser.add_argument(
        '--notes', type=str, help='A comma separated list of notes, e.g. `C3,G3,Eb4`'
    )
    parser.add_argument(
        '--name', type=str,
        help='A chord name, like Bbmaj7/D; will return all possible voicings'
    )
    parser.add_argument(
        '--top_n', '-n', type=int, default=None,
        help='How many positions to return'
    )
    parser.add_argument(
        '--max_fret_span', '-f', type=int, default=music.DEFAULT_MAX_FRET_SPAN,
        help='Max fret span to consider playable'
    )
    parser.add_argument(
        '--allow_repeats', '-r', action='store_true',
        help='Allow chord tones to appear more than once (different octaves)'
    )
    parser.add_argument(
        '--allow_identical', '-i', action='store_true',
        help='Allow chord tones to appear more than once in the same octave'
    )
    parser.add_argument(
        '--graphical', '-g', action='store_true',
        help='Show ASCII art for guitar positions'
    )
    parser.add_argument(
        '--tuning', type=music.Guitar.parse_tuning, default=None,
        help='A json dict specifying a different guitar tuning, e.g.: {"D": "D2", "A": "A2", ...}'
    )
    parser.add_argument(
        '--capo', type=int, default=0,
        help='An int specifying where to fret a capo'
    )
    parser.add_argument(
        '--frets', type=int, default=music.Guitar.DEFAULT_FRETS,
        help='How many frets on the guitar'
    )
    parser.add_argument(
        '--parallel', '-p', action='store_true',
        help='Use parallel processing for calculations'
    )

    args = parser.parse_args()
    t1 = time.time()
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
    t2 = time.time()
    tuning_display = guitar.tuning_name if guitar.tuning_name == 'standard' else f'{guitar.tuning_name} ({guitar}):'
    print(
        f'There are {len(chords_playable)} playable voicings and {len(positions_playable)} guitar positions '
        f'(out of {positions_all_count} possible) for a guitar tuned to {tuning_display}.\n'
        f'(Computed in {(t2 - t1):.2f} seconds)'
    )
    if args.top_n:
        print(f'Here are the top {args.top_n}:')
    for p in positions:
        print('\n' + '\n'.join(p.printable())) if args.graphical else print(p)
