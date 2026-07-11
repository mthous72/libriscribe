import type { Page } from '@playwright/test'

/**
 * Canned, realistic responses for the REST endpoints the pages hit on load.
 * Enough to render every page with content (chapters, stats, versions, lore,
 * an outline) so layout is exercised the way it is in real use — without a
 * backend. Unmatched routes fall through to `{}` which every page tolerates.
 */
const project = {
  project_name: 'demo', title: 'The Obsidian Gate', genre: 'Fantasy',
  category: 'Fiction', language: 'English',
  logline: 'A cartographer discovers the maps she draws reshape the world.',
  llm_provider: 'openai', model: 'gpt-4o', num_chapters: 5,
}
const progress = {
  stage_statuses: {
    concept: 'complete', outline: 'complete', characters: 'complete',
    worldbuilding: 'in_progress', chapters: 'pending', formatting: 'pending',
  },
}
const chapters = [
  { chapter_number: 1, title: 'The Vanishing Coastline', has_content: true, word_count: 3120 },
  { chapter_number: 2, title: 'Ink and Bone', has_content: true, word_count: 2890 },
  { chapter_number: 3, title: 'The Salt Road', has_content: false, word_count: 0 },
  { chapter_number: 4, title: 'Cartographer’s Oath', has_content: false, word_count: 0 },
  { chapter_number: 5, title: 'The Obsidian Gate', has_content: false, word_count: 0 },
]
const versions = [
  { version: 3, label: 'before Act 2 rewrite', created_at: '2026-06-30T12:00:00Z', summary: { chapters: 2, words: 6010, characters: 4, locations: 3, lore: 5, arcs: 2 } },
  { version: 2, label: '', created_at: '2026-06-29T09:00:00Z', summary: { chapters: 1, words: 3120, characters: 3, locations: 2, lore: 3, arcs: 1 } },
  { version: 1, label: 'initial import', created_at: '2026-06-28T08:00:00Z', summary: { chapters: 0, words: 0, characters: 2, locations: 1, lore: 1, arcs: 1 } },
]
const stats = {
  overall: { word_count: 6010, chapter_count: 2, flesch_reading_ease: 64.2, flesch_kincaid_grade: 7.8, avg_sentence_length: 16, dialogue_ratio: 0.32, adverb_ratio: 0.03, reading_time_min: 24 },
  chapters: [
    { chapter_number: 1, word_count: 3120, flesch_reading_ease: 65.1 },
    { chapter_number: 2, word_count: 2890, flesch_reading_ease: 63.3 },
  ],
}
const outline = {
  outline_markdown: '# Act 1\n\n## Chapter 1 — The Vanishing Coastline\nMira wakes to find a village gone from both the shore and her map.',
  chapters: [
    { chapter_number: 1, title: 'The Vanishing Coastline', scene_count: 3 },
    { chapter_number: 2, title: 'Ink and Bone', scene_count: 2 },
  ],
}
const chapter1 = {
  chapter_number: 1, title: 'The Vanishing Coastline',
  content: 'The morning the coastline vanished, Mira was still bent over her drafting table, nib poised above a stretch of parchment where a fishing village had been the night before.\n\n'.repeat(6),
}
const providers = [
  { name: 'openai', configured: true }, { name: 'claude', configured: true },
  { name: 'google_ai_studio', configured: false }, { name: 'deepseek', configured: false },
  { name: 'mistral', configured: false }, { name: 'openrouter', configured: false },
  { name: 'local', configured: false },
]

// B45: the workbench-tree aggregate (chapters w/ scenes, lore names, arcs, threads).
const workbenchTree = {
  stage_statuses: progress.stage_statuses, next_step: 'chapters',
  outline_set: true, num_chapters: 5,
  chapters: [
    { chapter_number: 1, title: 'The Vanishing Coastline', summary_set: true, has_file: true, unstructured: false, word_count: 3120, scenes: [
      { scene_number: 1, summary_set: true, has_prose: true, word_count: 1000 },
      { scene_number: 2, summary_set: true, has_prose: true, word_count: 2120 },
    ] },
    { chapter_number: 2, title: 'Ink and Bone', summary_set: true, has_file: true, unstructured: true, word_count: 2890, scenes: [] },
    { chapter_number: 3, title: 'The Salt Road', summary_set: false, has_file: false, unstructured: false, word_count: 0, scenes: [] },
  ],
  characters: [{ name: 'Mira', role: 'protagonist', fields_set: 4, has_voice: true }, { name: 'Captain Vos', role: 'mentor', fields_set: 2, has_voice: false }],
  locations: [{ name: 'Saltrow' }],
  lore: [{ name: 'Living Cartography', entry_type: 'magic' }],
  arcs: [{ name: 'Mira’s Awakening', arc_type: 'main', status: 'active', milestones: [
    { name: 'First redraw', milestone_type: 'inciting_incident', target_chapter: 1, actual_chapter: 1, status: 'completed', description: 'Mira redraws the coast.' },
  ] }],
  threads: [],
  worldbuilding_fields_set: 3,
}

function bodyFor(pathname: string): unknown {
  const p = pathname.replace(/^\/api/, '')
  if (p === '/projects') return []
  if (p === '/projects/demo/workbench-tree') return workbenchTree
  // The docked brainstorm pane loads sessions on mount (the drawer only did when opened).
  if (p === '/projects/demo/chat/sessions') return [{ id: 'abc123', title: 'General', focus: null, prefs: { verbosity: 'medium' }, message_count: 0 }]
  if (p.startsWith('/projects/demo/chat/sessions/')) return { id: 'abc123', title: 'General', focus: null, prefs: { verbosity: 'medium' }, messages: [] }
  if (p.startsWith('/projects/demo/impact/')) return { entity: '', chapters: [], scenes: [], total_mentions: 0 }
  if (p === '/projects/demo/chapters/1/scene-prose') return { exists: true, unstructured: false, scenes: [{ scene_number: 1, has_prose: true, word_count: 1000 }, { scene_number: 2, has_prose: true, word_count: 2120 }] }
  if (/^\/projects\/demo\/chapters\/1\/scene-prose\/\d+$/.test(p)) return { scene_number: 1, text: chapter1.content, word_count: 1000 }
  if (p === '/projects/demo') return project
  if (p === '/projects/demo/progress') return progress
  if (p === '/projects/demo/versions') return versions
  if (p === '/projects/demo/retrieval') return { mode: 'keyword', chunk_count: 128, embedder_configured: false, semantic_ready: false }
  if (p === '/projects/demo/chapters') return chapters
  if (p === '/projects/demo/chapters/1') return chapter1
  if (p === '/projects/demo/preview-context/1') return { context: 'Mira — protagonist, cartographer whose maps reshape the world.\nSaltrow — a fishing village that vanished from the coast.\n'.repeat(20), token_estimate: 512 }
  if (p === '/projects/demo/cost') return { total_cost: 0.1234 }
  if (p === '/projects/demo/stats') return stats
  if (p === '/projects/demo/outline') return outline
  if (p === '/projects/demo/scenes/1') return []
  if (p === '/projects/demo/jobs/current') return null
  if (p.startsWith('/projects/demo/characters')) return [{ name: 'Mira', role: 'protagonist' }, { name: 'Captain Vos', role: 'mentor' }]
  if (p.startsWith('/projects/demo/locations')) return [{ name: 'Saltrow' }]
  if (p.startsWith('/projects/demo/lore')) return [{ name: 'Living Cartography', entry_type: 'magic' }]
  if (p.startsWith('/projects/demo/arcs')) return [{ name: 'Mira’s Awakening', status: 'open' }]
  if (p.startsWith('/projects/demo/threads')) return []
  if (p.startsWith('/projects/demo/worldbuilding')) return {}
  if (p.startsWith('/projects/demo/xref')) return []
  if (p.startsWith('/projects/demo/references')) return { references: [], ocr_available: true }
  if (p === '/settings') return { openai_model: 'gpt-4o', local_base_url: '', embedding_source: 'off', writing_system_prompt: '' }
  if (p === '/settings/providers') return providers
  return {}
}

/** Intercept every REST call and answer from the canned data above. */
export async function mockApi(page: Page): Promise<void> {
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url())
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(bodyFor(url.pathname)),
    })
  })
}
