"""Entity interconnection (B25) — bidirectional, name-resolved links."""
import unittest

from libriscribe.knowledge_base import (
    ProjectKnowledgeBase, Character, Location, LoreEntry, StoryArc, NarrativeThread,
)
from libriscribe.services import connections


def _kb():
    kb = ProjectKnowledgeBase(project_name="t", title="B", genre="F", num_chapters=10)
    kb.add_character(Character(name="Maren", relationships={"Tya": "old ally", "Ghost": "rumor"}))
    kb.add_character(Character(name="Tya"))
    kb.add_location(Location(name="The Keep", associated_characters=["Maren"]))
    kb.story_arcs["Fall"] = StoryArc(name="Fall", characters_involved=["Maren", "Tya"])
    kb.narrative_threads["Debt"] = NarrativeThread(name="Debt", characters_involved=["Tya"])
    kb.lore_entries["Guild"] = LoreEntry(name="Guild", related_entities=["The Keep"])
    return kb


class ConnectionsTests(unittest.TestCase):
    def test_outgoing_resolves_and_flags_unresolved(self):
        c = connections.entity_connections(_kb(), "character", "Maren")
        out = {o["name"]: o for o in c["outgoing"]}
        self.assertTrue(out["Tya"]["resolved"])
        self.assertEqual(out["Tya"]["type"], "character")
        self.assertEqual(out["Tya"]["detail"], "old ally")
        self.assertFalse(out["Ghost"]["resolved"])   # no such record → unlinked
        self.assertEqual(out["Ghost"]["type"], "")

    def test_incoming_finds_all_referrers(self):
        c = connections.entity_connections(_kb(), "character", "Maren")
        incoming = {(i["type"], i["name"]) for i in c["incoming"]}
        self.assertIn(("location", "The Keep"), incoming)   # associated_characters
        self.assertIn(("arc", "Fall"), incoming)            # characters_involved
        self.assertNotIn(("thread", "Debt"), incoming)      # Debt involves Tya, not Maren

    def test_incoming_is_case_insensitive(self):
        kb = _kb()
        kb.story_arcs["Rise"] = StoryArc(name="Rise", characters_involved=["maren"])  # lowercase
        c = connections.entity_connections(kb, "character", "Maren")
        self.assertIn(("arc", "Rise"), {(i["type"], i["name"]) for i in c["incoming"]})

    def test_cross_type_link_resolves(self):
        # Codex 'Guild' relates to a location 'The Keep' → resolves across types.
        c = connections.entity_connections(_kb(), "lore", "Guild")
        out = c["outgoing"][0]
        self.assertEqual((out["type"], out["name"], out["resolved"]), ("location", "The Keep", True))
        # And the location sees the incoming codex link.
        loc = connections.entity_connections(_kb(), "location", "The Keep")
        self.assertIn(("lore", "Guild"), {(i["type"], i["name"]) for i in loc["incoming"]})

    def test_missing_entity_returns_not_found(self):
        c = connections.entity_connections(_kb(), "character", "Nobody")
        self.assertFalse(c["found"])
        self.assertEqual(c["outgoing"], [])
        self.assertEqual(c["incoming"], [])

    def test_no_self_link(self):
        c = connections.entity_connections(_kb(), "character", "Maren")
        self.assertNotIn(("character", "Maren"), {(i["type"], i["name"]) for i in c["incoming"]})

    def test_primary_link_field_map(self):
        self.assertEqual(connections.PRIMARY_LINK_FIELD["arc"], "characters_involved")
        self.assertEqual(connections.PRIMARY_LINK_FIELD["character"], "relationships")


class SuggestConnectionsTests(unittest.TestCase):
    def test_suggests_co_occurring_not_yet_linked(self):
        import libriscribe.services.retrieval_service as rs
        kb = _kb()  # Maren already links to Tya (relationship) and Ghost (unlinked)

        class FakeXref:
            related_entities = ["Tya", "The Keep", "Ghost"]  # Tya already linked; Keep is new; Ghost isn't a record

        class FakeSvc:
            def search_cross_references(self, n):
                return FakeXref()

        orig = rs.search_service_for
        rs.search_service_for = lambda *a, **k: FakeSvc()
        try:
            out = connections.suggest_connections(kb, project_dir=None, entity_type="character", name="Maren")
        finally:
            rs.search_service_for = orig
        names = {s["name"] for s in out["suggestions"]}
        self.assertIn("The Keep", names)       # co-occurs, is a record, not already linked
        self.assertNotIn("Tya", names)         # already linked → excluded
        self.assertEqual(len(out["suggestions"]), 1)  # Ghost isn't a real record → excluded

    def test_suggest_missing_entity_is_empty(self):
        self.assertEqual(connections.suggest_connections(_kb(), None, "character", "Nobody")["suggestions"], [])


if __name__ == "__main__":
    unittest.main()
