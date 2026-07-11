"""Partial outline regeneration ("Regen Unlocked") — lore grounding + milestone roadmap.

The partial path was missing the Phase-0 grounding the full outline pass has, and ignored
the author's arc milestones — so regenerated chapters invented plots unrelated to the
planned beat-to-chapter roadmap.
"""
import unittest

from libriscribe.knowledge_base import (
    ProjectKnowledgeBase, Chapter, StoryArc, ArcMilestone, LoreEntry,
)


class _CaptureLLM:
    def __init__(self, response="## Chapter 4: The Catalyst\n### Summary\nTya meets CEE alone.\n\n### Key Events\n- A different resonance."):
        self.prompts = []
        self.response = response

    def generate_content(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return self.response


class PartialOutlineTests(unittest.TestCase):
    def _pkb(self):
        pkb = ProjectKnowledgeBase(project_name="p", title="Helix", genre="SF", num_chapters=5)
        pkb.add_chapter(Chapter(chapter_number=1, title="One", summary="Maren finds CEE."))
        pkb.add_chapter(Chapter(chapter_number=4, title="Chapter 4 Placeholder",
                                summary="Chapter 4 summary to be developed."))
        pkb.lore_entries["The Neural Gradient"] = LoreEntry(
            name="The Neural Gradient", entry_type="mechanic",
            description="CEE's pigmentation tracks her state.")
        pkb.add_story_arc(StoryArc(
            name="Subjective Drift", description="CEE wakes up.", arc_type="main",
            milestones=[
                ArcMilestone(name="Semantic Colonization", milestone_type="escalation",
                             target_chapter=4, description="Crude language displaces technical vocabulary.",
                             status="in_progress"),
                ArcMilestone(name="First Deviation", milestone_type="setup",
                             target_chapter=1, description="Already done.", status="completed"),
            ],
        ))
        return pkb

    def test_prompt_carries_lore_and_milestone_roadmap(self):
        from libriscribe.agents.outliner import OutlinerAgent

        pkb = self._pkb()
        fake = _CaptureLLM()
        OutlinerAgent(llm_client=fake).execute_partial(pkb, locked_chapters=[1], regenerate_chapters=[4])

        prompt = fake.prompts[0]
        self.assertIn("The Neural Gradient", prompt)            # lore digest present
        self.assertIn("PLANNED STORY BEATS", prompt)            # milestone roadmap present
        self.assertIn("Semantic Colonization", prompt)          # ch-4 milestone included
        self.assertNotIn("First Deviation", prompt)             # completed/other-chapter milestone excluded
        self.assertIn("Chapter 1: One", prompt)                 # locked context intact

    def test_locked_chapter_untouched_and_target_replaced(self):
        from libriscribe.agents.outliner import OutlinerAgent

        pkb = self._pkb()
        fake = _CaptureLLM()
        OutlinerAgent(llm_client=fake).execute_partial(pkb, locked_chapters=[1], regenerate_chapters=[4])

        self.assertEqual(pkb.chapters[1].summary, "Maren finds CEE.")   # locked survives
        self.assertIn("Tya meets CEE", pkb.chapters[4].summary)         # placeholder replaced

    def test_classify_development_buckets(self):
        from libriscribe.agents.outliner import OutlinerAgent

        pkb = ProjectKnowledgeBase(project_name="p", title="T", genre="F", num_chapters=4)
        pkb.add_chapter(Chapter(chapter_number=1, title="One", summary="Real summary.",
                                scenes=[]))
        ch2 = Chapter(chapter_number=2, title="Two", summary="Also real.")
        from libriscribe.knowledge_base import Scene
        ch2.scenes.append(Scene(scene_number=1, summary="A scene."))
        pkb.add_chapter(ch2)
        pkb.add_chapter(Chapter(chapter_number=3, title="Chapter 3 Placeholder",
                                summary="Chapter 3 summary to be developed."))
        pkb.add_chapter(Chapter(chapter_number=4, title="Four", summary="   "))

        buckets = OutlinerAgent.classify_development(pkb)
        self.assertEqual(buckets["scene"], [1])       # real summary, no scenes -> scenes only
        self.assertEqual(buckets["done"], [2])        # fully developed -> untouched
        self.assertEqual(buckets["summarize"], [3, 4])  # placeholder / blank -> full develop

    def test_no_milestones_no_roadmap_block(self):
        from libriscribe.agents.outliner import OutlinerAgent

        pkb = self._pkb()
        pkb.story_arcs.clear()
        fake = _CaptureLLM()
        OutlinerAgent(llm_client=fake).execute_partial(pkb, locked_chapters=[1], regenerate_chapters=[4])
        self.assertNotIn("PLANNED STORY BEATS", fake.prompts[0])


if __name__ == "__main__":
    unittest.main()
