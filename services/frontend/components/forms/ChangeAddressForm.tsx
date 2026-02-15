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
  const [street, setStreet] = useState<string>("");
  const [city, setCity] = useState<string>("");
  const [country, setCountry] = useState<string>("Israel");
  const [loading, setLoading] = useState(false);

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
    render: ({ args, respond, status }) => {
      if (!respond) return <></>;

      const { customer_email, new_address } = args;

      if (new_address && street === "") {
        const parts = new_address.split(",").map((p: string) => p.trim());
        setStreet(parts[0] || "");
        setCity(parts[1] || "");
        setCountry(parts[2] || "Israel");
      }

      const fullAddress = `${street}, ${city}, ${country}`;

      const handleApprove = async () => {
        setLoading(true);
        try {
          const res = await fetch("/api/copilot/execute-tool", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              tool_name: "change_address",
              tool_args: { customer_email, new_address: fullAddress },
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
              Update delivery address for <strong>{customer_email}</strong>
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
                disabled={status !== "executing" || loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="city">City</Label>
              <Input
                id="city"
                placeholder="Tel Aviv"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                disabled={status !== "executing" || loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="country">Country</Label>
              <Input
                id="country"
                placeholder="Israel"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                disabled={status !== "executing" || loading}
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
              disabled={status !== "executing" || !street || !city || loading}
            >
              {loading ? "Processing..." : "Confirm Address"}
            </Button>
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => respond("CANCELLED: User declined address change")}
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
