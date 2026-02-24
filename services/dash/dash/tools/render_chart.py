"""Generative UI chart tool.

When the agent calls render_chart, AgentOS emits a ToolCallCompleted event.
The AG-UI adapter intercepts this and emits AG-UI ToolCall events so that
CopilotKit's useRenderToolCall hook renders the chart on the frontend.
"""

import json


def render_chart(
    chart_type: str,
    title: str,
    data: str,
    x_key: str,
    y_keys: str,
) -> str:
    """Display an interactive chart in the chat UI.

    Use this tool AFTER running a SQL query to visualize the results.
    The frontend will render the chart using Recharts.

    Args:
        chart_type: One of 'line', 'bar', 'area', 'pie'.
        title: Chart title displayed above the chart.
        data: JSON array of objects (data points). Each object should
              have keys matching x_key and y_keys.
        x_key: Key name for the X axis (e.g., 'day', 'category').
        y_keys: Comma-separated key names for Y axis values
                (e.g., 'count' or 'revenue,cost').
    """
    # Validate JSON
    parsed = json.loads(data)
    if not isinstance(parsed, list):
        return json.dumps({"error": "data must be a JSON array"})

    y_list = [k.strip() for k in y_keys.split(",")]

    return json.dumps({
        "chart_type": chart_type,
        "title": title,
        "data": parsed,
        "x_key": x_key,
        "y_keys": y_list,
        "rendered": True,
    })
