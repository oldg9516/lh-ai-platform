"use client";

const QUICK_PROMPTS = [
  "What is the current resolution rate?",
  "Show subscription status distribution",
  "Top 10 customers by lifetime value",
  "Which category has the highest escalation rate?",
  "What is the average AI response cost per session?",
  "How many repeat customers contacted support?",
];

export default function DashPage() {
  return (
    <main className="min-h-screen bg-linear-to-b from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight mb-4">
            Dash Analytics
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Self-learning data agent for Lev Haolam. Use the chat sidebar to
            ask questions about customers, subscriptions, orders, and support
            metrics.
          </p>
        </div>

        <div className="max-w-4xl mx-auto space-y-8">
          <div className="bg-white dark:bg-slate-800 rounded-lg shadow-sm p-6">
            <h2 className="text-2xl font-semibold mb-4">Try These Questions</h2>
            <div className="flex flex-wrap gap-3">
              {QUICK_PROMPTS.map((q) => (
                <span
                  key={q}
                  className="text-sm px-4 py-2.5 rounded-lg bg-blue-50 dark:bg-blue-900/20"
                >
                  {q}
                </span>
              ))}
            </div>
          </div>

          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-2">Capabilities</h3>
            <ul className="list-disc list-inside space-y-2 text-sm">
              <li>SQL generation over real customer, order, and subscription data</li>
              <li>Self-learning: validated queries are saved to the knowledge base</li>
              <li>Markdown tables, charts, and insights rendered in the sidebar</li>
            </ul>
          </div>

          <div className="text-center">
            <a
              href="/"
              className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400"
            >
              Switch to Support Chat
            </a>
          </div>
        </div>
      </div>
    </main>
  );
}
