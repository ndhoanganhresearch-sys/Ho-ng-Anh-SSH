# Obsidian MCP Setup

#mcp #obsidian #setup

MCP đã được cấu hình cho dự án này, nhưng Obsidian cần bật community plugin lần đầu bằng tay.

## Bật plugin trong Obsidian

1. Mở vault dự án này trong Obsidian.
2. Vào **Settings**.
3. Vào **Community plugins**.
4. Tắt **Restricted mode** nếu đang bật.
5. Bật plugin **Local REST API with MCP**.
6. Vào setting của plugin và kiểm tra:
   - Non-encrypted HTTP server: enabled
   - HTTP port: `27123`
   - MCP endpoint: `http://127.0.0.1:27123/mcp/`

## Codex MCP

Dự án đã có MCP server `obsidian` trong `.mcp.json`.
Sau khi bật plugin, khởi động lại Codex/CLI để MCP server mới xuất hiện trong tool list.

## Files

- `.obsidian/plugins/obsidian-local-rest-api/`
- `.obsidian/plugins/obsidian-local-rest-api/data.json`
- `.obsidian-mcp.env`
- `tools/start_obsidian_mcp.ps1`
- `.mcp.json`
