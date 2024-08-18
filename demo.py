import argparse
import time

import notes

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
        '--top_n', '-n', type=int, default=None, help='How many positions to return'
    )
    parser.add_argument(
        '--allow_repeats', '-r', action='store_true', help='Allow chord tones to appear more than once'
    )
    parser.add_argument(
        '--allow_redundant', '-R', action='store_true', help='Allow redundant positions (fully above fret 12)'
    )
    parser.add_argument(
        '--graphical', '-g', action='store_true', help='Show ASCII art for guitar positions'
    )
    parser.add_argument(
        '--tuning', type=notes.Guitar.parse_tuning, default=None,
        help='A json dict specifying a different guitar tuning, e.g.: {"D": "D2", "A": "A2", ...}'
    )
    parser.add_argument(
        '--capo', type=int, default=0, help='An int specifying where to fret a capo'
    )
    parser.add_argument(
        '--frets', type=int, default=22, help='How many frets on the guitar'
    )

    args = parser.parse_args()
    guitar = notes.Guitar(tuning=args.tuning, capo=args.capo, frets=args.frets)
    if args.notes:
        note_list = [notes.Note.from_string(note) for note in args.notes.split(',')]
        chord = notes.Chord(note_list)
        print(f'You input the chord: {chord}')
        positions_all = chord.guitar_positions(guitar=guitar)
    elif args.name:
        print(f'You input the chord: {args.name}')
        t1 = time.time()
        chords = notes.ChordName(args.name).get_all_chords(
            lower=guitar.lowest, upper=guitar.highest,
            allow_repeats=args.allow_repeats, max_notes=len(guitar.tuning)
        )
        t2 = time.time()
        positions_all = []
        for chord in chords:
            positions_all += chord.guitar_positions(guitar=guitar)
        t3 = time.time()
    else:
        raise ValueError('Either `notes` or `name` is required')
    positions_playable = list(filter(lambda x: x.playable, positions_all))
    if not args.allow_redundant:
        positions_playable = list(filter(lambda x: not x.redundant, positions_playable))
    if args.allow_repeats:
        positions_playable = notes.filter_subset_guitar_positions(positions_playable)
    positions = notes.sort_guitar_positions(positions_playable)[:args.top_n]
    t4 = time.time()
    print('Times:')
    print(f'Get chords ({len(chords)}): {(t2 - t1):.3f} seconds')
    print(f'Get positions ({len(positions_all)}): {(t3 - t2):.3f} seconds')
    print(f'Filter positions ({len(positions)}): {(t4 - t3):.3f} seconds')
    tuning_display = guitar.tuning_name if guitar.tuning_name == 'standard' else f'{guitar.tuning_name} ({guitar}):'
    print(
        f'There are {len(positions_playable)} playable guitar positions (out of {len(positions_all)} possible) '
        f'for a guitar tuned to {tuning_display}.'
    )
    if args.top_n:
        print(f'Here are the top {args.top_n}:')
    for p in positions:
        print('\n' + '\n'.join(p.printable())) if args.graphical else print(p)
