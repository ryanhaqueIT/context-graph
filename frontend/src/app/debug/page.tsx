"use client";

import { Bug, Terminal, Globe, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function DebugPage() {
  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-50">Debug Reports</h1>
        <Badge variant="outline" className="border-slate-700">3 active sessions</Badge>
      </div>

      <div className="grid gap-4">
        {[
          { title: "Session #4521 - Checkout Flow Failure", errors: 3, duration: "2:30", severity: "error" as const },
          { title: "Session #4518 - Login Timeout", errors: 1, duration: "5:12", severity: "warning" as const },
          { title: "Session #4515 - Dashboard Load Performance", errors: 0, duration: "1:45", severity: "info" as const },
        ].map((session) => (
          <Card key={session.title} className="bg-slate-900 border-slate-800 cursor-pointer hover:border-slate-700 transition-colors">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-slate-800 flex items-center justify-center">
                    <Bug className="h-5 w-5 text-slate-400" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-200">{session.title}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-slate-500 flex items-center gap-1">
                        <AlertTriangle className="h-3 w-3" />
                        {session.errors} errors
                      </span>
                      <span className="text-xs text-slate-500 flex items-center gap-1">
                        <Terminal className="h-3 w-3" />
                        {session.duration}
                      </span>
                    </div>
                  </div>
                </div>
                <Badge variant={session.severity}>{session.severity}</Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Placeholder for session replay */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-base text-slate-50">Session Replay</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 rounded-lg bg-slate-800/30 border border-slate-800 border-dashed flex items-center justify-center">
            <div className="text-center">
              <Globe className="h-8 w-8 text-slate-600 mx-auto mb-2" />
              <p className="text-sm text-slate-500">Select a session to view the replay</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
