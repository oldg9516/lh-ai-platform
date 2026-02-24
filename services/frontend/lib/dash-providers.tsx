"use client";

import { ReactNode, useState } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";
import { DashChart } from "@/components/DashChart";
import "@copilotkit/react-ui/styles.css";

interface DashProvidersProps {
  children: ReactNode;
}

export function DashProviders({ children }: DashProvidersProps) {
  const [threadId] = useState(() => crypto.randomUUID());

  return (
    <CopilotKit
      runtimeUrl="/api/copilot"
      agent="dash"
      threadId={threadId}
      showDevConsole={process.env.NODE_ENV === "development"}
    >
      {/* Register Generative UI renderers inside CopilotKit context */}
      <DashChart />
      <CopilotSidebar
        defaultOpen={true}
        clickOutsideToClose={false}
        labels={{
          title: "Dash Analytics",
          initial:
            "Ask questions about customers, subscriptions, orders, and support metrics. I can generate SQL queries and visualize results with charts.",
        }}
      >
        {children}
      </CopilotSidebar>
    </CopilotKit>
  );
}
