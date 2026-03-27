import { create } from "zustand";
import type { ChatMessage, Agent } from "@/lib/types";
import {
  simulateAIResponse,
  simulateAgentExecution,
  getHiveAgents,
  getSingleAgent,
} from "@/lib/ai-simulator";
import { sendChatMessage } from "@/lib/api";

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  mode: "agent" | "hive";
  agents: Agent[];
  context: {
    files: string[];
    patterns: string[];
    problems: string[];
  };
  sendMessage: (content: string) => Promise<void>;
  setMode: (mode: "agent" | "hive") => void;
  clearMessages: () => void;
}

function generateId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

function now(): string {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isLoading: false,
  mode: "agent",
  agents: getSingleAgent(),
  context: {
    files: [],
    patterns: [],
    problems: [],
  },

  sendMessage: async (content: string) => {
    const state = get();
    if (state.isLoading) return;

    // Add user message
    const userMessage: ChatMessage = {
      id: generateId(),
      role: "user",
      content,
      timestamp: now(),
    };

    set({ isLoading: true, messages: [...state.messages, userMessage] });

    // Reset agents to pending
    const freshAgents =
      state.mode === "hive" ? getHiveAgents() : getSingleAgent();
    set({ agents: freshAgents });

    // Animate agent statuses
    simulateAgentExecution(freshAgents, (updated) => {
      set({ agents: updated });
    });

    // Try the real API first
    const apiResponse = await sendChatMessage({
      message: content,
      context: {
        files: state.context.files,
        mode: state.mode,
      },
    });

    if (apiResponse) {
      // Use real API response
      set((s) => ({
        messages: [...s.messages, apiResponse.message],
        isLoading: false,
        context: apiResponse.context
          ? {
              files: [
                ...new Set([
                  ...s.context.files,
                  ...apiResponse.context.files,
                ]),
              ],
              patterns: [
                ...new Set([
                  ...s.context.patterns,
                  ...apiResponse.context.patterns,
                ]),
              ],
              problems: [
                ...new Set([
                  ...s.context.problems,
                  ...apiResponse.context.problems,
                ]),
              ],
            }
          : s.context,
      }));
    } else {
      // Fall back to simulated response
      const simulated = await simulateAIResponse(content);

      set((s) => ({
        messages: [...s.messages, ...simulated.messages],
        isLoading: false,
        context: {
          files: [
            ...new Set([...s.context.files, ...simulated.files]),
          ],
          patterns: [
            ...new Set([...s.context.patterns, ...simulated.patterns]),
          ],
          problems: [
            ...new Set([...s.context.problems, ...simulated.problems]),
          ],
        },
      }));
    }
  },

  setMode: (mode) => {
    const agents = mode === "hive" ? getHiveAgents() : getSingleAgent();
    set({ mode, agents });
  },

  clearMessages: () =>
    set({
      messages: [],
      context: { files: [], patterns: [], problems: [] },
      agents:
        get().mode === "hive" ? getHiveAgents() : getSingleAgent(),
    }),
}));
