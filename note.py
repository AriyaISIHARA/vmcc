from collections import deque
from logging import getLogger
import re

from error import VmccError


logger = getLogger(__name__)


_REGEX_NOTE = re.compile(''.join([
    r'(?:'
    r'(?P<signature>[cdfg](?:[ie]s)?|[eah](?:is)?|[ea]s|b(?P<octave>[0-9]*))',
    r'|(?P<octaveset>o[0-9]+)|(?P<octaveinc><)|(?P<octavedec>>)|(?P<repeat>-)|(?P<tacet>.)',
    r'|(?P<lpar>\()|(?P<rpar>\)(?P<rpar_scale>[0-9]*))',
    r')\s*',
]))
_KEY_MAP = {
    'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 10, 'h': 11,
}
_SCALE_NAMES = [
    'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B',
]


def scale_name(scale_key):
    octave = scale_key // 12
    name = _SCALE_NAMES[scale_key % 12]
    return '%s%d' % (name, octave)


class Note:
    def __init__(self, signature, octave, length, pos):
        self.signature = signature
        self.octave = octave
        self.length = length
        self.pos = pos

    @property
    def displaytext(self):
        return f"<{self.pos}:{self.length}@{self.signature}{self.octave}>"

    @property
    def is_normal(self):
        return self.octave is not None

    @property
    def is_repeat(self):
        return self.signature == '-'

    @property
    def is_tacet(self):
        return self.signature == '.'

    def __add__(self, other):
        unifiable = False
        if self.is_normal and other.is_repeat:
            unifiable = True
        elif self.is_tacet and other.is_tacet:
            unifiable = True
        if not unifiable:
            return None
        return Note(self.signature, self.octave, self.length + other.length, self.pos)

    def get_key(self, env, default=None):
        if not self.is_normal:
            return default
        signature = self.signature
        key = self.octave * 12 + _KEY_MAP[signature[0]]
        if signature.endswith('is'):
            key += 1
        elif signature.endswith('s'):
            key -= 1
        if key < env.lowest_key:
            return env.lowest_key
        if key > env.highest_key:
            return env.highest_key
        return key

    @classmethod
    def parse_melody(cls, env, text, lineno=None, chars=1):
        if lineno is None:
            lineno = env.lineno
        textlen = len(text)
        pos = 0
        melody = deque()
        par = None
        while pos < textlen:
            item = text[pos:]
            # logger.debug("item:%s", item)
            m = _REGEX_NOTE.match(item)
            if not m:
                raise VmccError(f"L{lineno}:{pos + chars}:'{item}' unrecognizable")
            d = m.groupdict()
            signature = d['signature']
            note_pos = pos + chars
            pos += m.end()
            if par is None:
                scale = env.tick_unit
                q = melody
            else:
                scale = None
                q = par
            if signature:
                octavestr = d['octave']
                octave = int(octavestr) if octavestr else env.octave
                q.append(cls(signature, octave, scale, note_pos))
            elif d['octaveinc']:
                env.octave += 1
            elif d['octavedec']:
                env.octave -= 1
            elif d['repeat']:
                q.append(cls('-', None, scale, note_pos))
            elif d['tacet']:
                q.append(cls('.', None, scale, note_pos))
            elif d['lpar']:
                if par is not None:
                    raise VmccError(f"L{lineno}:{pos + chars}:'{item}' nested parentheses are not supported")
                par = []
            elif d['rpar']:
                if par is None:
                    raise VmccError(f"L{lineno}:{pos + chars}:'{item}' unbalanced right parenthesis")
                if not par:
                    raise VmccError(f"L{lineno}:{pos + chars}:'{item}' empty parentheses")
                rpar_scale = d['rpar_scale']
                if rpar_scale:
                    numerator = int(rpar_scale) or 1
                else:
                    numerator = 1
                resource = numerator * env.tick_unit
                rest = len(par)
                for note in par:
                    if rest == 1:
                        subscale = resource
                    else:
                        subscale = round(resource / rest)
                    note.length = subscale
                    melody.append(note)
                    resource -= subscale
                    rest -= 1
                par = None
            else:
                octaveset = d['octaveset']
                assert octaveset
                env.octave = int(octaveset[2:])
        return melody


class Notes:
    @classmethod
    def unify(cls, notes):
        unified_notes = deque([notes[0]])
        for note in notes[1:]:
            unified = unified_notes[-1] + note
            if unified:
                unified_notes[-1] = unified
            else:
                unified_notes.append(note)
        return unified_notes
