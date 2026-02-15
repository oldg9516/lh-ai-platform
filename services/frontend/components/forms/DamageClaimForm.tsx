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
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

/**
 * DamageClaimForm - HITL component for damage claim creation
 *
 * Uses CopilotKit's useHumanInTheLoop hook for human-in-the-loop approval flow:
 * 1. Agent calls create_damage_claim tool
 * 2. UI renders with damage details and confirmation buttons
 * 3. User approves or modifies claim details
 * 4. Response sent back to agent with user decision
 */

export function DamageClaimForm() {
  const [item, setItem] = useState<string>("");
  const [description, setDescription] = useState<string>("");

  useHumanInTheLoop({
    name: "create_damage_claim",
    description: "Create damage claim for damaged/leaking item. Requires human confirmation.",
    parameters: [
      {
        name: "email",
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
    render: ({ args, respond, status }) => {
      // Guard: respond must be available for HITL
      if (!respond) return <></>;

      const { email, item_description, damage_description } = args;

      // Initialize with agent's values
      if (item_description && item === "") {
        setItem(item_description);
      }
      if (damage_description && description === "") {
        setDescription(damage_description);
      }

      return (
        <Card className="w-full max-w-md mx-auto border-red-500">
          <CardHeader>
            <CardTitle>📦 Create Damage Claim</CardTitle>
            <CardDescription>
              File damage report for <strong>{email}</strong>
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
                disabled={status !== "executing"}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Damage Description</Label>
              <Textarea
                id="description"
                placeholder="Describe the damage (e.g., bottle cracked, oil leaked)"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={status !== "executing"}
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

          <CardFooter className="flex gap-2">
            <Button
              variant="default"
              className="flex-1"
              onClick={() =>
                respond(`APPROVED: Item: ${item}, Damage: ${description}`)
              }
              disabled={status !== "executing" || !item || !description}
            >
              ✅ Create Claim
            </Button>
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => respond("CANCELLED: User declined claim creation")}
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
