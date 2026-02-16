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

interface RecentOrder {
  box_name: string;
  box_sequence: number;
  payment_date: string;
  tracking_number: string | null;
}

interface OrderData {
  found: boolean;
  customer?: {
    email: string;
    name: string;
    customer_number: string;
  };
  subscription?: {
    status: string;
    frequency: string;
    start_date: string;
  };
  orders_summary?: {
    total_subscription_boxes: number;
    total_one_time_orders: number;
    recent_orders: RecentOrder[];
  };
  message?: string;
}

export function OrderHistoryWidget() {
  useHumanInTheLoop({
    name: "display_orders",
    description: "Display customer order history widget.",
    parameters: [
      {
        name: "customer_email",
        type: "string",
        description: "Customer email address",
        required: true,
      },
    ],
    render: ({ args, status, respond }) => {
      const [data, setData] = useState<OrderData | null>(null);
      const [loading, setLoading] = useState(true);
      const [error, setError] = useState<string | null>(null);
      const customerEmail = String(args.customer_email || "");

      useEffect(() => {
        if (!customerEmail) return;
        fetch("/api/copilot/fetch-data", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tool_name: "get_customer_history",
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
                ? `Order history widget displayed (${data.orders_summary?.total_subscription_boxes || 0} boxes)`
                : "Order history displayed"
            );
          }, 500);
          return () => clearTimeout(timer);
        }
      }, [loading, data, status, respond]);

      if (loading) {
        return (
          <Card className="w-full max-w-md mx-auto border-purple-500 animate-pulse">
            <CardContent className="p-6">
              <div className="h-4 bg-slate-200 rounded w-3/4 mb-3" />
              <div className="h-4 bg-slate-200 rounded w-1/2" />
            </CardContent>
          </Card>
        );
      }

      if (error || !data?.found) {
        return (
          <Card className="w-full max-w-md mx-auto border-slate-300">
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">
                {data?.message || error || "No order history available."}
              </p>
            </CardContent>
          </Card>
        );
      }

      const orders = data.orders_summary?.recent_orders || [];

      return (
        <Card className="w-full max-w-md mx-auto border-purple-500">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Order History</CardTitle>
            <CardDescription>
              {data.customer?.name} &middot;{" "}
              {data.orders_summary?.total_subscription_boxes || 0} boxes total
              {(data.orders_summary?.total_one_time_orders || 0) > 0 &&
                ` + ${data.orders_summary?.total_one_time_orders} one-time`}
            </CardDescription>
          </CardHeader>

          <CardContent>
            {/* Subscription info */}
            {data.subscription && (
              <div className="flex gap-2 mb-3 text-xs">
                <span className={`px-2 py-0.5 rounded-full font-medium ${
                  data.subscription.status === "Active"
                    ? "bg-green-100 text-green-700"
                    : "bg-yellow-100 text-yellow-700"
                }`}>
                  {data.subscription.status}
                </span>
                <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                  {data.subscription.frequency}
                </span>
                <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                  Since {data.subscription.start_date}
                </span>
              </div>
            )}

            {/* Orders table */}
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-800">
                    <th className="text-left p-2 font-medium">Box</th>
                    <th className="text-left p-2 font-medium">#</th>
                    <th className="text-left p-2 font-medium">Date</th>
                    <th className="text-left p-2 font-medium">Tracking</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.slice(0, 6).map((order, i) => (
                    <tr key={i} className="border-t">
                      <td className="p-2">{order.box_name}</td>
                      <td className="p-2 text-muted-foreground">{order.box_sequence}</td>
                      <td className="p-2">{order.payment_date}</td>
                      <td className="p-2 font-mono text-[10px]">
                        {order.tracking_number
                          ? order.tracking_number.slice(0, 12) + "..."
                          : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {orders.length > 6 && (
              <p className="text-xs text-muted-foreground mt-2 text-center">
                Showing 6 of {orders.length} recent orders
              </p>
            )}
          </CardContent>
        </Card>
      );
    },
  });

  return <></>;
}
