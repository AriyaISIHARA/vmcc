import re

from error import VmccError


_BREATHES = (0, 34, 46, 51, 57, 60, 80)
_REGEX_SYLLABLE = re.compile(''.join([
    r'(?P<consonant>[bdfghjklmnprstvwyz]*(?:_[bdfghjklmnprstvwyz]*)*)',  # consonant
    r'(?P<breath>[0-9]*)',                                            # breath
    r'(?P<vowel>[aeiou]*(?:_[aeiou]*)*)',                                 # vowel
    r'(?P<suffix>[bdfghjklmnprstvwyz]*(?:_[bdfghjklmnprstvwyz]*)*)',      # suffix
    '$',
]))


def breath_text(breathstr):
    if not breathstr:
        return ''
    breath = int(breathstr)
    middles = [(low + high) // 2 for (low, high) in zip(_BREATHES, _BREATHES[1:])]
    for threshold, b in zip(middles, _BREATHES):
        if breath < threshold:
            final_breath = b
    else:
        final_breath = _BREATHES[-1]
    return 'breath%d' % final_breath

class Syllable:
    def __init__(self, consonant, breath, vowel, suffix, pos):
        self.consonant = consonant
        self.breath = breath
        self.vowel = vowel
        self.suffix = suffix
        self.pos = pos

    @property
    def displaytext(self):
        return f"{self.consonant}{self.breath}{self.vowel}{self.suffix}"

    @classmethod
    def parse(cls, text, lineno=0, chars=1):
        m = _REGEX_SYLLABLE.match(text)
        if not m:
            raise VmccError(f"L{lineno}:{chars}:'{text}' unrecognizable")
        return cls(**m.groupdict(), pos=chars)
