import argparse
import notes

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Given a chord from a set of notes, show the corresponding guitar positions',
    )
    parser.add_argument('--notes', type=str, help='A comma separated list of notes, e.g. `C3,G3,Eb4`')
    parser.add_argument('--top_n', type=int, default=5, help='How many positions to return')
    parser.add_argument('--graphical', '-g', action='store_true', help='Show ASCII art for guitar positions')
    args = parser.parse_args()
    note_list = [notes.Note.from_string(note) for note in args.notes.split(',')]
    chord = notes.Chord(note_list)
    positions = chord.guitar_positions()[:args.top_n]
    print(f'Here are the top {args.top_n} guitar positions for the chord: {chord}')
    for p in positions:
        print('\n' + '\n'.join(p.printable())) if args.graphical else print(p)