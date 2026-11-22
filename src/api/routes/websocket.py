"""
WebSocket 路由
提供实时通信功能
"""
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
from urllib.parse import urlsplit

from src.auth.session_store import SESSION_COOKIE_NAME, get_session_user
from src.infrastructure.config.settings import settings as app_settings


router = APIRouter()

# 全局 WebSocket 连接管理
active_connections: Set[WebSocket] = set()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
):
    """WebSocket 端点"""
    session_token = websocket.cookies.get(SESSION_COOKIE_NAME)
    username = get_session_user(session_token, expected_username=app_settings.web_username)
    if not username:
        await websocket.accept()
        await websocket.close(code=4401)
        return

    origin = websocket.headers.get("origin")
    host = websocket.headers.get("host")
    if origin and host and urlsplit(origin).netloc.lower() != host.lower():
        await websocket.accept()
        await websocket.close(code=4403)
        return

    # 接受连接
    await websocket.accept()
    active_connections.add(websocket)
    session_monitor = asyncio.create_task(_monitor_session(websocket, session_token, username))

    try:
        # 保持连接并接收消息
        while True:
            # 接收客户端消息（如果有的话）
            data = await websocket.receive_text()
            # 这里可以处理客户端发送的消息
            # 目前我们主要用于服务端推送，所以暂时不处理
    except WebSocketDisconnect:
        active_connections.discard(websocket)
    except Exception as e:
        print(f"WebSocket 错误: {e}")
        active_connections.discard(websocket)
    finally:
        session_monitor.cancel()


async def _monitor_session(websocket: WebSocket, session_token: str | None, username: str):
    """Close long-lived sockets when their server-side session expires or is revoked."""
    while True:
        await asyncio.sleep(30)
        if not get_session_user(session_token, expected_username=username):
            try:
                await websocket.close(code=4401)
            except Exception:
                pass
            return


async def broadcast_message(message_type: str, data: dict):
    """向所有连接的客户端广播消息"""
    message = {
        "type": message_type,
        "data": data
    }

    # 移除已断开的连接
    disconnected = set()

    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception:
            disconnected.add(connection)

    # 清理断开的连接
    for connection in disconnected:
        active_connections.discard(connection)
