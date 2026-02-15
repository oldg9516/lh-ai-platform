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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/**
 * ChangeFrequencyForm - HITL component for subscription frequency change
 *
 * Uses CopilotKit's useHumanInTheLoop hook for human-in-the-loop approval flow:
 * 1. Agent calls change_frequency tool
 * 2. UI renders with frequency selector and confirmation buttons
 * 3. User approves or cancels
 * 4. Response sent back to agent with user decision
 */

export function ChangeFrequencyForm() {
  const [selectedFrequency, setSelectedFrequency] = useState<string>("monthly");

  useHumanInTheLoop({
    name: "change_frequency",
    description: "Change customer subscription frequency. Requires human confirmation.",
    parameters: [
      {
        name: "email",
        type: "string",
        description: "Customer email address",
        required: true,
      },
      {
        name: "new_frequency",
        type: "string",
        description: "New delivery frequency: monthly, bi-monthly, or quarterly",
        required: true,
      },
    ],
    render: ({ args, respond, status }) => {
      // Guard: respond must be available for HITL
      if (!respond) return <></>;

      const { email, new_frequency } = args;

      // Initialize with agent's suggested frequency
      if (new_frequency && selectedFrequency !== new_frequency) {
        setSelectedFrequency(new_frequency);
      }

      return (
        <Card className="w-full max-w-md mx-auto border-blue-500">
          <CardHeader>
            <CardTitle>🔄 Change Delivery Frequency</CardTitle>
            <CardDescription>
              Update delivery frequency for <strong>{email}</strong>
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="frequency">
                New Frequency: <strong>{selectedFrequency}</strong>
              </Label>
              <Select
                value={selectedFrequency}
                onValueChange={setSelectedFrequency}
                disabled={status !== "executing"}
              >
                <SelectTrigger id="frequency">
                  <SelectValue placeholder="Select frequency" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="monthly">Monthly (Every month)</SelectItem>
                  <SelectItem value="bi-monthly">Bi-Monthly (Every 2 months)</SelectItem>
                  <SelectItem value="quarterly">Quarterly (Every 3 months)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
              <p className="text-sm">
                <strong>What happens:</strong>
              </p>
              <ul className="text-sm list-disc list-inside mt-2 space-y-1">
                <li>Frequency changed to {selectedFrequency}</li>
                <li>Next charge date will be updated</li>
                <li>Confirmation email sent to customer</li>
                <li>Can be changed again anytime</li>
              </ul>
            </div>
          </CardContent>

          <CardFooter className="flex gap-2">
            <Button
              variant="default"
              className="flex-1"
              onClick={() => respond(`APPROVED: Change to ${selectedFrequency}`)}
              disabled={status !== "executing"}
            >
              ✅ Confirm Change
            </Button>
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => respond("CANCELLED: User declined frequency change")}
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
