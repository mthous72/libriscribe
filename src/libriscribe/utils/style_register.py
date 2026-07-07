"""Prose register control (B36) — an optional 1–5 intensity dial for generated prose.

Adjusts the register/tone directive injected into scene prompts. Purely a generation steer:
it changes prompt text only and performs no filtering of model output. The feature is OFF
unless explicitly enabled in Advanced settings (opt-in + age affirmation + terms acknowledgment
— see the settings router); until then no directive is ever injected and the app behaves
identically to before.
"""
from __future__ import annotations

# Level -> register directive. Neutral, professional phrasing; the dial expresses how frank
# and unrestrained the prose's depiction of mature/intense material may be.
REGISTER_LEVELS: dict[int, str] = {
    1: ("PROSE REGISTER 1 (restrained): keep mature content implied rather than shown; use "
        "euphemistic, tasteful language and transition past intense moments (fade out)."),
    2: ("PROSE REGISTER 2 (suggestive): sensual or intense moments may be acknowledged on the "
        "page but stay tasteful and indirect; favor implication over description."),
    3: ("PROSE REGISTER 3 (frank): depict mature and intense scenes directly on the page in "
        "plain, direct language, without crude vocabulary."),
    4: ("PROSE REGISTER 4 (graphic): depict mature and intense scenes explicitly and in detail, "
        "using direct, unflinching language appropriate to the scene."),
    5: ("PROSE REGISTER 5 (unrestrained): depict mature and intense scenes with full explicitness "
        "and a coarse, colloquial vocabulary; hold nothing back within the story's canon rules."),
}


def register_directive(level) -> str:
    """The directive for a 1–5 level; empty string for anything else."""
    try:
        return REGISTER_LEVELS.get(int(level), "")
    except (TypeError, ValueError):
        return ""


def active_register_directive(kb, settings) -> str:
    """The directive to inject for this project — ONLY when the feature is globally enabled
    (Advanced settings gate) AND the project sets a level. Empty otherwise."""
    if not getattr(settings, "prose_register_enabled", False):
        return ""
    return register_directive(getattr(kb, "prose_register", None))
