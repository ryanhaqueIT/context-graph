import { create } from "zustand";

interface AppState {
  sidebarCollapsed: boolean;
  activeProject: string;
  theme: "dark" | "light";
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setActiveProject: (project: string) => void;
  setTheme: (theme: "dark" | "light") => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  activeProject: "context-graph",
  theme: "dark",
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setActiveProject: (project) => set({ activeProject: project }),
  setTheme: (theme) => set({ theme }),
}));
