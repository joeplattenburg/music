import notes

if __name__ == "__main__":
    print("Here's a demo!")
    note_list = [
        notes.Note('C', 3),
        notes.Note('G', 3),
        notes.Note('E', 4),
        notes.Note('Bb', 4),
    ]
    chord = notes.Chord(note_list)
    print(f"Get the guitar positions for for the C7 chord: {chord}")
    print("(In order of lowest to highest fret span)")
    positions = chord.guitar_positions()
    for p in positions:
        print(p)