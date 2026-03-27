"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

export default function SettingsPage() {
  return (
    <div className="p-6 space-y-6 max-w-3xl mx-auto">
      <h1 className="text-lg font-semibold text-slate-50">Settings</h1>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-base text-slate-50">Project Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Project Name</label>
            <Input
              defaultValue="context-graph"
              className="bg-slate-800/50 border-slate-700 text-slate-200"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Repository URL</label>
            <Input
              defaultValue="https://github.com/user/context-graph"
              className="bg-slate-800/50 border-slate-700 text-slate-200"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Default Branch</label>
            <Input
              defaultValue="main"
              className="bg-slate-800/50 border-slate-700 text-slate-200"
            />
          </div>
        </CardContent>
      </Card>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-base text-slate-50">Integrations</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {["GitHub", "GitNexus", "Datadog", "Jira", "Slack"].map((integration) => (
            <div
              key={integration}
              className="flex items-center justify-between py-2"
            >
              <div>
                <p className="text-sm text-slate-200">{integration}</p>
                <p className="text-xs text-slate-500">Not connected</p>
              </div>
              <Button variant="outline" size="sm" className="border-slate-700 text-slate-400">
                Connect
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      <Separator className="bg-slate-800" />

      <div className="flex justify-end">
        <Button className="bg-blue-600 hover:bg-blue-500 text-white">
          Save Changes
        </Button>
      </div>
    </div>
  );
}
