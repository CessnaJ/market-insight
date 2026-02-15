"""WebSocket Routes for Real-time Updates"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Set
import asyncio
import json
from datetime import datetime

router = APIRouter()


class ConnectionManager:
    """WebSocket connection manager for broadcasting updates"""

    def __init__(self):
        # Active WebSocket connections
        self.active_connections: List[WebSocket] = []
        # Client subscriptions
        self.subscriptions: Dict[WebSocket, Set[str]] = {}

    async def connect(self, websocket: WebSocket, channels: List[str] = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = set(channels or ["portfolio", "thoughts", "reports"])

        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Market Insight WebSocket",
            "channels": list(self.subscriptions[websocket]),
            "timestamp": datetime.now().isoformat()
        })

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]

    async def broadcast(self, message: dict, channel: str = None):
        """Broadcast a message to all connected clients"""
        if channel:
            # Only send to clients subscribed to this channel
            disconnected = []
            for connection in self.subscriptions:
                if channel in self.subscriptions[connection]:
                    try:
                        await connection.send_json(message)
                    except Exception:
                        disconnected.append(connection)
            # Clean up disconnected clients
            for conn in disconnected:
                self.disconnect(conn)
        else:
            # Send to all connected clients
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            # Clean up disconnected clients
            for conn in disconnected:
                self.disconnect(conn)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific client"""
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates

    Client can subscribe to specific channels:
    - portfolio: Portfolio updates
    - thoughts: New thoughts
    - reports: New reports
    - alerts: Price alerts and notifications

    Example message format from client:
    {
        "type": "subscribe",
        "channels": ["portfolio", "thoughts"]
    }

    Example message format from server:
    {
        "type": "portfolio_update",
        "data": {...},
        "timestamp": "2024-01-01T00:00:00"
    }
    """
    # Default channels
    channels = ["portfolio", "thoughts", "reports"]

    # Wait for initial message from client
    try:
        initial_message = await websocket.receive_json()
        if initial_message.get("type") == "subscribe":
            channels = initial_message.get("channels", channels)
    except Exception:
        pass

    await manager.connect(websocket, channels)

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()

            # Handle client messages
            message_type = data.get("type")

            if message_type == "subscribe":
                # Update subscriptions
                new_channels = data.get("channels", [])
                manager.subscriptions[websocket] = set(new_channels)
                await websocket.send_json({
                    "type": "subscribed",
                    "channels": new_channels,
                    "timestamp": datetime.now().isoformat()
                })

            elif message_type == "ping":
                # Respond to ping with pong
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })

            elif message_type == "get_portfolio":
                # Request current portfolio data
                from storage.db import get_portfolio_summary
                from sqlmodel import Session
                from storage.db import engine

                with Session(engine) as session:
                    portfolio = get_portfolio_summary(session)
                    await websocket.send_json({
                        "type": "portfolio_data",
                        "data": portfolio,
                        "timestamp": datetime.now().isoformat()
                    })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ──── Helper Functions for Broadcasting ────

async def broadcast_portfolio_update(portfolio_data: dict):
    """Broadcast portfolio update to subscribed clients"""
    await manager.broadcast({
        "type": "portfolio_update",
        "data": portfolio_data,
        "timestamp": datetime.now().isoformat()
    }, channel="portfolio")


async def broadcast_new_thought(thought_data: dict):
    """Broadcast new thought to subscribed clients"""
    await manager.broadcast({
        "type": "new_thought",
        "data": thought_data,
        "timestamp": datetime.now().isoformat()
    }, channel="thoughts")


async def broadcast_new_report(report_data: dict):
    """Broadcast new report to subscribed clients"""
    await manager.broadcast({
        "type": "new_report",
        "data": report_data,
        "timestamp": datetime.now().isoformat()
    }, channel="reports")


async def broadcast_alert(alert_data: dict):
    """Broadcast alert to subscribed clients"""
    await manager.broadcast({
        "type": "alert",
        "data": alert_data,
        "timestamp": datetime.now().isoformat()
    }, channel="alerts")


async def broadcast_price_update(ticker: str, price_data: dict):
    """Broadcast price update to subscribed clients"""
    await manager.broadcast({
        "type": "price_update",
        "ticker": ticker,
        "data": price_data,
        "timestamp": datetime.now().isoformat()
    }, channel="portfolio")


# ──── API Endpoints for Manual Broadcasting ────

@router.post("/broadcast/portfolio")
async def trigger_portfolio_broadcast():
    """Manually trigger portfolio broadcast (for testing)"""
    from storage.db import get_portfolio_summary
    from sqlmodel import Session
    from storage.db import engine

    with Session(engine) as session:
        portfolio = get_portfolio_summary(session)
        await broadcast_portfolio_update(portfolio)
        return {"status": "ok", "message": "Portfolio update broadcasted"}


@router.get("/connections")
async def get_active_connections():
    """Get number of active WebSocket connections"""
    return {
        "active_connections": len(manager.active_connections),
        "subscriptions": {
            "portfolio": sum(1 for subs in manager.subscriptions.values() if "portfolio" in subs),
            "thoughts": sum(1 for subs in manager.subscriptions.values() if "thoughts" in subs),
            "reports": sum(1 for subs in manager.subscriptions.values() if "reports" in subs),
            "alerts": sum(1 for subs in manager.subscriptions.values() if "alerts" in subs),
        }
    }
