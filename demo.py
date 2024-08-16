import argparse

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
        chords = notes.ChordName(args.name).get_all_chords(lower=guitar.lowest, upper=guitar.highest)
        positions_all = []
        for chord in chords:
            positions_all += chord.guitar_positions(guitar=guitar)
    else:
        raise ValueError('Either `notes` or `name` is required')
    positions_playable = list(filter(lambda x: x.playable, positions_all))
    positions = notes.sort_guitar_positions(positions_playable)[:args.top_n]
    tuning_display = guitar.tuning_name if guitar.tuning_name == 'standard' else f'{guitar.tuning_name} ({guitar}):'
    print(
        f'There are {len(positions_playable)} playable guitar positions (out of {len(positions_all)} possible) '
        f'for a guitar tuned to {tuning_display}.'
    )
    if args.top_n:
        print(f'Here are the top {args.top_n}:')
    for p in positions:
        print('\n' + '\n'.join(p.printable())) if args.graphical else print(p)