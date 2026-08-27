import io
import os
from typing import Optional

import matplotlib
import matplotlib.pyplot as plt

from music.primitives import Chord

matplotlib.use('Agg')
IMAGE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static')


class Staff:
    """
    This class defines a (grand) music staff, which contains a sequence of zero or more chords.
    This implies how many additional ledger lines are needed for each chord in the sequence.
    At present, there is no notion of "time" or "meter", and all chords are whole notes with no bar lines.

    Attributes:
        - chords: list[Chord]
        - ledger_lines: list[tuple[int, int]], for each chord, the number of additional ledger lines
            above or below the grand staff that are needed
    """
    def __init__(self, chords: Optional[list[Chord]] = None):
        # ledger line 0 is middle C, one int index for each line or space
        self.chords = chords or []
        self.ledger_lines = []
        for chord in self.chords:
            self.ledger_lines.append((
                min((min(chord.notes).staff_line + 1) & ~1, 2),
                max(max(chord.notes).staff_line & ~1, 10)
            ))

    def generate_fig(self) -> plt.Figure:
        figsize = (len(self.chords) + 1, 1.75)
        fig, ax = plt.subplots(figsize=figsize)
        # matplotlib axes will have origin (0, 0) at left of staff, middle c, so staff goes from y = 2 to 10
        xlim = [0.5, 10 + 6 * len(self.chords) - 3]
        ylim = [2, 10]  # noqa: F841
        note_positions = [10 + 6 * n for n in range(len(self.chords))]
        note_rad = 1
        # clef
        im = plt.imread(os.path.join(IMAGE_DIR, 'treble_clef.png'))
        ax.imshow(im, extent=(1, 5, -1, 12))
        im = plt.imread(os.path.join(IMAGE_DIR, 'bass_clef.png'))
        ax.imshow(im, extent=(1, 6, -9, -2))
        # staff
        for line in range(2, 12, 2):
            ax.plot(xlim, [line] * 2, 'k-')
        for line in range(-2, -12, -2):
            ax.plot(xlim, [line] * 2, 'k-')
        for chord, (lowest_line, highest_line), note_pos in zip(self.chords, self.ledger_lines, note_positions):
            if lowest_line < -10:
                for line in range(lowest_line, 10, 2):
                    ax.plot([note_pos - 2 * note_rad, note_pos + 2 * note_rad], [line] * 2, 'k-')
            if highest_line > 10:
                for line in range(12, highest_line + 2, 2):
                    ax.plot([note_pos - 2 * note_rad, note_pos + 2 * note_rad], [line] * 2, 'k-')
            shift = 0
            for note, gap in zip(chord.notes, chord.staff_line_gaps):
                if shift == 0 and gap is not None and gap < 2:
                    shift = 1.75 * note_rad
                else:
                    shift = 0
                note_pos_ = note_pos + shift
                ax.add_patch(plt.Circle(xy=(note_pos_, note.staff_line), radius=0.9 * note_rad, facecolor="none", edgecolor='k'))
                ax.annotate(note.modifier, xy=(note_pos_ - 2.25 * note_rad, note.staff_line - 0.6), fontsize=12, family='arial')
                if note.staff_line == 0:
                    ax.plot([note_pos_ - 2 * note_rad, note_pos_ + 2 * note_rad], [0, 0], 'k-')
        ax.set_aspect(0.9)
        ax.axis('off')
        plt.tight_layout()
        plt.close()
        return fig

    def write_png(self, path: Optional[str] = None) -> Optional[bytes]:
        if not path:
            buffer = io.BytesIO()
            self.generate_fig().savefig(buffer, bbox_inches='tight', pad_inches=0)
            buffer.seek(0)
            return buffer.read()
        else:
            self.generate_fig().savefig(path, bbox_inches='tight', pad_inches=0)

