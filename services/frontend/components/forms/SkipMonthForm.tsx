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

function getUpcomingMonths(): { value: string; label: string }[] {
  const months = [];
  const now = new Date();
  for (let i = 1; i <= 6; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
    const value = d.toLocaleDateString("en-US", { year: "numeric", month: "long" });
    months.push({ value, label: value });
  }
  return months;
}

export function SkipMonthForm() {
  useHumanInTheLoop({
    name: "skip_month",
    description: "Skip one month of customer subscription. Requires human confirmation.",
    parameters: [
      {
        name: "customer_email",
        type: "string",
        description: "Customer email address",
        required: true,
      },
      {
        name: "month",
        type: "string",
        description: "Which month to skip (e.g., 'next' or specific month name)",
        required: false,
      },
    ],
    render: ({ args, status, respond }) => {
      const monthArg = String(args.month || "next");
      const [selectedMonth, setSelectedMonth] = useState<string>(monthArg);
      const [loading, setLoading] = useState(false);
      const upcomingMonths = getUpcomingMonths();
      const customerEmail = String(args.customer_email || "");

      if (status === "complete") {
        return (
          <Card className="w-full max-w-md mx-auto border-green-500">
            <CardContent className="p-4">
              <p className="text-sm text-green-700">Action completed.</p>
            </CardContent>
          </Card>
        );
      }

      const isExecuting = status === "executing" && !!respond;

      const handleApprove = async () => {
        if (!respond) return;
        setLoading(true);
        try {
          const res = await fetch("/api/copilot/execute-tool", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              tool_name: "skip_month",
              tool_args: { customer_email: customerEmail, month: selectedMonth },
            }),
          });
          const data = await res.json();
          if (data.status === "completed") {
            respond(`APPROVED: Skipped ${data.result.skipped_month}. Next charge: ${data.result.next_charge_date}`);
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
        <Card className="w-full max-w-md mx-auto border-amber-500">
          <CardHeader>
            <CardTitle>Skip Month</CardTitle>
            <CardDescription>
              Skip a delivery month for <strong>{customerEmail}</strong>
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="skip-month">
                Month to Skip: <strong>{selectedMonth === "next" ? "Next month" : selectedMonth}</strong>
              </Label>
              <Select
                value={selectedMonth}
                onValueChange={setSelectedMonth}
                disabled={!isExecuting || loading}
              >
                <SelectTrigger id="skip-month">
                  <SelectValue placeholder="Select month to skip" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="next">Next month</SelectItem>
                  {upcomingMonths.map((m) => (
                    <SelectItem key={m.value} value={m.value}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="bg-amber-50 dark:bg-amber-900/20 p-4 rounded-lg">
              <p className="text-sm">
                <strong>What happens:</strong>
              </p>
              <ul className="text-sm list-disc list-inside mt-2 space-y-1">
                <li>No delivery for the selected month</li>
                <li>No charge for that month</li>
                <li>Subscription continues next month</li>
                <li>Can be reversed before the skip date</li>
              </ul>
            </div>
          </CardContent>

          <CardFooter className="flex gap-2">
            <Button
              variant="default"
              className="flex-1"
              onClick={handleApprove}
              disabled={!isExecuting || loading}
            >
              {loading ? "Processing..." : "Confirm Skip"}
            </Button>
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => respond?.("CANCELLED: User declined skip")}
              disabled={!isExecuting || loading}
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
