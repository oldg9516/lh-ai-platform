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

interface TrackingEvent {
  timestamp: string;
  status: string;
  location: string;
}

interface TrackingData {
  found: boolean;
  customer_email: string;
  tracking_number?: string;
  carrier?: string;
  delivery_status?: string;
  delivery_date?: string;
  shipped_date?: string;
  box_name?: string;
  box_sequence?: number;
  history?: TrackingEvent[];
  message?: string;
}

const STATUS_STEPS = ["Shipped", "In Transit", "Out for Delivery", "Delivered"];

function getStatusIndex(status: string): number {
  const lower = status.toLowerCase();
  if (lower.includes("deliver") && !lower.includes("out for")) return 3;
  if (lower.includes("out for")) return 2;
  if (lower.includes("transit")) return 1;
  return 0;
}

export function TrackingWidget() {
  useHumanInTheLoop({
    name: "display_tracking",
    description: "Display package tracking information widget.",
    parameters: [
      {
        name: "customer_email",
        type: "string",
        description: "Customer email address",
        required: true,
      },
    ],
    render: ({ args, status, respond }) => {
      const [data, setData] = useState<TrackingData | null>(null);
      const [loading, setLoading] = useState(true);
      const [error, setError] = useState<string | null>(null);
      const customerEmail = String(args.customer_email || "");

      useEffect(() => {
        if (!customerEmail) return;
        fetch("/api/copilot/fetch-data", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tool_name: "track_package",
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

      // Auto-respond once data is loaded
      useEffect(() => {
        if (!loading && data && status === "executing" && respond) {
          const timer = setTimeout(() => {
            respond(
              data.found && data.tracking_number
                ? `Tracking widget displayed for ${data.tracking_number}`
                : "Tracking data displayed"
            );
          }, 500);
          return () => clearTimeout(timer);
        }
      }, [loading, data, status, respond]);

      if (loading) {
        return (
          <Card className="w-full max-w-md mx-auto border-blue-500 animate-pulse">
            <CardContent className="p-6">
              <div className="h-4 bg-slate-200 rounded w-3/4 mb-3" />
              <div className="h-4 bg-slate-200 rounded w-1/2" />
            </CardContent>
          </Card>
        );
      }

      if (error || !data?.found || !data?.tracking_number) {
        return (
          <Card className="w-full max-w-md mx-auto border-slate-300">
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">
                {data?.message || error || "No tracking information available."}
              </p>
            </CardContent>
          </Card>
        );
      }

      const statusIdx = getStatusIndex(data.delivery_status || "Shipped");

      return (
        <Card className="w-full max-w-md mx-auto border-blue-500">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              Package Tracking
            </CardTitle>
            <CardDescription>
              {data.box_name && `${data.box_name} #${data.box_sequence} - `}
              {data.carrier}
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {/* Tracking number */}
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Tracking #</span>
              <span className="font-mono font-medium">{data.tracking_number}</span>
            </div>

            {/* Progress bar */}
            <div className="space-y-2">
              <div className="flex justify-between">
                {STATUS_STEPS.map((step, i) => (
                  <div key={step} className="flex flex-col items-center flex-1">
                    <div
                      className={`w-3 h-3 rounded-full ${
                        i <= statusIdx
                          ? "bg-blue-500"
                          : "bg-slate-200"
                      }`}
                    />
                    <span className="text-[10px] mt-1 text-center text-muted-foreground">
                      {step}
                    </span>
                  </div>
                ))}
              </div>
              <div className="h-1 bg-slate-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all"
                  style={{ width: `${((statusIdx + 1) / STATUS_STEPS.length) * 100}%` }}
                />
              </div>
            </div>

            {/* Details */}
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <p className="text-muted-foreground">Status</p>
                <p className="font-medium">{data.delivery_status}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Est. Delivery</p>
                <p className="font-medium">{data.delivery_date || "TBD"}</p>
              </div>
              {data.shipped_date && (
                <div>
                  <p className="text-muted-foreground">Shipped</p>
                  <p className="font-medium">{data.shipped_date}</p>
                </div>
              )}
            </div>

            {/* Tracking history */}
            {data.history && data.history.length > 0 && (
              <div className="border-t pt-3">
                <p className="text-xs font-medium mb-2 text-muted-foreground">History</p>
                <div className="space-y-2">
                  {data.history.slice(0, 4).map((event, i) => (
                    <div key={i} className="flex gap-2 text-xs">
                      <div className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 shrink-0" />
                      <div>
                        <p className="font-medium">{event.status}</p>
                        <p className="text-muted-foreground">
                          {event.location} &middot; {new Date(event.timestamp).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      );
    },
  });

  return <></>;
}
