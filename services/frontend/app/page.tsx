"use client";

import { PauseSubscriptionForm } from "@/components/forms/PauseSubscriptionForm";
import { ChangeFrequencyForm } from "@/components/forms/ChangeFrequencyForm";
import { ChangeAddressForm } from "@/components/forms/ChangeAddressForm";
import { DamageClaimForm } from "@/components/forms/DamageClaimForm";
import { SkipMonthForm } from "@/components/forms/SkipMonthForm";

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
            Open the chat sidebar to get started.
          </p>
        </div>

        <div className="max-w-4xl mx-auto space-y-8">
          <div className="bg-white dark:bg-slate-800 rounded-lg shadow-sm p-6">
            <h2 className="text-2xl font-semibold mb-4">Platform Features</h2>
            <div className="grid gap-4">
              <div className="flex items-start gap-3">
                <span className="text-green-500 font-bold">*</span>
                <div>
                  <p className="font-medium">5 HITL Confirmation Forms</p>
                  <p className="text-sm text-muted-foreground">
                    Pause, Frequency, Address, Damage Claim, Skip Month
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <span className="text-green-500 font-bold">*</span>
                <div>
                  <p className="font-medium">AI Agent with 12 Action Tools</p>
                  <p className="text-sm text-muted-foreground">
                    Read-only lookups + write operations with approval
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <span className="text-green-500 font-bold">*</span>
                <div>
                  <p className="font-medium">AG-UI Protocol Streaming</p>
                  <p className="text-sm text-muted-foreground">
                    Real-time responses via CopilotKit sidebar
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-2">Try It Out</h3>
            <p className="text-sm mb-3">Click the chat button in the bottom-right corner and try:</p>
            <ul className="list-disc list-inside space-y-2 text-sm">
              <li>&quot;I want to pause my subscription. My email is audreygs1955@me.com&quot;</li>
              <li>&quot;Can I skip next month? Email: mmefred1@gmail.com&quot;</li>
              <li>&quot;I need to change my delivery frequency to quarterly&quot;</li>
              <li>&quot;My olive oil bottle arrived cracked and leaking&quot;</li>
            </ul>
          </div>
        </div>

        {/* Hidden components - register HITL tools with CopilotKit */}
        <PauseSubscriptionForm />
        <ChangeFrequencyForm />
        <ChangeAddressForm />
        <DamageClaimForm />
        <SkipMonthForm />
      </div>
    </main>
  );
}
