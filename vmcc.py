from collections import deque
import logging
import re
import sys

from note import Note
from syllable import Syllable


logger = logging.getLogger(__name__)


def _tempo_to_scale_unit(tempo):
    return int(440 * 60 / tempo + .5)


class Environment:
    def __init__(
            self, *,
            lowest_key=0,  # C0
            highest_key=127,  # G10
            scale_unit=0,
            tempo=0,
            octave=4,
            transpose=0,
    ):
        self.settables = ('scale_unit', 'tempo', 'octave', 'transpose')
        self.lowest_key = lowest_key
        self.highest_key = highest_key
        if scale_unit:
            assert not tempo
            self.scale_unit = scale_unit
        else:
            self.scale_unit = _tempo_to_scale_unit(tempo or 120)
        self.octave = octave
        self.transpose = transpose
        self.lyrics = None
        self.melody = None
        self.lineno = 0
        self.morae = []

    def feed_line(self, line):
        self.lineno += 1
        if line.isspace():
            pass
        elif line.startswith('!'):  # comments
            pass
        elif line.startswith('#'):  # pragmas
            items = line.strip().split()
            assert len(items) == 3
            pragma = items[1]
            assert pragma in self.settables
            paramstr = items[2]
            assert paramstr.isnumeric()
            param = int(paramstr)
            logger.info("L%d: %s = %d", self.lineno, pragma, param)
            if pragma == 'tempo':
                pragma = 'scale_unit'
                param = _tempo_to_scale_unit(param)
            setattr(self, pragma, param)
        elif self.lyrics:
            self._feed_melody(line)
            self._merge()
        else:
            items = tuple((m.group(), m.start() + 1) for m in re.finditer(r'\S+', line))
            self._feed_lyrics(items)

    def _feed_lyrics(self, items):
        lyrics = deque()
        for item, chars in items:
            syllable = Syllable.parse(item, self.lineno, chars)
            lyrics.append(syllable)
        self.lyrics = lyrics
        
    def _feed_melody(self, line):
        self.melody = Note.parse_melody(self, line)
        for note in self.melody:
            logger.info(note.displaytext)

    def _merge(self):
        assert self.lyrics and self.melody
        # TBA
        self.lyrics = None
        self.melody = None
        

def _main(fin):
    env = Environment()
    for line in fin:
        env.feed_line(line)
        

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s @ %(filename)s:%(lineno)d : %(message)s"
    )
    _main(sys.stdin)
