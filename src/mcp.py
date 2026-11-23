"""Minimal Composio Connect MCP client (streamable HTTP, x-consumer-api-key)."""
import os, json, re, httpx
URL = "https://connect.composio.dev/mcp"
class MCP:
    def __init__(self, key=None):
        self.h = {"x-consumer-api-key": key or os.environ["COMPOSIO_API_KEY"], "content-type": "application/json", "accept": "application/json, text/event-stream"}
        self.c = httpx.Client(timeout=120); self.i = 0
        r = self._post({"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"research-agent","version":"0.1"}}})
        self.sid = r.headers.get("mcp-session-id")
        if self.sid: self.h["mcp-session-id"] = self.sid
        self._post({"jsonrpc":"2.0","method":"notifications/initialized"})
    def _post(self, body): return self.c.post(URL, headers=self.h, json=body)
    def rpc(self, method, params=None):
        self.i += 1
        r = self._post({"jsonrpc":"2.0","id":self.i,"method":method,"params":params or {}})
        m = re.search(r"data: (\{.*\})", r.text) or re.search(r"(\{.*\})", r.text, re.S)
        d = json.loads(m.group(1))
        if "error" in d: raise RuntimeError(d["error"])
        return d["result"]
    def tools(self): return self.rpc("tools/list")["tools"]
    def call(self, name, args): return self.rpc("tools/call", {"name": name, "arguments": args})
