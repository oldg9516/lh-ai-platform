"use client";

import { useHumanInTheLoop } from "@copilotkit/react-core";
import { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface BoxData {
  found: boolean;
  customer_email: string;
  last_box?: {
    box_name: string;
    box_sequence: number;
    sku: string;
    shipping_date: string;
    detailed_contents_available: boolean;
  };
  customization_preferences?: {
    current: string[];
    no_alcohol: boolean;
    no_honey: boolean;
    available_exclusions: string[];
    note: string;
  };
  message?: string;
}

export function BoxContentsWidget() {
  useHumanInTheLoop({
    name: "display_box_contents",
    description: "Display box contents and customization preferences widget.",
    parameters: [
      {
        name: "customer_email",
        type: "string",
        description: "Customer email address",
        required: true,
      },
    ],
    render: ({ args, status, respond }) => {
      const [data, setData] = useState<BoxData | null>(null);
      const [loading, setLoading] = useState(true);
      const [error, setError] = useState<string | null>(null);
      const customerEmail = String(args.customer_email || "");

      useEffect(() => {
        if (!customerEmail) return;
        fetch("/api/copilot/fetch-data", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tool_name: "get_box_contents",
            tool_args: { customer_email: customerEmail },
          }),
        })
          .then((res) => res.json())
          .then((res) => {
            setData(res.result);
            setLoading(false);
          })
          .catch((err) => {
            setError(String(err));
            setLoading(false);
          });
      }, [customerEmail]);

      useEffect(() => {
        if (!loading && data && status === "executing" && respond) {
          const timer = setTimeout(() => {
            respond(
              data.found
                ? `Box contents widget displayed for ${data.last_box?.box_name || "box"}`
                : "Box contents displayed"
            );
          }, 500);
          return () => clearTimeout(timer);
        }
      }, [loading, data, status, respond]);

      if (loading) {
        return (
          <Card className="w-full max-w-md mx-auto border-emerald-500 animate-pulse">
            <CardContent className="p-6">
              <div className="h-4 bg-slate-200 rounded w-3/4 mb-3" />
              <div className="h-4 bg-slate-200 rounded w-1/2" />
            </CardContent>
          </Card>
        );
      }

      if (error || !data?.found || !data?.last_box) {
        return (
          <Card className="w-full max-w-md mx-auto border-slate-300">
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">
                {data?.message || error || "No box information available."}
              </p>
            </CardContent>
          </Card>
        );
      }

      const prefs = data.customization_preferences;

      return (
        <Card className="w-full max-w-md mx-auto border-emerald-500">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Box Contents</CardTitle>
            <CardDescription>
              {data.last_box.box_name} #{data.last_box.box_sequence} &middot;{" "}
              Shipped {data.last_box.shipping_date}
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {/* Box details */}
            <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-lg p-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">SKU</span>
                <span className="font-mono text-xs">{data.last_box.sku}</span>
              </div>
              <div className="flex justify-between text-sm mt-1">
                <span className="text-muted-foreground">Contents</span>
                <span>
                  {data.last_box.detailed_contents_available
                    ? "Detailed list available"
                    : "Standard assortment"}
                </span>
              </div>
            </div>

            {/* Customization preferences */}
            {prefs && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">
                  Customization Preferences
                </p>

                <div className="flex flex-wrap gap-1.5">
                  {prefs.no_alcohol && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                      No Alcohol
                    </span>
                  )}
                  {prefs.no_honey && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                      No Honey
                    </span>
                  )}
                  {!prefs.no_alcohol && !prefs.no_honey && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                      No Exclusions
                    </span>
                  )}
                </div>

                {prefs.available_exclusions.length > 0 && (
                  <p className="text-[10px] text-muted-foreground">
                    Available: {prefs.available_exclusions.join(", ")}
                  </p>
                )}

                <p className="text-[10px] text-muted-foreground italic">
                  {prefs.note}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      );
    },
  });

  return <></>;
}
