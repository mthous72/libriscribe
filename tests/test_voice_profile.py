"""Tests for F3: Dialogue Voice Consistency."""

import unittest

from libriscribe.knowledge_base import (
    Character,
    ProjectKnowledgeBase,
    VoiceProfile,
)


class TestVoiceProfile(unittest.TestCase):
    """Tests for the VoiceProfile model and Character integration."""

    def test_voice_profile_model(self):
        vp = VoiceProfile(
            speech_patterns="Short, clipped sentences",
            vocabulary_level="street slang",
            verbal_tics="says 'right?' often",
            avoids="never uses formal language",
            example_dialogue=["You comin' or what?", "Right? That's what I said."],
        )
        self.assertEqual(vp.speech_patterns, "Short, clipped sentences")
        self.assertEqual(len(vp.example_dialogue), 2)

    def test_character_with_voice_profile(self):
        char = Character(
            name="Shade",
            role="protagonist",
            voice_profile=VoiceProfile(
                speech_patterns="Terse, economical",
                vocabulary_level="direct",
            ),
        )
        self.assertIsNotNone(char.voice_profile)
        self.assertEqual(char.voice_profile.speech_patterns, "Terse, economical")

    def test_character_without_voice_profile(self):
        char = Character(name="NPC", role="background")
        self.assertIsNone(char.voice_profile)

    def test_voice_profile_serialization(self):
        pkb = ProjectKnowledgeBase(project_name="test")
        char = Character(
            name="Alice",
            voice_profile=VoiceProfile(
                speech_patterns="Formal and precise",
                verbal_tics="clears throat",
                example_dialogue=["I beg your pardon.", "As I was saying..."],
            ),
        )
        pkb.add_character(char)
        json_str = pkb.to_json()
        restored = ProjectKnowledgeBase.from_json(json_str)
        restored_char = restored.get_character("Alice")
        self.assertIsNotNone(restored_char)
        self.assertIsNotNone(restored_char.voice_profile)
        self.assertEqual(restored_char.voice_profile.speech_patterns, "Formal and precise")
        self.assertEqual(
            restored_char.voice_profile.example_dialogue,
            ["I beg your pardon.", "As I was saying..."],
        )

    def test_backward_compat_no_voice_profile(self):
        char = Character(name="Old Character")
        data = char.model_dump()
        self.assertIsNone(data["voice_profile"])
        # Should load fine from old data without voice_profile
        restored = Character(**{k: v for k, v in data.items() if k != "voice_profile"})
        self.assertIsNone(restored.voice_profile)


if __name__ == "__main__":
    unittest.main()
