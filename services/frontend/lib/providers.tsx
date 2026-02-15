"use client";

import { ReactNode, useState } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@copilotkit/react-ui/styles.css";

// Create QueryClient instance (Vercel best practice: singleton pattern)
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
      retry: 1,
    },
  },
});

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  // Generate unique threadId for this session (UUID v4 format)
  const [threadId] = useState(() => crypto.randomUUID());

  return (
    <QueryClientProvider client={queryClient}>
      <CopilotKit
        runtimeUrl="/api/copilot"
        agent="default"
        threadId={threadId}
        showDevConsole={process.env.NODE_ENV === "development"}
      >
        <CopilotSidebar
          defaultOpen={false}
          clickOutsideToClose={false}
          labels={{
            title: "Lev Haolam Support",
            initial: "How can I help you today?",
          }}
        >
          {children}
        </CopilotSidebar>
      </CopilotKit>
    </QueryClientProvider>
  );
}
