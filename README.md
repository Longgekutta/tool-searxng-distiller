# tool-searxng-distiller (AI 全局高密搜索与多节点出口中枢装具)
### 基于第一性原理的 SearXNG 聚合检索、Tavily 工业协议适配与 TokenDistiller 极速脱水架构
**Universal CLI Facade (UCFS v1.0) Compatible AI Search Hub Infrastructure**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Tavily Compatible](https://img.shields.io/badge/API-Tavily%20100%25%20Compatible-success.svg)](#-ai-编辑器一键对接指南)
[![Tests Passing](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)](#-快速开始与-cli-指令)

---

## 🌟 核心定位与设计哲学

在现代 AI 辅助研发（如 Cursor、Windsurf、VSCode Continue 及各类 Agentic 深度调研智能体）中，开发者普遍面临三大痛点：
1. **商业搜索 API 昂贵且受限**：Tavily / Perplexity 等商业搜索服务单次检索成本昂贵且存在严格调用配额；
2. **原始网页 Token 爆炸与污染**：传统搜索引擎返回的 HTML 充斥大量的导航、CSS、Cookie 弹窗与广告脚本，白白浪费 80%~90% 的上下文窗口（Context Window），导致大模型遭遇“迷失在中间 (Lost-in-the-Middle)”；
3. **低配海外小鸡容易 OOM 崩溃**：低成本海外节点（如 128MB 内存 NAT VPS）资源极度贫瘠，强行运行重型 Docker/SearXNG 会瞬间触发 Linux OOM-Killer 强退。

**`tool-searxng-distiller`** 秉承**第一性原理**提出**“全局最优双机拓扑”**：
- **国内计算中枢节点**：承载 SearXNG 内核、Tavily 兼容网关与 `TokenDistiller` 噪声脱水，享受国内低延迟（10~20ms）与充足内存算力；
- **海外轻量代理出口**：仅运行安全加密动态 SSH SOCKS5 隧道（内存常驻仅 **2.2MB**），提供纯净海外 IP 顺畅访问 Google/DuckDuckGo/Bing，永不 OOM；
- **智能轮询与平摊**：内置引擎分组轮询（不逮着单个引擎薅羊毛）、公共 SearXNG 实例兜底池与限流防封机制。

---

## 🏛️ 全局系统拓扑架构图

```mermaid
flowchart TD
    subgraph Client[开发者本地开发环境]
        AI_Editor["AI 编辑器 (Cursor / Windsurf / VSCode / Claude)"]
    end

    subgraph CN_Hub["国内高性能计算节点 (例如 47.119.117.111)"]
        Hub["AI Search Hub Gateway (:8000)<br>Tavily 标准 API 兼容网关"]
        Distiller["tool-token-distiller<br>Token 噪声极速蒸馏 (剥离 85%+ 噪声)"]
        SearXNG["SearXNG 搜索引擎内核 (:8080)<br>Docker 容器化运行"]
        TunnelClient["SSH Dynamic SOCKS5 Client (:1080)<br>常驻系统服务 (内存仅占 2.2MB)"]
    end

    subgraph Overseas_Egress["海外纯净出口节点 (例如 45.153.246.167)"]
        TunnelServer["SSH SOCKS5 Egress Tunnel<br>NAT 穿透出口 (零内存负载，稳定无 OOM)"]
        Engines["Google / Bing / DuckDuckGo / GitHub / Wikidata"]
    end

    AI_Editor -->|1. Tavily 协议请求 (极低延迟 20ms)| Hub
    Hub -->|2. 调度搜索| SearXNG
    SearXNG -->|3. 出口流量路由| TunnelClient
    TunnelClient -->|4. 加密传输| TunnelServer
    TunnelServer -->|5. 检索公共引擎| Engines
    Engines -->|6. 原始搜索结果与网页| TunnelServer
    TunnelServer --> TunnelClient
    TunnelClient --> SearXNG
    SearXNG -->|7. 原始富文本与 HTML| Hub
    Hub <-->|8. 正文纯化与关键信息提取| Distiller
    Hub -->|9. 高密度 AI 友好 Markdown/JSON| AI_Editor
```

---

## 🚀 快速开始与 CLI 指令 (UCFS 规范)

本项目遵循 **Universal CLI Facade Standard (UCFS v1.0)**，标准动词开箱即用：

```bash
# 1. 验证运行环境
python main.py setup

# 2. 执行自动化单元测试
python main.py test

# 3. 运行健康检查自检
python main.py health

# 4. 本地启动网关服务 (默认端口 8000)
python main.py run --port 8000

# 5. 清理缓存字节码
python main.py clean
```

---

## 💻 AI 编辑器一键对接指南 (Tavily 兼容)

### 1. Cursor 配置
- 打开 **Cursor Settings** -> **Features** -> **Web Search**：
- **Tavily API Key**: 任意填写（如 `sk-local-hub`）
- **Tavily Base URL**: `http://<你的国内服务器IP>:8000`

### 2. Windsurf (Codeium) 配置
- 打开 **Settings** -> **Web Search Tools**：
- **API URL**: `http://<你的国内服务器IP>:8000/v1`
- **API Key**: 留空或任意字符串

### 3. VSCode Continue 插件
在 `~/.continue/config.json` 中添加：
```json
{
  "tools": [
    {
      "name": "web_search",
      "description": "Searches the web via tool-searxng-distiller hub",
      "apiBase": "http://<你的国内服务器IP>:8000",
      "apiKey": "sk-local"
    }
  ]
}
```

---

## 🛠️ 灵活扩展与未来薅羊毛指南

项目在 `hub/config.json` 预留了完全解耦的配置拓展接口：

### 1. 扩充更多海外代理小鸡 (免费/低价节点池)
只需在 `proxy_pool.proxies` 数组中追加节点即可：
```json
{
  "proxy_pool": {
    "enabled": true,
    "strategy": "round_robin",
    "proxies": [
      {"id": "node-nat-01", "url": "socks5h://127.0.0.1:1080", "weight": 10},
      {"id": "node-oracle-free", "url": "socks5h://x.x.x.x:1080", "weight": 10}
    ]
  }
}
```

### 2. 避免单引擎被封 (引擎轮询组)
```json
{
  "engine_pool": {
    "rotation_enabled": true,
    "engine_groups": {
      "group_a": ["duckduckgo", "brave"],
      "group_b": ["google", "bing"],
      "group_c": ["qwant", "startpage", "wikidata", "github"]
    }
  }
}
```

### 3. 公共 SearXNG 实例兜底池 (零成本安全网)
当本地检索遇到验证码或空结果时，自动无缝切换到公共节点：
```json
{
  "public_instances_fallback": {
    "enabled": true,
    "public_nodes": [
      "https://searx.be",
      "https://searx.tiekoetter.com",
      "https://search.ononoki.org"
    ]
  }
}
```

---

## 📜 许可证

本项目基于 [MIT 许可证](LICENSE) 开源。
