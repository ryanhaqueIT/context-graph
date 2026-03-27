"use client";

import { GitPullRequest, FileText, AlertTriangle, CheckSquare } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function ReviewsPage() {
  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-50">PR Reviews</h1>
        <Badge variant="info">1 pending review</Badge>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <GitPullRequest className="h-5 w-5 text-blue-400" />
              <CardTitle className="text-base text-slate-50">
                PR #423 -- Fix checkout permissions
              </CardTitle>
            </div>
            <Badge variant="success">Ready for review</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Summary */}
          <div className="p-4 rounded-lg bg-slate-800/30 border border-slate-800">
            <h3 className="text-sm font-medium text-slate-300 mb-2">Summary</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              This PR fixes a null pointer in the permission check that caused 500 errors for
              non-owner users during checkout. Adds a guard clause before the processPayment call.
            </p>
          </div>

          {/* Regression Warning */}
          <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/20 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-400 mt-0.5 shrink-0" />
            <p className="text-xs text-amber-300">
              Regression remembered from 14 days ago (Ticket #234)
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* File Changes */}
            <div>
              <h3 className="text-sm font-medium text-slate-300 mb-2 flex items-center gap-1.5">
                <FileText className="h-4 w-4" />
                File Changes
              </h3>
              <div className="space-y-1.5">
                {[
                  { file: "auth/permissions.ts", added: 12, removed: 3 },
                  { file: "api/checkout.ts", added: 4, removed: 1 },
                  { file: "tests/auth.test.ts", added: 45, removed: 0 },
                ].map((change) => (
                  <div
                    key={change.file}
                    className="flex items-center justify-between text-xs px-2 py-1.5 rounded bg-slate-800/30"
                  >
                    <span className="text-slate-400 font-mono">{change.file}</span>
                    <span>
                      <span className="text-emerald-400">+{change.added}</span>
                      {" "}
                      <span className="text-rose-400">-{change.removed}</span>
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Testing Suggestions */}
            <div>
              <h3 className="text-sm font-medium text-slate-300 mb-2 flex items-center gap-1.5">
                <CheckSquare className="h-4 w-4" />
                Testing Suggestions
              </h3>
              <div className="space-y-1.5">
                {[
                  "Unit: null user.role",
                  "Integration: SSO + checkout",
                  "Edge: concurrent sessions",
                  "Regression: Ticket #234",
                ].map((test) => (
                  <label
                    key={test}
                    className="flex items-center gap-2 text-xs text-slate-400 px-2 py-1.5 rounded bg-slate-800/30 cursor-pointer hover:bg-slate-800/50"
                  >
                    <input type="checkbox" className="rounded border-slate-700 bg-slate-800" />
                    {test}
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 pt-2">
            <Button size="sm" className="bg-blue-600 hover:bg-blue-500 text-white">
              Get Started for Me
            </Button>
            <Button variant="outline" size="sm" className="border-slate-700 text-slate-300">
              Write a Test Plan
            </Button>
            <Button variant="outline" size="sm" className="border-slate-700 text-slate-300">
              Draft Test Code
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
