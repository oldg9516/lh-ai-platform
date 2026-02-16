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

interface Payment {
  date: string;
  amount: number;
  currency: string;
  box_name: string;
  box_sequence: number;
  order_type: string;
  invoice: string;
}

interface PaymentData {
  found: boolean;
  customer_email: string;
  payments?: Payment[];
  next_payment_date?: string;
  payment_method?: string;
  payment_method_id?: string;
  message?: string;
}

export function PaymentHistoryWidget() {
  useHumanInTheLoop({
    name: "display_payments",
    description: "Display payment history widget.",
    parameters: [
      {
        name: "customer_email",
        type: "string",
        description: "Customer email address",
        required: true,
      },
    ],
    render: ({ args, status, respond }) => {
      const [data, setData] = useState<PaymentData | null>(null);
      const [loading, setLoading] = useState(true);
      const [error, setError] = useState<string | null>(null);
      const customerEmail = String(args.customer_email || "");

      useEffect(() => {
        if (!customerEmail) return;
        fetch("/api/copilot/fetch-data", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tool_name: "get_payment_history",
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
                ? `Payment history widget displayed (${data.payments?.length || 0} payments)`
                : "Payment history displayed"
            );
          }, 500);
          return () => clearTimeout(timer);
        }
      }, [loading, data, status, respond]);

      if (loading) {
        return (
          <Card className="w-full max-w-md mx-auto border-indigo-500 animate-pulse">
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
                {data?.message || error || "No payment history available."}
              </p>
            </CardContent>
          </Card>
        );
      }

      const payments = data.payments || [];
      const totalAmount = payments.reduce((sum, p) => sum + p.amount, 0);

      return (
        <Card className="w-full max-w-md mx-auto border-indigo-500">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Payment History</CardTitle>
            <CardDescription>
              {payments.length} payments &middot; Total: $
              {totalAmount.toFixed(2)}{" "}
              {data.payment_method && `&middot; ${data.payment_method}`}
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {/* Next payment */}
            {data.next_payment_date && (
              <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-3 flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Next payment</span>
                <span className="text-sm font-medium">{data.next_payment_date}</span>
              </div>
            )}

            {/* Payment timeline */}
            <div className="space-y-2">
              {payments.slice(0, 6).map((payment, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 text-sm border-l-2 border-indigo-200 pl-3 py-1"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between">
                      <span className="font-medium truncate">
                        {payment.box_name} #{payment.box_sequence}
                      </span>
                      <span className="font-medium text-green-600">
                        ${payment.amount.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>{payment.date}</span>
                      <span className="font-mono">{payment.invoice}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {payments.length > 6 && (
              <p className="text-xs text-muted-foreground text-center">
                Showing 6 of {payments.length} payments
              </p>
            )}
          </CardContent>
        </Card>
      );
    },
  });

  return <></>;
}
