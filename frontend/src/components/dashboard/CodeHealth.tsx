"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { moduleHealth } from "@/lib/sample-data";

export function CodeHealth() {
  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold text-slate-50">
          Code Health
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {moduleHealth.map((mod) => (
          <div key={mod.name} className="space-y-1.5">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-300">{mod.name}</span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">
                  {mod.files} files, {mod.issues} issues
                </span>
                <span
                  className="text-xs font-semibold"
                  style={{ color: mod.color }}
                >
                  {mod.health}%
                </span>
              </div>
            </div>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${mod.health}%`,
                  backgroundColor: mod.color,
                }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
