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
        help='A chord name, like Bbmaj7; currently gives a chord in close root position '
             'with lowest possible root for guitar tuning'
    )
    parser.add_argument(
        '--top_n', type=int, default=5, help='How many positions to return'
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
    elif args.name:
        chord = notes.ChordName(args.name).get_close_chord(lower=guitar.lowest)
        print(chord)
    else:
        raise ValueError('Either `notes` or `name` is required')
    positions = chord.guitar_positions(guitar=guitar)[:args.top_n]
    print(f'Here are the top {args.top_n} guitar positions for the chord: {chord} with a guitar tuned to: {guitar}')
    for p in positions:
        print('\n' + '\n'.join(p.printable())) if args.graphical else print(p)