"""Plotly chart endpoints.

Returns chart data as JSON that can be rendered in frontend or Jupyter notebooks.
"""

import asyncio
import json

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import plotly.graph_objects as go
import plotly.utils

from database.queries import get_category_breakdown, get_daily_trends

router = APIRouter()


@router.get("/category-distribution")
async def category_distribution_chart(
    days: int = Query(7, ge=1, le=90, description="Number of days to look back")
):
    """Return Plotly bar chart JSON for category distribution.

    Example usage in frontend:
        fetch('/charts/category-distribution?days=7')
            .then(r => r.json())
            .then(fig => Plotly.newPlot('chart-div', fig.data, fig.layout))
    """
    data = await asyncio.to_thread(get_category_breakdown, days)

    if not data:
        # Empty chart
        fig = go.Figure()
        fig.update_layout(
            title=f"No data for last {days} days",
            template="plotly_white",
        )
    else:
        categories = [row["category"] for row in data]
        counts = [row["count"] for row in data]

        fig = go.Figure(
            data=[go.Bar(x=categories, y=counts, marker_color="lightblue")]
        )
        fig.update_layout(
            title=f"Messages by Category (Last {days} Days)",
            xaxis_title="Category",
            yaxis_title="Count",
            template="plotly_white",
        )

    # Return JSON (Plotly-compatible format)
    return JSONResponse(
        content=json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig))
    )


@router.get("/resolution-trend")
async def resolution_trend_chart(
    days: int = Query(30, ge=7, le=90, description="Number of days to look back")
):
    """Line chart showing resolution rate over time.

    Helps identify trends and anomalies in AI performance.
    """
    data = await asyncio.to_thread(get_daily_trends, days)

    if not data:
        fig = go.Figure()
        fig.update_layout(
            title=f"No data for last {days} days",
            template="plotly_white",
        )
    else:
        dates = [row["day"] for row in data]
        resolution_rates = [row["resolution_rate_pct"] for row in data]

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=dates,
                    y=resolution_rates,
                    mode="lines+markers",
                    line=dict(color="green", width=2),
                    marker=dict(size=6),
                )
            ]
        )
        fig.update_layout(
            title="AI Resolution Rate Trend",
            xaxis_title="Date",
            yaxis_title="Resolution Rate (%)",
            yaxis=dict(range=[0, 100]),
            template="plotly_white",
        )

    return JSONResponse(
        content=json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig))
    )


@router.get("/eval-decision-breakdown")
async def eval_decision_breakdown_chart(
    days: int = Query(7, ge=1, le=90, description="Number of days to look back")
):
    """Pie chart showing distribution of eval decisions (send/draft/escalate).

    Helps visualize how often AI auto-sends vs. requires review.
    """
    data = await asyncio.to_thread(get_daily_trends, days)

    if not data:
        fig = go.Figure()
        fig.update_layout(
            title=f"No data for last {days} days",
            template="plotly_white",
        )
    else:
        # Aggregate totals across all days
        total_sent = sum(row["auto_sent"] for row in data)
        total_drafted = sum(row["drafted"] for row in data)
        total_escalated = sum(row["escalated"] for row in data)

        labels = ["Auto-sent", "Drafted", "Escalated"]
        values = [total_sent, total_drafted, total_escalated]
        colors = ["#90EE90", "#FFD700", "#FF6B6B"]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    marker=dict(colors=colors),
                    textinfo="label+percent",
                    hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>",
                )
            ]
        )
        fig.update_layout(
            title=f"Eval Decision Distribution (Last {days} Days)",
            template="plotly_white",
        )

    return JSONResponse(
        content=json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig))
    )
