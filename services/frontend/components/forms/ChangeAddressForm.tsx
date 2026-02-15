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
import { Input } from "@/components/ui/input";

/**
 * ChangeAddressForm - HITL component for shipping address change
 *
 * Uses CopilotKit's useHumanInTheLoop hook for human-in-the-loop approval flow:
 * 1. Agent calls change_address tool
 * 2. UI renders with address fields and confirmation buttons
 * 3. User approves or modifies address
 * 4. Response sent back to agent with user decision
 */

export function ChangeAddressForm() {
  const [street, setStreet] = useState<string>("");
  const [city, setCity] = useState<string>("");
  const [country, setCountry] = useState<string>("Israel");

  useHumanInTheLoop({
    name: "change_address",
    description: "Change customer shipping address. Requires human confirmation.",
    parameters: [
      {
        name: "email",
        type: "string",
        description: "Customer email address",
        required: true,
      },
      {
        name: "new_address",
        type: "string",
        description: "New shipping address (street, city, country)",
        required: true,
      },
    ],
    render: ({ args, respond, status }) => {
      // Guard: respond must be available for HITL
      if (!respond) return <></>;

      const { email, new_address } = args;

      // Parse address if provided as string
      if (new_address && street === "") {
        const parts = new_address.split(",").map((p) => p.trim());
        setStreet(parts[0] || "");
        setCity(parts[1] || "");
        setCountry(parts[2] || "Israel");
      }

      const fullAddress = `${street}, ${city}, ${country}`;

      return (
        <Card className="w-full max-w-md mx-auto border-green-500">
          <CardHeader>
            <CardTitle>📍 Change Shipping Address</CardTitle>
            <CardDescription>
              Update delivery address for <strong>{email}</strong>
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="street">Street Address</Label>
              <Input
                id="street"
                placeholder="123 Main St, Apt 4B"
                value={street}
                onChange={(e) => setStreet(e.target.value)}
                disabled={status !== "executing"}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="city">City</Label>
              <Input
                id="city"
                placeholder="Tel Aviv"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                disabled={status !== "executing"}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="country">Country</Label>
              <Input
                id="country"
                placeholder="Israel"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                disabled={status !== "executing"}
              />
            </div>

            <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
              <p className="text-sm">
                <strong>What happens:</strong>
              </p>
              <ul className="text-sm list-disc list-inside mt-2 space-y-1">
                <li>Address validated and updated</li>
                <li>Future boxes ship to new address</li>
                <li>Confirmation email sent to customer</li>
                <li>No impact on current orders</li>
              </ul>
            </div>
          </CardContent>

          <CardFooter className="flex gap-2">
            <Button
              variant="default"
              className="flex-1"
              onClick={() => respond(`APPROVED: ${fullAddress}`)}
              disabled={status !== "executing" || !street || !city}
            >
              ✅ Confirm Address
            </Button>
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => respond("CANCELLED: User declined address change")}
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
