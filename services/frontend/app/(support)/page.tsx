"use client";

import { PauseSubscriptionForm } from "@/components/forms/PauseSubscriptionForm";
import { ChangeFrequencyForm } from "@/components/forms/ChangeFrequencyForm";
import { ChangeAddressForm } from "@/components/forms/ChangeAddressForm";
import { DamageClaimForm } from "@/components/forms/DamageClaimForm";
import { SkipMonthForm } from "@/components/forms/SkipMonthForm";
import { TrackingWidget } from "@/components/widgets/TrackingWidget";
import { OrderHistoryWidget } from "@/components/widgets/OrderHistoryWidget";
import { BoxContentsWidget } from "@/components/widgets/BoxContentsWidget";
import { PaymentHistoryWidget } from "@/components/widgets/PaymentHistoryWidget";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-linear-to-b from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight mb-4">
            Welcome to Lev Haolam Support
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            We&apos;re here to help with your subscription, deliveries, and
            more. Open the chat to get started.
          </p>
        </div>

        <div className="max-w-4xl mx-auto space-y-8">
          <div className="bg-white dark:bg-slate-800 rounded-lg shadow-sm p-6">
            <h2 className="text-2xl font-semibold mb-4">How can we help?</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="flex items-start gap-3 p-3 rounded-md bg-slate-50 dark:bg-slate-700/50">
                <span className="text-blue-500 text-xl">&#x1f4e6;</span>
                <div>
                  <p className="font-medium">Shipping &amp; Delivery</p>
                  <p className="text-sm text-muted-foreground">
                    Track packages, delivery questions
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-md bg-slate-50 dark:bg-slate-700/50">
                <span className="text-green-500 text-xl">&#x1f4b3;</span>
                <div>
                  <p className="font-medium">Payments &amp; Billing</p>
                  <p className="text-sm text-muted-foreground">
                    Payment history, billing questions
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-md bg-slate-50 dark:bg-slate-700/50">
                <span className="text-purple-500 text-xl">&#x1f504;</span>
                <div>
                  <p className="font-medium">Subscription Changes</p>
                  <p className="text-sm text-muted-foreground">
                    Pause, skip, change frequency or address
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-md bg-slate-50 dark:bg-slate-700/50">
                <span className="text-orange-500 text-xl">&#x1f6e0;&#xfe0f;</span>
                <div>
                  <p className="font-medium">Damaged Items</p>
                  <p className="text-sm text-muted-foreground">
                    Report damaged or leaking products
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-2">Quick Start</h3>
            <p className="text-sm mb-3">Click the chat button and try asking:</p>
            <ul className="list-disc list-inside space-y-2 text-sm">
              <li>&quot;Where is my package?&quot;</li>
              <li>&quot;I want to pause my subscription&quot;</li>
              <li>&quot;Can I skip next month?&quot;</li>
              <li>&quot;My item arrived damaged&quot;</li>
            </ul>
          </div>
        </div>

        {/* Hidden components - register HITL tools with CopilotKit */}
        <PauseSubscriptionForm />
        <ChangeFrequencyForm />
        <ChangeAddressForm />
        <DamageClaimForm />
        <SkipMonthForm />
        {/* Informational display widgets */}
        <TrackingWidget />
        <OrderHistoryWidget />
        <BoxContentsWidget />
        <PaymentHistoryWidget />
      </div>
    </main>
  );
}
