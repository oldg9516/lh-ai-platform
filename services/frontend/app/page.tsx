"use client";

import { PauseSubscriptionForm } from "@/components/forms/PauseSubscriptionForm";
import { ChangeFrequencyForm } from "@/components/forms/ChangeFrequencyForm";
import { ChangeAddressForm } from "@/components/forms/ChangeAddressForm";
import { DamageClaimForm } from "@/components/forms/DamageClaimForm";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-linear-to-b from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight mb-4">
            Lev Haolam Support Platform
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            AI-powered customer support with Human-in-the-Loop confirmations.
            Phase 6.1: CopilotKit Prototype
          </p>
        </div>

        <div className="max-w-4xl mx-auto space-y-8">
          <div className="bg-white dark:bg-slate-800 rounded-lg shadow-sm p-6">
            <h2 className="text-2xl font-semibold mb-4">🎯 Phase 6.1 Status</h2>
            <div className="grid gap-4">
              <div className="flex items-start gap-3">
                <span className="text-green-500 font-bold">✅</span>
                <div>
                  <p className="font-medium">Next.js 16 + pnpm + shadcn/ui</p>
                  <p className="text-sm text-muted-foreground">
                    Modern stack with Tailwind CSS 4
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <span className="text-green-500 font-bold">✅</span>
                <div>
                  <p className="font-medium">CopilotKit + React Query installed</p>
                  <p className="text-sm text-muted-foreground">
                    AG-UI protocol ready for streaming
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <span className="text-green-500 font-bold">✅</span>
                <div>
                  <p className="font-medium">4 HITL Forms created (Day 3 complete!)</p>
                  <p className="text-sm text-muted-foreground">
                    PauseSubscription, ChangeFrequency, ChangeAddress, DamageClaim
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <span className="text-orange-500 font-bold">🔄</span>
                <div>
                  <p className="font-medium">AG-UI streaming endpoint (stub)</p>
                  <p className="text-sm text-muted-foreground">
                    /api/copilot created, needs FastAPI integration
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <span className="text-gray-400 font-bold">⏳</span>
                <div>
                  <p className="font-medium">Docker + E2E testing</p>
                  <p className="text-sm text-muted-foreground">
                    Next: Add to docker-compose.yml
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-2">💡 What's Next</h3>
            <ol className="list-decimal list-inside space-y-2 text-sm">
              <li>Connect AG-UI endpoint to FastAPI backend</li>
              <li>Implement real agent streaming with tool calls</li>
              <li>Add Dockerfile and docker-compose service</li>
              <li>Create E2E test: Chatwoot → pause → confirm → Zoho</li>
              <li>Add remaining HITL forms (address, damage claim, etc.)</li>
            </ol>
          </div>
        </div>

        {/* Hidden components - register HITL tools with CopilotKit */}
        <PauseSubscriptionForm />
        <ChangeFrequencyForm />
        <ChangeAddressForm />
        <DamageClaimForm />

        {/* CopilotSidebar will appear here when CopilotKit is active */}
        <div className="fixed bottom-4 right-4">
          <p className="text-xs text-muted-foreground bg-white dark:bg-slate-800 px-3 py-1 rounded-full shadow">
            💬 CopilotKit sidebar will appear here
          </p>
        </div>
      </div>
    </main>
  );
}
