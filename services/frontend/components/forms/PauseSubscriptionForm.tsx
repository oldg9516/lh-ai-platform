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

export function PauseSubscriptionForm() {
  const [selectedMonths, setSelectedMonths] = useState<number>(1);
  const [loading, setLoading] = useState(false);

  useHumanInTheLoop({
    name: "pause_subscription",
    description: "Pause customer subscription for N months. Requires human confirmation.",
    parameters: [
      {
        name: "customer_email",
        type: "string",
        description: "Customer email address",
        required: true,
      },
      {
        name: "duration_months",
        type: "number",
        description: "Number of months to pause (1-12)",
        required: true,
      },
    ],
    render: ({ args, respond, status }) => {
      if (!respond) return <></>;

      const { customer_email, duration_months } = args;

      const handleApprove = async () => {
        setLoading(true);
        try {
          const res = await fetch("/api/copilot/execute-tool", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              tool_name: "pause_subscription",
              tool_args: { customer_email, duration_months: selectedMonths },
            }),
          });
          const data = await res.json();
          if (data.status === "completed") {
            respond(`APPROVED: Subscription paused until ${data.result.paused_until}`);
          } else {
            respond(`ERROR: ${data.result?.message || data.message}`);
          }
        } catch (err) {
          respond(`ERROR: Failed to execute - ${err}`);
        } finally {
          setLoading(false);
        }
      };

      return (
        <Card className="w-full max-w-md mx-auto border-orange-500">
          <CardHeader>
            <CardTitle>Pause Subscription</CardTitle>
            <CardDescription>
              Confirm subscription pause for <strong>{customer_email}</strong>
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
                disabled={status !== "executing" || loading}
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
              onClick={handleApprove}
              disabled={status !== "executing" || loading}
            >
              {loading ? "Processing..." : "Confirm Pause"}
            </Button>
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => respond("CANCELLED: User declined pause")}
              disabled={status !== "executing" || loading}
            >
              Cancel
            </Button>
          </CardFooter>
        </Card>
      );
    },
  });

  return <></>;
}
