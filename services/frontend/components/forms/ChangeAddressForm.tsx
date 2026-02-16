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

export function ChangeAddressForm() {
  useHumanInTheLoop({
    name: "change_address",
    description: "Change customer shipping address. Requires human confirmation.",
    parameters: [
      {
        name: "customer_email",
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
    render: ({ args, status, respond }) => {
      const addressArg = String(args.new_address || "");
      const parts = addressArg ? addressArg.split(",").map((p) => p.trim()) : [];

      const [street, setStreet] = useState<string>(parts[0] || "");
      const [city, setCity] = useState<string>(parts[1] || "");
      const [country, setCountry] = useState<string>(parts[2] || "Israel");
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
      const fullAddress = `${street}, ${city}, ${country}`;

      const handleApprove = async () => {
        if (!respond) return;
        setLoading(true);
        try {
          const res = await fetch("/api/copilot/execute-tool", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              tool_name: "change_address",
              tool_args: { customer_email: customerEmail, new_address: fullAddress },
            }),
          });
          const data = await res.json();
          if (data.status === "completed") {
            respond(`APPROVED: Address updated to ${data.result.new_address}`);
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
        <Card className="w-full max-w-md mx-auto border-green-500">
          <CardHeader>
            <CardTitle>Change Shipping Address</CardTitle>
            <CardDescription>
              Update delivery address for <strong>{customerEmail}</strong>
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
                disabled={!isExecuting || loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="city">City</Label>
              <Input
                id="city"
                placeholder="Tel Aviv"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                disabled={!isExecuting || loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="country">Country</Label>
              <Input
                id="country"
                placeholder="Israel"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                disabled={!isExecuting || loading}
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
              onClick={handleApprove}
              disabled={!isExecuting || !street || !city || loading}
            >
              {loading ? "Processing..." : "Confirm Address"}
            </Button>
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => respond?.("CANCELLED: User declined address change")}
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
