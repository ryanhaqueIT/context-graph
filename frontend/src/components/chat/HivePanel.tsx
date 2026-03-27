"use client";

import { CheckCircle2, Loader2, Circle, Zap } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { useChatStore } from "@/store/chat-store";
import type { Agent } from "@/lib/types";

function AgentStatusIcon({ status }: { status: Agent["status"] }) {
  if (status === "completed")
    return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
  if (status === "running")
    return <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />;
  if (status === "failed")
    return <Circle className="h-4 w-4 text-rose-400" />;
  return <Circle className="h-4 w-4 text-slate-600" />;
}

function statusColor(status: Agent["status"]): string {
  switch (status) {
    case "completed":
      return "border-emerald-500/20";
    case "running":
      return "border-blue-500/30 bg-blue-500/5";
    case "failed":
      return "border-rose-500/20";
    default:
      return "border-slate-800";
  }
}

function AgentCard({ agent }: { agent: Agent }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex items-start gap-2.5 p-2.5 rounded-md bg-slate-800/30 border ${statusColor(
        agent.status
      )} hover:border-slate-700 cursor-pointer transition-colors`}
    >
      <AgentStatusIcon status={agent.status} />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-slate-300">{agent.name}</p>
        <p className="text-[10px] text-slate-500 mt-0.5 truncate">
          {agent.objective}
        </p>
        {agent.result && (
          <p className="text-[10px] text-emerald-400/80 mt-1 truncate">
            {agent.result}
          </p>
        )}
      </div>
    </motion.div>
  );
}

function HiveDAG({ agents }: { agents: Agent[] }) {
  return (
    <div className="relative space-y-2">
      {agents.map((agent, i) => (
        <div key={agent.id}>
          <AgentCard agent={agent} />
          {/* Connection line between agents */}
          {i < agents.length - 1 && (
            <div className="flex justify-center py-0.5">
              <div
                className={`w-px h-3 ${
                  agent.status === "completed"
                    ? "bg-emerald-500/30"
                    : "bg-slate-700"
                }`}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function SpawningAnimation() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="flex items-center justify-center gap-2 py-4"
    >
      <Zap className="h-4 w-4 text-blue-400 animate-pulse" />
      <span className="text-xs text-blue-400 animate-pulse">
        Spawning agents...
      </span>
    </motion.div>
  );
}

export function HivePanel() {
  const { mode, setMode, agents, context, isLoading } = useChatStore();

  const completedCount = agents.filter(
    (a) => a.status === "completed"
  ).length;
  const totalCount = agents.length;

  return (
    <div className="w-64 border-l border-slate-800 bg-slate-950 p-4 space-y-5 overflow-y-auto">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          {mode === "hive" ? "Hive Mode" : "Agent Mode"}
        </h3>
        {mode === "hive" ? (
          <Badge variant="info" className="text-[10px]">
            {completedCount}/{totalCount}
          </Badge>
        ) : (
          <Badge variant="outline" className="text-[10px] border-slate-700">
            Single
          </Badge>
        )}
      </div>

      {/* Mode Toggle */}
      <div className="flex rounded-lg border border-slate-800 p-0.5">
        <button
          onClick={() => setMode("agent")}
          className={`flex-1 text-xs py-1.5 rounded-md transition-colors ${
            mode === "agent"
              ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
              : "text-slate-500 hover:text-slate-300"
          }`}
        >
          Agent
        </button>
        <button
          onClick={() => setMode("hive")}
          className={`flex-1 text-xs py-1.5 rounded-md transition-colors ${
            mode === "hive"
              ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
              : "text-slate-500 hover:text-slate-300"
          }`}
        >
          Hive
        </button>
      </div>

      {/* Agents */}
      <div className="space-y-2">
        <span className="text-xs font-medium text-slate-500">
          {mode === "hive" ? "Agent Swarm" : "Agent"}
        </span>

        <AnimatePresence mode="wait">
          {isLoading && agents.every((a) => a.status === "pending") ? (
            <SpawningAnimation key="spawning" />
          ) : (
            <motion.div
              key="agents"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {mode === "hive" ? (
                <HiveDAG agents={agents} />
              ) : (
                <div className="space-y-2">
                  {agents.map((agent) => (
                    <AgentCard key={agent.id} agent={agent} />
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Context Stats */}
      <div className="pt-2 border-t border-slate-800 space-y-2">
        <span className="text-xs font-medium text-slate-500">Context</span>
        <div className="grid grid-cols-2 gap-2">
          <div className="text-center p-2 rounded-md bg-slate-800/30">
            <p className="text-lg font-bold text-slate-200">
              {context.files.length}
            </p>
            <p className="text-[10px] text-slate-500">Files</p>
          </div>
          <div className="text-center p-2 rounded-md bg-slate-800/30">
            <p className="text-lg font-bold text-slate-200">
              {context.patterns.length}
            </p>
            <p className="text-[10px] text-slate-500">Patterns</p>
          </div>
        </div>
      </div>
    </div>
  );
}
