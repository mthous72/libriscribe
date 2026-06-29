import { create } from 'zustand'

interface ProjectState {
  projects: any[]
  currentProject: any | null
  setProjects: (projects: any[]) => void
  setCurrentProject: (project: any) => void
}

export const useProjectStore = create<ProjectState>((set) => ({
  projects: [],
  currentProject: null,
  setProjects: (projects) => set({ projects }),
  setCurrentProject: (project) => set({ currentProject: project }),
}))
