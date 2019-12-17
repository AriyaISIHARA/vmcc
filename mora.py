from logging import getLogger
import math

from error import VmccError
from note import Notes, scale_name
from syllable import breath_text


logger = getLogger(__name__)


REFRAIN_TICK = 44
MAX_CONSONANT_TICK = 30
MIN_SUFFIX = 15


class Mora:
    def __init__(
            self, *,
            attenuation=None,
            consonant1=None,
            consonant2=None,
            vowel=None,
            scale,
            tick,
            on_tick=None,
            off_tick=None,
            tenseness=None,
            pitchbend=None,
    ):
        self.attenuation = attenuation or 0
        self.consonant1 = consonant1 or ''
        self.consonant2 = consonant2 or ''
        self.vowel = vowel or ''
        self.scale = scale
        self.tick = tick
        self.on_tick = on_tick or 0
        self.off_tick = off_tick or 0
        self.tenseness = tenseness or 0
        self.pitchbend = pitchbend or ()

    @property
    def displaytext(self):
        return ','.join([
            str(getattr(self, key)) for key in (
                'attenuation', 'consonant1', 'breath_text', 'vowel',
                'scale_name', 'tick', 'on_tick', 'off_tick', 'tenseness',
            )
        ])

    @property
    def scale_name(self):
        return scale_name(self.scale, pitchbend=self.pitchbend)

    @property
    def breath_text(self):
        return breath_text(self.consonant2)

    def write(self, file=None):
        print(self.displaytext, file=file)

    @property
    def vowel_tick(self):
        return self.tick - (self.on_tick + self.off_tick)

    def refrain_pitchbend(self, next_mora):
        if self.scale != next_mora.scale:
            pitchbend = (0,) * math.ceil(self.tick / REFRAIN_TICK)
            refrained_mora = Mora(
                attenuation=self.attenuation,
                consonant1=self.consonant1,
                consonant2=self.consonant2,
                vowel=self.vowel,
                scale=self.scale,
                tick=self.tick - 1,
                on_tick=self.on_tick,
                off_tick=self.off_tick,
                tenseness=self.tenseness,
                pitchbend=pitchbend,
            )
            # logger.debug("refrained mora: %s", refrained_mora.displaytext)
            return (refrained_mora,)
        return (self,)


class Morae:
    def __init__(self, env):
        self._env = env

        self._morae = []
        self._current_syllable = None
        self._current_notes = []
        self._postponed = None

    def _last_morae(self):
        return self._morae[-1] if self._morae else None

    def feed_syllable(self, syllable):
        if self._current_syllable:
            self._proceed_syllable()
        self._current_syllable = syllable

    def feed_note(self, note):
        if self._current_notes:
            last_note = self._current_notes[-1]
            if last_note.is_tacet and not note.is_tacet:
                raise VmccError(
                    "tacet should be placed at the end of a syllable " +
                    f"@ L{self._env.lineno}:{last_note.pos}:'{last_note.displaytext}{note.displaytext}'"
                )
        self._current_notes.append(note)

    def get_morae(self):
        if self._current_syllable:
            self._proceed_syllable()
        if self._postponed:
            length, consonant = self._postponed
            if consonant:
                if length > MAX_CONSONANT_TICK + 1:
                    self._postponed = MAX_CONSONANT_TICK + 1, consonant
                self._proceed_single_postponed()
            else:
                self._postponed = None
        self._refrain_pitchbend()
        return self._morae

    def _proceed_syllable(self):
        # logger.info(
        #     f"syl:{self._current_syllable.displaytext}, " +
        #     f"notes:{' '.join([n.displaytext for n in self._current_notes])}"
        # )
        unified_notes = Notes.unify(self._current_notes)
        self._current_notes = []

        syllable = self._current_syllable
        
        suffix_tacet = 0
        while unified_notes[-1].is_tacet:
            suffix_tacet += unified_notes.pop().length

        suffix_consonant = self._current_syllable.suffix
        if suffix_consonant and unified_notes[-1].length < MIN_SUFFIX:
            suffix_consonant = None

        scale = None
        if self._morae:
            scale = self._morae[-1].scale

        # logger.debug(
        #     "syllable: %s  suf-tac: %d suf-cons: %s postponed: %s",
        #     syllable.displaytext, suffix_tacet, suffix_consonant, self._postponed
        # )
        for idx, note in enumerate(unified_notes):
            first = idx == 0
            last = idx + 1 == len(unified_notes)
            # logger.debug("unified_notes#%d: %s", idx, note.displaytext)
            consonant1 = None
            consonant2 = None
            vowel = syllable.vowel
            scale = note.get_key(self._env, default=scale)
            assert scale is not None
            tick = note.length
            on_tick = 0
            off_tick = 0
            suffix_length = 0
            if last and suffix_consonant:
                suffix_length = min(self._env.maximal_suffix, tick // 2)
                tick -= suffix_length
            if first:
                consonant1 = syllable.consonant
                consonant2 = syllable.breath
                off_tick = min(MAX_CONSONANT_TICK, tick // 2)
                if self._postponed:
                    p_tick, p_consonant = self._postponed
                    if not p_consonant:
                        tick += p_tick
                        on_tick += p_tick
                        self._postponed = None
                    elif consonant1 == p_consonant:
                        tick += p_tick
                        off_tick += p_tick
                        self._postponed = None
                    else:
                        self._proceed_single_postponed()
            mora = Mora(
                consonant1=consonant1, consonant2=consonant2, vowel=vowel,
                scale=scale, tick=tick, on_tick=on_tick, off_tick=off_tick
            )
            # logger.debug("mora: %s", mora.displaytext)
            self._morae.append(mora)
            if suffix_length:
                self._postponed = suffix_length, syllable.suffix
        if suffix_tacet:
            if self._postponed:
                self._proceed_single_postponed()
            self._postponed = suffix_tacet, None
            # logger.debug("postpone set: %s", self._postponed)

    def _refrain_pitchbend(self):
        morae = []
        prev_mora = self._morae[0]
        for mora in self._morae[1:]:
            morae += prev_mora.refrain_pitchbend(mora)
            prev_mora = mora
        morae.append(prev_mora)
        self._morae = morae

    def _proceed_single_postponed(self):
        tick, consonant1 = self._postponed
        assert consonant1
        scale = self._morae[-1].scale
        off_tick = tick - 1
        mora = Mora(tick=tick, consonant1=consonant1, scale=scale, off_tick=off_tick)
        # logger.info("single cons.: %s", mora.displaytext)
        self._morae.append(mora)
        self._postponed = None

    def merge(self):
        env = self._env
        lyrics = env.lyrics
        melody = env.melody
        while melody:
            note = melody.popleft()
            while lyrics and lyrics[0].pos <= note.pos:
                self.feed_syllable(lyrics.popleft())
            self.feed_note(note)
        if lyrics:
            syllable = lyrics[0]
            raise VmccError(f"no note for syllable '{syllable}' @ L{env.lineno}:{syllable.pos}")
