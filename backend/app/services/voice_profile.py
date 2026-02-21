"""Voice profile generation and consistency analysis service."""

import re
import uuid
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException

from ..models.character import Character, DialogueLine
from ..models.voice_profile import ConsistencyFlag, ManuscriptLocation, VoiceDimension, VoiceProfile
from .supabase import supabase_client

# Module-level tracking for dismissed flags (mock DB update doesn't persist)
_dismissed_flag_ids: set = set()

# Cache for generated profiles {character_id: VoiceProfile}
_profile_cache: Dict[str, VoiceProfile] = {}

# Cache for generated flags {character_id: List[ConsistencyFlag]}
_flags_cache: Dict[str, List[ConsistencyFlag]] = {}

# Strong informal words/patterns that push formality toward 0
INFORMAL_WORDS = {
    "yo", "sup", "dude", "bro", "bruh", "brah", "gonna", "wanna", "gotta",
    "nah", "yeah", "yep", "yup", "whatever", "chill", "awesome", "totally",
    "kinda", "sorta", "lemme", "gimme", "ain't", "cool", "like", "hey",
    "ugh", "jeez", "whoa", "omg", "wtf", "lol", "dunno",
}

# Strong formal words that push formality toward 1
FORMAL_WORDS = {
    "indeed", "therefore", "thus", "hence", "furthermore", "moreover",
    "henceforth", "consequently", "accordingly", "hitherto", "whereupon",
    "quite", "rather", "shall", "ought", "must", "propose", "suggest",
    "believe", "analyze", "examine", "proceed", "ascertain", "determine",
    "certainly", "undoubtedly", "respectfully", "formally", "precisely",
    "nevertheless", "however", "nonetheless",
}

# Contraction pattern (mild informal marker)
CONTRACTIONS_RE = re.compile(
    r"\b(?:don't|can't|won't|isn't|aren't|wasn't|weren't|hasn't|haven't|"
    r"hadn't|doesn't|didn't|couldn't|shouldn't|wouldn't|i'm|i'll|i've|i'd|"
    r"you're|you'll|you've|you'd|he's|she's|it's|we're|we'll|we've|we'd|"
    r"they're|they'll|they've|they'd|don'tcha|fixin'|lookin'|gonna|wanna|gotta)\b",
    re.IGNORECASE,
)


class VoiceProfileService:
    """Generates voice profiles and consistency analyses for characters."""

    def __init__(self):
        self.client = supabase_client

    def _formality_score(self, text: str) -> float:
        """
        Compute a formality score for a dialogue line.
        0.0 = very informal, 1.0 = very formal, 0.5 = neutral.
        """
        text_lower = text.lower()
        words = [w.strip('.,!?;:"\'()[]') for w in text_lower.split()]
        words = [w for w in words if w]

        if not words:
            return 0.5

        # Start neutral
        score = 0.5

        # Penalty per informal word
        informal_count = sum(1 for w in words if w in INFORMAL_WORDS)
        score -= informal_count * 0.25

        # Bonus per formal word
        formal_count = sum(1 for w in words if w in FORMAL_WORDS)
        score += formal_count * 0.25

        # Mild penalty for contractions
        contraction_count = len(CONTRACTIONS_RE.findall(text_lower))
        score -= contraction_count * 0.10

        return min(1.0, max(0.0, score))

    def _avg_word_length(self, text: str) -> float:
        """Average word length of the text."""
        words = text.split()
        if not words:
            return 0.0
        return sum(len(w.strip('.,!?;:"\'')) for w in words) / len(words)

    def _avg_sentence_length(self, lines: List[str]) -> float:
        """Average number of words per dialogue line."""
        if not lines:
            return 0.0
        return sum(len(line.split()) for line in lines) / len(lines)

    def _detect_verbal_tics(self, dialogue_texts: List[str]) -> List[str]:
        """Detect repeated phrases or words that form verbal tics."""
        # Count 1-gram and 2-gram frequencies
        word_counts: Counter = Counter()
        bigram_counts: Counter = Counter()

        for text in dialogue_texts:
            words = [w.lower().strip('.,!?;:"\'') for w in text.split() if len(w) > 2]
            word_counts.update(words)
            for i in range(len(words) - 1):
                bigram_counts[(words[i], words[i + 1])] += 1

        tics = []
        total = len(dialogue_texts)
        threshold = max(2, total * 0.15)  # Appears in 15%+ of lines

        # Single word tics
        for word, count in word_counts.most_common(10):
            if count >= threshold and word not in {"the", "and", "but", "for", "not", "you", "are", "was"}:
                tics.append(word)
                if len(tics) >= 3:
                    break

        # Bigram tics
        for (w1, w2), count in bigram_counts.most_common(5):
            if count >= threshold:
                tics.append(f"{w1} {w2}")

        return tics[:5]

    def _select_quotes(
        self, dialogue_texts: List[str], criterion: str, n_min: int = 3, n_max: int = 5
    ) -> List[str]:
        """
        Select representative quotes for a dimension.
        Returns n_min–n_max verbatim dialogue texts.
        """
        unique_texts = list(dict.fromkeys(dialogue_texts))  # preserve order, deduplicate

        if criterion == "vocabulary_level":
            # Sort by average word length (more complex vocabulary first)
            sorted_texts = sorted(
                unique_texts,
                key=lambda t: self._avg_word_length(t),
                reverse=True,
            )
        elif criterion == "sentence_structure":
            # Sort by sentence length (longest first)
            sorted_texts = sorted(unique_texts, key=lambda t: len(t.split()), reverse=True)
        elif criterion == "verbal_tics":
            # Lines that contain detected tics come first
            tics = self._detect_verbal_tics(unique_texts)
            def tic_score(text: str) -> int:
                t_lower = text.lower()
                return sum(1 for tic in tics if tic in t_lower)
            sorted_texts = sorted(unique_texts, key=tic_score, reverse=True)
        elif criterion == "formality":
            # Sort by formality score
            sorted_texts = sorted(unique_texts, key=self._formality_score, reverse=True)
        else:
            sorted_texts = unique_texts

        n = min(n_max, max(n_min, min(n_max, len(sorted_texts))))
        return sorted_texts[:n]

    def _generate_flags_for_character(
        self,
        character: Character,
        full_text: str,
    ) -> List[ConsistencyFlag]:
        """
        Detect voice inconsistency flags for a character.

        A flag is generated when a dialogue line's formality deviates significantly
        from the character's overall voice profile.
        """
        dialogue_lines = character.dialogue_lines
        if not dialogue_lines:
            return []

        # Compute formality score per unique line
        unique_lines: Dict[str, DialogueLine] = {}
        for line in dialogue_lines:
            if line.text not in unique_lines:
                unique_lines[line.text] = line

        texts = list(unique_lines.keys())
        scores = {text: self._formality_score(text) for text in texts}

        if not scores:
            return []

        mean_score = sum(scores.values()) / len(scores)

        flags: List[ConsistencyFlag] = []

        for text, score in scores.items():
            line = unique_lines[text]
            deviation = abs(score - mean_score)
            flag_needed = False
            severity: str = "low"

            # Very informal line in a mostly formal/neutral character
            if score <= 0.25 and mean_score >= 0.4:
                flag_needed = True
                severity = "high" if score == 0.0 else "medium"

            # Very formal line in a mostly informal character
            elif score >= 0.75 and mean_score <= 0.4:
                flag_needed = True
                severity = "high"

            # Large deviation from mean regardless of direction
            elif deviation >= 0.35:
                flag_needed = True
                if deviation >= 0.5:
                    severity = "high"
                else:
                    severity = "medium"

            if flag_needed:
                # Determine which dimension is flagged
                dimension = "formality"

                flags.append(
                    ConsistencyFlag(
                        id=str(uuid.uuid4()),
                        character_id=character.id,
                        project_id=character.project_id,
                        severity=severity,  # type: ignore[arg-type]
                        dimension=dimension,
                        manuscript_location=ManuscriptLocation(
                            chapter=line.chapter_index,
                            paragraph=line.paragraph_index,
                        ),
                        passage=text,
                        dismissed=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )

        return flags

    def _compute_score(self, all_flags: List[ConsistencyFlag]) -> float:
        """
        Compute consistency score 0-100 based on active (non-dismissed) flags.
        Dismissing all flags yields exactly 100.
        """
        active_flags = [f for f in all_flags if f.id not in _dismissed_flag_ids]
        if not active_flags:
            return 100.0

        penalty_map = {"low": 5, "medium": 15, "high": 25}
        total_penalty = sum(penalty_map.get(f.severity, 10) for f in active_flags)
        return max(0.0, 100.0 - total_penalty)

    def generate_profile(self, character: Character, full_text: str) -> VoiceProfile:
        """
        Generate a voice profile for a character using rule-based analysis.

        Falls back gracefully if there are too few dialogue lines.
        """
        dialogue_lines = character.dialogue_lines
        dialogue_texts = [line.text for line in dialogue_lines]

        warning = None
        if character.dialogue_line_count < 20:
            warning = (
                f"Only {character.dialogue_line_count} dialogue lines available. "
                "Profile may not be fully representative."
            )

        # Generate flags first (needed for score)
        if character.id not in _flags_cache:
            flags = self._generate_flags_for_character(character, full_text)
            _flags_cache[character.id] = flags

        flags = _flags_cache[character.id]
        score = self._compute_score(flags)

        # Build profile dimensions
        vocab_quotes = self._select_quotes(dialogue_texts, "vocabulary_level")
        struct_quotes = self._select_quotes(dialogue_texts, "sentence_structure")
        tics_quotes = self._select_quotes(dialogue_texts, "verbal_tics")
        formality_quotes = self._select_quotes(dialogue_texts, "formality")

        avg_word_len = self._avg_word_length(" ".join(dialogue_texts[:20]))
        avg_sent_len = self._avg_sentence_length(dialogue_texts[:20])
        tics = self._detect_verbal_tics(dialogue_texts)
        mean_formality = (
            sum(self._formality_score(t) for t in dialogue_texts) / len(dialogue_texts)
            if dialogue_texts else 0.5
        )
        formality_label = (
            "formal" if mean_formality >= 0.65
            else "informal" if mean_formality <= 0.35
            else "neutral"
        )

        profile = VoiceProfile(
            character_id=character.id,
            project_id=character.project_id,
            vocabulary_level=VoiceDimension(
                description=f"Average word length: {avg_word_len:.1f} characters",
                representative_quotes=vocab_quotes,
            ),
            sentence_structure=VoiceDimension(
                description=f"Average sentence length: {avg_sent_len:.1f} words",
                representative_quotes=struct_quotes,
            ),
            verbal_tics=VoiceDimension(
                description=f"Recurring patterns: {', '.join(tics) if tics else 'none detected'}",
                representative_quotes=tics_quotes,
            ),
            formality=VoiceDimension(
                description=f"Overall formality: {formality_label} (score: {mean_formality:.2f})",
                representative_quotes=formality_quotes,
            ),
            consistency_score=score,
            warning=warning,
        )

        _profile_cache[character.id] = profile
        return profile

    def get_profile(self, character: Character, full_text: str) -> VoiceProfile:
        """Get the voice profile, generating it if needed."""
        if character.id in _profile_cache:
            # Recompute score in case flags were dismissed
            cached = _profile_cache[character.id]
            flags = _flags_cache.get(character.id, [])
            score = self._compute_score(flags)
            return VoiceProfile(
                character_id=cached.character_id,
                project_id=cached.project_id,
                vocabulary_level=cached.vocabulary_level,
                sentence_structure=cached.sentence_structure,
                verbal_tics=cached.verbal_tics,
                formality=cached.formality,
                consistency_score=score,
                warning=cached.warning,
            )
        return self.generate_profile(character, full_text)

    def get_flags(self, character: Character, full_text: str) -> List[ConsistencyFlag]:
        """Get consistency flags for a character, generating them if needed."""
        if character.id not in _flags_cache:
            flags = self._generate_flags_for_character(character, full_text)
            _flags_cache[character.id] = flags
            # Ensure profile cache is updated too
            if character.id not in _profile_cache:
                self.generate_profile(character, full_text)
        return _flags_cache[character.id]

    def dismiss_flag(
        self, flag_id: str, character_id: str, project_id: str
    ) -> Tuple[ConsistencyFlag, float]:
        """
        Mark a flag as dismissed and return the updated flag and new score.

        Returns (updated_flag, new_score).
        """
        flags = _flags_cache.get(character_id, [])
        flag = next((f for f in flags if f.id == flag_id), None)
        if not flag:
            raise HTTPException(status_code=404, detail="Flag not found")

        if flag.project_id != project_id:
            raise HTTPException(status_code=403, detail="Access denied")

        _dismissed_flag_ids.add(flag_id)
        new_score = self._compute_score(flags)
        return flag, new_score
