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
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

export function DamageClaimForm() {
  useHumanInTheLoop({
    name: "create_damage_claim",
    description: "Create damage claim for damaged/leaking item. Requires human confirmation.",
    parameters: [
      {
        name: "customer_email",
        type: "string",
        description: "Customer email address",
        required: true,
      },
      {
        name: "item_description",
        type: "string",
        description: "Which item was damaged (e.g., 'olive oil bottle')",
        required: true,
      },
      {
        name: "damage_description",
        type: "string",
        description: "Description of the damage (e.g., 'bottle cracked, oil leaked')",
        required: true,
      },
    ],
    render: ({ args, status, respond }) => {
      const [item, setItem] = useState<string>(String(args.item_description || ""));
      const [description, setDescription] = useState<string>(String(args.damage_description || ""));
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
              tool_name: "create_damage_claim",
              tool_args: {
                customer_email: customerEmail,
                item_description: item,
                damage_description: description,
              },
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
            toast.success(`Damage claim ${data.result.claim_id} created`);
            respond(`APPROVED: Claim ${data.result.claim_id} created. ${data.result.message}`);
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
        <Card className="w-full max-w-md mx-auto border-red-500">
          <CardHeader>
            <CardTitle>Create Damage Claim</CardTitle>
            <CardDescription>
              File damage report for <strong>{customerEmail}</strong>
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="item">Damaged Item</Label>
              <Input
                id="item"
                placeholder="e.g., olive oil bottle"
                value={item}
                onChange={(e) => setItem(e.target.value)}
                disabled={!isExecuting || loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Damage Description</Label>
              <Textarea
                id="description"
                placeholder="Describe the damage (e.g., bottle cracked, oil leaked)"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={!isExecuting || loading}
                rows={4}
              />
            </div>

            <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
              <p className="text-sm">
                <strong>What happens:</strong>
              </p>
              <ul className="text-sm list-disc list-inside mt-2 space-y-1">
                <li>Damage claim created in system</li>
                <li>Customer receives claim ID</li>
                <li>Photo upload link sent via email</li>
                <li>Support team will review within 24-48 hours</li>
              </ul>
            </div>
          </CardContent>

          <CardFooter className="flex flex-col sm:flex-row gap-2">
            <Button
              variant="default"
              className="flex-1 min-h-[44px]"
              onClick={handleApprove}
              disabled={!isExecuting || !item || !description || loading}
            >
              {loading ? "Processing..." : "Create Claim"}
            </Button>
            <Button
              variant="outline"
              className="flex-1 min-h-[44px]"
              onClick={() => respond?.("CANCELLED: User declined claim creation")}
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
