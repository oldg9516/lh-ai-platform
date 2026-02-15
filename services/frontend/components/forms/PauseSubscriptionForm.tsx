"use client";

import { useHumanInTheLoop } from "@copilotkit/react-core";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";

/**
 * PauseSubscriptionForm - HITL component for subscription pause
 *
 * Uses CopilotKit's useHumanInTheLoop hook for human-in-the-loop approval flow:
 * 1. Agent calls pause_subscription tool
 * 2. UI renders with month selector and confirmation buttons
 * 3. User approves or cancels
 * 4. Response sent back to agent with user decision
 */

export function PauseSubscriptionForm() {
  const [selectedMonths, setSelectedMonths] = useState<number>(1);

  useHumanInTheLoop({
    name: "pause_subscription",
    description: "Pause customer subscription for N months. Requires human confirmation.",
    parameters: [
      {
        name: "email",
        type: "string",
        description: "Customer email address",
        required: true,
      },
      {
        name: "months",
        type: "number",
        description: "Number of months to pause (1-12)",
        required: true,
      },
    ],
    render: ({ args, respond, status }) => {
      // Guard: respond must be available for HITL
      if (!respond) return <></>;

      const { email, months } = args;

      return (
        <Card className="w-full max-w-md mx-auto border-orange-500">
          <CardHeader>
            <CardTitle>⏸️ Pause Subscription</CardTitle>
            <CardDescription>
              Confirm subscription pause for <strong>{email}</strong>
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="months">
                Pause Duration: <strong>{selectedMonths} month(s)</strong>
              </Label>
              <Slider
                id="months"
                min={1}
                max={12}
                step={1}
                value={[selectedMonths]}
                onValueChange={(value) => setSelectedMonths(value[0])}
                className="w-full"
                disabled={status !== "executing"}
              />
              <p className="text-sm text-muted-foreground">
                Subscription will resume automatically after {selectedMonths} month(s)
              </p>
            </div>

            <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
              <p className="text-sm">
                <strong>What happens:</strong>
              </p>
              <ul className="text-sm list-disc list-inside mt-2 space-y-1">
                <li>No charges for {selectedMonths} month(s)</li>
                <li>Deliveries will pause</li>
                <li>Subscription resumes automatically</li>
                <li>You can unpause anytime</li>
              </ul>
            </div>
          </CardContent>

          <CardFooter className="flex gap-2">
            <Button
              variant="default"
              className="flex-1"
              onClick={() => respond(`APPROVED: Pause for ${selectedMonths} months`)}
              disabled={status !== "executing"}
            >
              ✅ Confirm Pause
            </Button>
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => respond("CANCELLED: User declined pause")}
              disabled={status !== "executing"}
            >
              ❌ Cancel
            </Button>
          </CardFooter>
        </Card>
      );
    },
  });

  // This component doesn't render anything directly
  // The render function above handles all UI
  return <></>;
}
