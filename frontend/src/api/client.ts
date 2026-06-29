import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

// ─── Projects ────────────────────────────────────────────────
export const listProjects = () => api.get('/projects').then(r => r.data)
export const createProject = (data: any) => api.post('/projects', data).then(r => r.data)
export const getProject = (name: string) => api.get(`/projects/${name}`).then(r => r.data)
export const deleteProject = (name: string) => api.delete(`/projects/${name}`)
export const getProjectProgress = (name: string) => api.get(`/projects/${name}/progress`).then(r => r.data)
export const getProjectStatus = (name: string) => api.get(`/projects/${name}/status`).then(r => r.data)

// ─── Generation ──────────────────────────────────────────────
export const startGeneration = (name: string, body?: any) => api.post(`/projects/${name}/generate`, body || {}).then(r => r.data)
export const cancelGeneration = (name: string) => api.post(`/projects/${name}/generate/cancel`).then(r => r.data)
export const resumeGeneration = (name: string, body: any) => api.post(`/projects/${name}/generate/resume`, body).then(r => r.data)
export const getCurrentJob = (name: string) => api.get(`/projects/${name}/jobs/current`).then(r => r.data)

// ─── Chapters ────────────────────────────────────────────────
export const listChapters = (name: string) => api.get(`/projects/${name}/chapters`).then(r => r.data)
export const getChapter = (name: string, n: number) => api.get(`/projects/${name}/chapters/${n}`).then(r => r.data)
export const saveChapter = (name: string, n: number, body: any) => api.put(`/projects/${name}/chapters/${n}`, body).then(r => r.data)

// ─── Files ───────────────────────────────────────────────────
export const listFiles = (name: string) => api.get(`/projects/${name}/files`).then(r => r.data)
export const triggerFormat = (name: string) => api.post(`/projects/${name}/format`).then(r => r.data)
export const getCost = (name: string) => api.get(`/projects/${name}/cost`).then(r => r.data)

// ─── Settings ────────────────────────────────────────────────
export const getSettings = () => api.get('/settings').then(r => r.data)
export const updateSettings = (body: any) => api.put('/settings', body).then(r => r.data)
export const getProviders = () => api.get('/settings/providers').then(r => r.data)

// ─── Lorebook ────────────────────────────────────────────────
export const listCharacters = (name: string) => api.get(`/projects/${name}/characters`).then(r => r.data)
export const getCharacter = (name: string, charName: string) => api.get(`/projects/${name}/characters/${charName}`).then(r => r.data)
export const createCharacter = (name: string, body: any) => api.post(`/projects/${name}/characters`, body).then(r => r.data)
export const updateCharacter = (name: string, charName: string, body: any) => api.put(`/projects/${name}/characters/${charName}`, body).then(r => r.data)
export const deleteCharacter = (name: string, charName: string) => api.delete(`/projects/${name}/characters/${charName}`)

export const listLocations = (name: string) => api.get(`/projects/${name}/locations`).then(r => r.data)
export const createLocation = (name: string, body: any) => api.post(`/projects/${name}/locations`, body).then(r => r.data)
export const updateLocation = (name: string, locName: string, body: any) => api.put(`/projects/${name}/locations/${locName}`, body).then(r => r.data)
export const deleteLocation = (name: string, locName: string) => api.delete(`/projects/${name}/locations/${locName}`)

export const listLoreEntries = (name: string) => api.get(`/projects/${name}/lore`).then(r => r.data)
export const createLoreEntry = (name: string, body: any) => api.post(`/projects/${name}/lore`, body).then(r => r.data)
export const updateLoreEntry = (name: string, entryName: string, body: any) => api.put(`/projects/${name}/lore/${entryName}`, body).then(r => r.data)
export const deleteLoreEntry = (name: string, entryName: string) => api.delete(`/projects/${name}/lore/${entryName}`)

export const listArcs = (name: string) => api.get(`/projects/${name}/arcs`).then(r => r.data)
export const createArc = (name: string, body: any) => api.post(`/projects/${name}/arcs`, body).then(r => r.data)
export const updateArc = (name: string, arcName: string, body: any) => api.put(`/projects/${name}/arcs/${arcName}`, body).then(r => r.data)
export const deleteArc = (name: string, arcName: string) => api.delete(`/projects/${name}/arcs/${arcName}`)

export const getWorldbuilding = (name: string) => api.get(`/projects/${name}/worldbuilding`).then(r => r.data)
export const updateWorldbuilding = (name: string, body: any) => api.put(`/projects/${name}/worldbuilding`, body).then(r => r.data)

export const listXref = (name: string) => api.get(`/projects/${name}/xref`).then(r => r.data)
export const searchProject = (name: string, body: any) => api.post(`/projects/${name}/search`, body).then(r => r.data)

export const getOutline = (name: string) => api.get(`/projects/${name}/outline`).then(r => r.data)
export const updateOutline = (name: string, body: any) => api.put(`/projects/${name}/outline`, body).then(r => r.data)
export const listScenes = (name: string, chapterNum: number) => api.get(`/projects/${name}/scenes/${chapterNum}`).then(r => r.data)
export const updateScene = (name: string, chapterNum: number, sceneNum: number, body: any) => api.put(`/projects/${name}/scenes/${chapterNum}/${sceneNum}`, body).then(r => r.data)
export const createScene = (name: string, chapterNum: number, body: any) => api.post(`/projects/${name}/scenes/${chapterNum}`, body).then(r => r.data)
export const deleteScene = (name: string, chapterNum: number, sceneNum: number) => api.delete(`/projects/${name}/scenes/${chapterNum}/${sceneNum}`)

// ─── Lore Sync / Analysis ────────────────────────────────
export const analyzeCharacter = (name: string, charName: string, body?: any) => api.post(`/projects/${name}/analyze/character/${charName}`, body || {}).then(r => r.data)
export const analyzeLocation = (name: string, locName: string, body?: any) => api.post(`/projects/${name}/analyze/location/${locName}`, body || {}).then(r => r.data)
export const analyzeLoreEntry = (name: string, entryName: string, body?: any) => api.post(`/projects/${name}/analyze/lore/${entryName}`, body || {}).then(r => r.data)
export const checkContinuity = (name: string, body?: any) => api.post(`/projects/${name}/analyze/continuity`, body || {}).then(r => r.data)
export const listSuggestions = (name: string, status: string = 'pending') => api.get(`/projects/${name}/suggestions`, { params: { status } }).then(r => r.data)
export const acceptSuggestion = (name: string, idx: number) => api.put(`/projects/${name}/suggestions/${idx}/accept`).then(r => r.data)
export const rejectSuggestion = (name: string, idx: number) => api.put(`/projects/${name}/suggestions/${idx}/reject`).then(r => r.data)
export const editSuggestion = (name: string, idx: number, body: { proposed_value: string }) => api.put(`/projects/${name}/suggestions/${idx}/edit`, body).then(r => r.data)
export const listCharacterStates = (name: string) => api.get(`/projects/${name}/character-states`).then(r => r.data)
export const getCharacterStates = (name: string, charName: string) => api.get(`/projects/${name}/character-states/${charName}`).then(r => r.data)
export const listContinuityNotes = (name: string) => api.get(`/projects/${name}/continuity-notes`).then(r => r.data)

// ─── Narrative Threads ──────────────────────────────────
export const listThreads = (name: string) => api.get(`/projects/${name}/threads`).then(r => r.data)
export const createThread = (name: string, body: any) => api.post(`/projects/${name}/threads`, body).then(r => r.data)
export const updateThread = (name: string, threadName: string, body: any) => api.put(`/projects/${name}/threads/${threadName}`, body).then(r => r.data)
export const deleteThread = (name: string, threadName: string) => api.delete(`/projects/${name}/threads/${threadName}`)

// ─── Outline Regeneration ───────────────────────────────
export const regenerateOutline = (name: string, body: { locked_chapters: number[], regenerate_chapters: number[] }) => api.post(`/projects/${name}/regenerate-outline`, body).then(r => r.data)

export default api
