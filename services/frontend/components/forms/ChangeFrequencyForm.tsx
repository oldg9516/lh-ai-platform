"use client";

import { useHumanInTheLoop } from "@copilotkit/react-core";
import { useState } from "react";
import { toast } from "sonner";
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

export function ChangeFrequencyForm() {
  useHumanInTheLoop({
    name: "change_frequency",
    description: "Change customer subscription frequency. Requires human confirmation.",
    parameters: [
      {
        name: "customer_email",
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
    render: ({ args, status, respond }) => {
      const freqArg = String(args.new_frequency || "monthly");
      const [selectedFrequency, setSelectedFrequency] = useState<string>(freqArg);
      const [loading, setLoading] = useState(false);
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
              tool_name: "change_frequency",
              tool_args: { customer_email: customerEmail, new_frequency: selectedFrequency },
            }),
          });
          if (!res.ok) {
            const errText = res.status === 429 ? "Too many requests. Please wait." : "Server error";
            toast.error(errText);
            respond(`ERROR: ${errText}`);
            return;
          }
          const data = await res.json();
          if (data.status === "completed") {
            toast.success(`Frequency changed to ${data.result.new_frequency}`);
            respond(`APPROVED: Frequency changed to ${data.result.new_frequency}. Next charge: ${data.result.next_charge_date}`);
          } else {
            toast.error(data.result?.message || data.message || "Action failed");
            respond(`ERROR: ${data.result?.message || data.message}`);
          }
        } catch (err) {
          toast.error("Network error. Please check your connection.");
          respond(`ERROR: Failed to execute - ${err}`);
        } finally {
          setLoading(false);
        }
      };

      return (
        <Card className="w-full max-w-md mx-auto border-blue-500">
          <CardHeader>
            <CardTitle>Change Delivery Frequency</CardTitle>
            <CardDescription>
              Update delivery frequency for <strong>{customerEmail}</strong>
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
                disabled={!isExecuting || loading}
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

          <CardFooter className="flex flex-col sm:flex-row gap-2">
            <Button
              variant="default"
              className="flex-1 min-h-[44px]"
              onClick={handleApprove}
              disabled={!isExecuting || loading}
            >
              {loading ? "Processing..." : "Confirm Change"}
            </Button>
            <Button
              variant="outline"
              className="flex-1 min-h-[44px]"
              onClick={() => respond?.("CANCELLED: User declined frequency change")}
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
