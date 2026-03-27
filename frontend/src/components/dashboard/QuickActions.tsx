"use client";

import { Bug, GitPullRequest, Zap } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

const actions = [
  {
    label: "Debug Report",
    description: "Investigate a production issue",
    icon: Bug,
    color: "from-rose-500/20 to-rose-500/5",
    iconColor: "text-rose-400",
  },
  {
    label: "PR Review",
    description: "Review a pull request with AI",
    icon: GitPullRequest,
    color: "from-blue-500/20 to-blue-500/5",
    iconColor: "text-blue-400",
  },
  {
    label: "Simulate",
    description: "Run code simulations",
    icon: Zap,
    color: "from-amber-500/20 to-amber-500/5",
    iconColor: "text-amber-400",
  },
];

export function QuickActions() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {actions.map((action) => {
        const Icon = action.icon;
        return (
          <Card
            key={action.label}
            className="bg-slate-900 border-slate-800 cursor-pointer hover:border-slate-700 transition-all group"
          >
            <CardContent className="p-4">
              <div className={`h-10 w-10 rounded-lg bg-gradient-to-br ${action.color} flex items-center justify-center mb-3`}>
                <Icon className={`h-5 w-5 ${action.iconColor}`} />
              </div>
              <h3 className="text-sm font-semibold text-slate-50 group-hover:text-white">
                {action.label}
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                {action.description}
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
