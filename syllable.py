import re

from error import VmccError


_BREATHES = (34, 46, 51, 57, 60, 80)
_REGEX_SYLLABLE = re.compile(''.join([
    r'(?P<consonant>[bdfghjklmnprstvwyz]*(?:_[bdfghjklmnprstvwyz]*)*)',  # consonant
    r'(?P<breath>[0-9]*)',                                            # breath
    r'(?P<vowel>[aeiou]*(?:_[aeiou]*)*)',                                 # vowel
    r'(?P<suffix>[bdfghjklmnprstvwyz]*(?:_[bdfghjklmnprstvwyz]*)*)',      # suffix
    '$',
]))



class Syllable:
    def __init__(self, consonant, breath, vowel, suffix, pos):
        self.consonant = consonant
        self.breath = breath
        self.vowel = vowel
        self.suffix = suffix
        self.pos = pos

    @classmethod
    def parse(cls, text, lineno=0, chars=1):
        m = _REGEX_SYLLABLE.match(text)
        if not m:
            raise VmccError(f"L{lineno}:{chars}:'{text}' unrecognizable")
        return cls(**m.groupdict(), pos=chars)
