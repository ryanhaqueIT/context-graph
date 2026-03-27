"use client";

import { CheckCircle2, XCircle, Loader2, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const scenarios = [
  { title: "Happy path billing update", status: "pass" as const },
  { title: "Currency conversion edge case", status: "pass" as const },
  { title: "Non-owner permission error", status: "blocked" as const },
  { title: "Token refresh after SSO", status: "running" as const },
  { title: "Concurrent session handling", status: "pass" as const },
  { title: "Rate limit boundary", status: "fail" as const },
  { title: "Empty cart checkout", status: "pass" as const },
  { title: "Expired coupon application", status: "pass" as const },
];

const statusIcons = {
  pass: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
  fail: <XCircle className="h-4 w-4 text-rose-400" />,
  running: <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />,
  blocked: <AlertCircle className="h-4 w-4 text-amber-400" />,
};

const statusBadges = {
  pass: <Badge variant="success">Pass</Badge>,
  fail: <Badge variant="error">Fail</Badge>,
  running: <Badge variant="info">Running</Badge>,
  blocked: <Badge variant="warning">Blocked</Badge>,
};

export default function SimulationsPage() {
  const passCount = scenarios.filter((s) => s.status === "pass").length;
  const failCount = scenarios.filter((s) => s.status === "fail").length;
  const runningCount = scenarios.filter((s) => s.status === "running").length;
  const coverage = Math.round((passCount / scenarios.length) * 100);

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-50">Code Simulations</h1>
        <div className="flex items-center gap-4">
          {(["Generate", "Execute", "Validate", "Ship"] as const).map((step, i) => (
            <div key={step} className="flex items-center gap-2">
              <span className={`text-xs font-medium ${i === 1 ? "text-blue-400" : "text-slate-500"}`}>
                {step}
              </span>
              {i < 3 && <span className="text-slate-700">{">"}</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Coverage bar */}
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-slate-300">Coverage Analytics</span>
            <div className="flex items-center gap-4 text-xs text-slate-500">
              <span>Total: {scenarios.length}</span>
              <span className="text-emerald-400">Pass: {passCount}</span>
              <span className="text-rose-400">Fail: {failCount}</span>
              <span className="text-blue-400">Running: {runningCount}</span>
            </div>
          </div>
          <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-emerald-500 rounded-full transition-all"
              style={{ width: `${coverage}%` }}
            />
          </div>
          <p className="text-xs text-slate-500 mt-1">{coverage}% coverage</p>
        </CardContent>
      </Card>

      {/* Scenario list */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader className="pb-3">
          <CardTitle className="text-base text-slate-50">Scenarios</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 p-2">
          {scenarios.map((scenario) => (
            <div
              key={scenario.title}
              className="flex items-center justify-between px-4 py-3 rounded-md hover:bg-slate-800/50 cursor-pointer transition-colors"
            >
              <div className="flex items-center gap-3">
                {statusIcons[scenario.status]}
                <span className="text-sm text-slate-200">{scenario.title}</span>
              </div>
              {statusBadges[scenario.status]}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
