# SSE to WebSocket Proxy

将 SSE 协议的后端服务转换为 WebSocket 协议对外暴露。

## 安装依赖

```bash
pip install aiohttp
```

## 使用方法

```bash
python sse_to_ws_proxy.py --sse-url http://your-sse-service.com/api/endpoint
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--sse-url` | 后端 SSE 服务的 URL（必填） | - |
| `--host` | WebSocket 服务监听地址 | `0.0.0.0` |
| `--port` | WebSocket 服务监听端口 | `8765` |

### 示例

```bash
# 基本用法
python sse_to_ws_proxy.py --sse-url http://localhost:8080/api/sse

# 指定端口
python sse_to_ws_proxy.py --sse-url http://localhost:8080/api/sse --port 9000

# 指定监听地址和端口
python sse_to_ws_proxy.py --sse-url http://localhost:8080/api/sse --host 127.0.0.1 --port 9000
```

## 客户端连接示例

### JavaScript

```javascript
const ws = new WebSocket('ws://localhost:8765/ws');

ws.onopen = () => {
    // 发送请求
    ws.send(JSON.stringify({
        sn: "5cd5e490-9d85-47b5-9975-eca1e76ba392",
        query: "大模型",
        // ... 其他字段
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('收到响应:', data);
};

ws.onerror = (error) => {
    console.error('WebSocket 错误:', error);
};

ws.onclose = () => {
    console.log('连接已关闭');
};
```

### Python

```python
import asyncio
import websockets
import json

async def main():
    async with websockets.connect('ws://localhost:8765/ws') as ws:
        # 发送请求
        await ws.send(json.dumps({
            "sn": "5cd5e490-9d85-47b5-9975-eca1e76ba392",
            "query": "大模型",
            # ... 其他字段
        }))

        # 接收响应
        async for message in ws:
            data = json.loads(message)
            print('收到响应:', data)

asyncio.run(main())
```

## 工作原理

1. WebSocket 客户端连接到代理服务 (`ws://host:port/ws`)
2. 客户端通过 WebSocket 发送 JSON 请求
3. 代理将请求透传到后端 SSE 服务
4. SSE 响应的每个事件被解析后通过 WebSocket 发送回客户端
