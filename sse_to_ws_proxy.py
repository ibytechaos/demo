#!/usr/bin/env python3
"""
SSE to WebSocket Protocol Converter
将 SSE 协议的后端服务转换为 WebSocket 协议对外暴露
"""

import asyncio
import json
import aiohttp
from aiohttp import web
import argparse


class SSEToWebSocketProxy:
    def __init__(self, sse_url: str):
        """
        初始化代理
        :param sse_url: 后端 SSE 服务的 URL
        """
        self.sse_url = sse_url

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """处理 WebSocket 连接"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        print(f"[WS] 新连接建立: {request.remote}")

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    # 收到 WebSocket 客户端的消息，转发到 SSE 服务
                    await self._forward_to_sse(ws, msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f"[WS] 连接错误: {ws.exception()}")
        except Exception as e:
            print(f"[WS] 处理异常: {e}")
        finally:
            print(f"[WS] 连接关闭: {request.remote}")

        return ws

    async def _forward_to_sse(self, ws: web.WebSocketResponse, data: str):
        """
        将请求转发到 SSE 服务，并将 SSE 响应转发回 WebSocket
        """
        try:
            # 尝试解析为 JSON，如果失败则作为原始数据发送
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                payload = data

            print(f"[SSE] 转发请求到: {self.sse_url}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.sse_url,
                    json=payload if isinstance(payload, dict) else None,
                    data=payload if isinstance(payload, str) else None,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                    },
                ) as response:
                    if response.status != 200:
                        error_msg = await response.text()
                        await ws.send_json({
                            "error": True,
                            "status": response.status,
                            "message": error_msg
                        })
                        return

                    # 检查是否是 SSE 响应
                    content_type = response.headers.get("Content-Type", "")

                    if "text/event-stream" in content_type:
                        # 处理 SSE 流式响应
                        await self._handle_sse_stream(ws, response)
                    else:
                        # 普通响应，直接转发
                        body = await response.text()
                        await ws.send_str(body)

        except aiohttp.ClientError as e:
            print(f"[SSE] 请求失败: {e}")
            await ws.send_json({"error": True, "message": str(e)})
        except Exception as e:
            print(f"[SSE] 未知错误: {e}")
            await ws.send_json({"error": True, "message": str(e)})

    async def _handle_sse_stream(self, ws: web.WebSocketResponse, response: aiohttp.ClientResponse):
        """
        处理 SSE 流式响应，将每个事件转发到 WebSocket
        """
        buffer = ""

        async for chunk in response.content.iter_any():
            if ws.closed:
                break

            buffer += chunk.decode("utf-8", errors="ignore")

            # 按照 SSE 协议解析事件（以双换行分隔）
            while "\n\n" in buffer:
                event_str, buffer = buffer.split("\n\n", 1)
                event_data = self._parse_sse_event(event_str)

                if event_data:
                    # 将 SSE 事件转发到 WebSocket
                    await ws.send_json(event_data)

        # 处理剩余的 buffer
        if buffer.strip():
            event_data = self._parse_sse_event(buffer)
            if event_data:
                await ws.send_json(event_data)

    def _parse_sse_event(self, event_str: str) -> dict | None:
        """
        解析 SSE 事件字符串
        SSE 格式:
            event: xxx
            data: xxx
            id: xxx
        """
        if not event_str.strip():
            return None

        event = {}
        data_lines = []

        for line in event_str.split("\n"):
            line = line.strip()
            if not line:
                continue

            if line.startswith("data:"):
                data_lines.append(line[5:].strip())
            elif line.startswith("event:"):
                event["event"] = line[6:].strip()
            elif line.startswith("id:"):
                event["id"] = line[3:].strip()
            elif line.startswith("retry:"):
                event["retry"] = line[6:].strip()
            elif not line.startswith(":"):  # 忽略注释行
                # 可能是没有前缀的数据行
                data_lines.append(line)

        if data_lines:
            data_str = "\n".join(data_lines)
            # 尝试解析为 JSON
            try:
                event["data"] = json.loads(data_str)
            except json.JSONDecodeError:
                event["data"] = data_str

        return event if event else None


def create_app(sse_url: str) -> web.Application:
    """创建 Web 应用"""
    proxy = SSEToWebSocketProxy(sse_url)
    app = web.Application()
    app.router.add_get("/ws", proxy.handle_websocket)
    app.router.add_get("/", proxy.handle_websocket)  # 也支持根路径
    return app


def main():
    parser = argparse.ArgumentParser(description="SSE to WebSocket Protocol Converter")
    parser.add_argument(
        "--sse-url",
        type=str,
        required=True,
        help="后端 SSE 服务的 URL (例如: http://localhost:8080/api/sse)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="WebSocket 服务监听地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="WebSocket 服务监听端口 (默认: 8765)"
    )

    args = parser.parse_args()

    print(f"启动 SSE to WebSocket 代理服务")
    print(f"  - 后端 SSE 服务: {args.sse_url}")
    print(f"  - WebSocket 监听: ws://{args.host}:{args.port}/ws")
    print()

    app = create_app(args.sse_url)
    web.run_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
