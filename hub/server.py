#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Search Hub: SearXNG + Searcharvester + TokenDistiller Gateway
Tavily-compatible API gateway with multi-engine rotation and noise distillation.
"""
import os
import sys
import json
import time
import uuid
import random
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from token_distiller import TokenDistiller

CONFIG_PATH = os.environ.get("CONFIG_PATH", os.path.join(BASE_DIR, "config.json"))
SEARXNG_LOCAL_URL = os.environ.get("SEARXNG_URL", "http://127.0.0.1:8080")
PORT = int(os.environ.get("PORT", "8000"))

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {}

class EngineRotator:
    def __init__(self, config):
        self.config = config.get("engine_pool", {})
        self.groups = self.config.get("engine_groups", {
            "default": ["duckduckgo", "google", "brave", "bing"]
        })
        self.group_keys = list(self.groups.keys())
        self.current_idx = 0

    def get_engines_for_query(self):
        if not self.config.get("rotation_enabled", True) or not self.group_keys:
            return "duckduckgo,google,brave"
        self.current_idx = (self.current_idx + 1) % len(self.group_keys)
        chosen_group = self.groups[self.group_keys[self.current_idx]]
        return ",".join(chosen_group)

class PublicFallbackManager:
    def __init__(self, config):
        self.cfg = config.get("public_instances_fallback", {})
        self.nodes = self.cfg.get("public_nodes", [])

    def fetch_fallback(self, query, max_results=5):
        if not self.cfg.get("enabled", False) or not self.nodes:
            return []
        shuffled = list(self.nodes)
        random.shuffle(shuffled)
        for node in shuffled[:2]:
            try:
                url = f"{node.rstrip('/')}/search?q={urllib.parse.quote(query)}&format=json"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    results = data.get("results", [])
                    if results:
                        return results[:max_results]
            except Exception:
                continue
        return []

class RateLimiter:
    def __init__(self, config):
        self.cfg = config.get("rate_limiting", {})
        self.max_rpm = self.cfg.get("max_requests_per_minute", 60)
        self.requests = []

    def allow_request(self):
        if not self.cfg.get("enabled", True):
            return True
        now = time.time()
        self.requests = [t for t in self.requests if now - t < 60]
        if len(self.requests) >= self.max_rpm:
            return False
        self.requests.append(now)
        return True

CONFIG = load_config()
engine_rotator = EngineRotator(CONFIG)
fallback_mgr = PublicFallbackManager(CONFIG)
rate_limiter = RateLimiter(CONFIG)

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class TavilyHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path in ["/health", "/"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_cors_headers()
            self.end_headers()
            cfg = load_config()
            health_data = {
                "status": "healthy",
                "version": "2.0.0-extensible",
                "features": {
                    "token_compression": True,
                    "engine_rotation": cfg.get("engine_pool", {}).get("rotation_enabled", True),
                    "proxy_pool_extensible": True,
                    "proxy_count": len(cfg.get("proxy_pool", {}).get("proxies", [])),
                    "public_fallback_nodes": len(cfg.get("public_instances_fallback", {}).get("public_nodes", [])),
                    "rate_limiting": cfg.get("rate_limiting", {}).get("enabled", True)
                }
            }
            self.wfile.write(json.dumps(health_data, ensure_ascii=False, indent=2).encode("utf-8"))
        elif self.path == "/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(load_config(), ensure_ascii=False, indent=2).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path in ["/search", "/v1/search", "/api/search"]:
            self._handle_search()
        elif self.path in ["/extract", "/v1/extract", "/api/extract"]:
            self._handle_extract()
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_search(self):
        if not rate_limiter.allow_request():
            self.send_response(429)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Rate limit exceeded"}).encode("utf-8"))
            return

        start_time = time.time()
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            req_data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            req_data = {}

        query = req_data.get("query", "")
        max_results = int(req_data.get("max_results", 5))
        include_raw = bool(req_data.get("include_raw_content", False))
        
        if not query:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing query parameter"}).encode("utf-8"))
            return

        selected_engines = engine_rotator.get_engines_for_query()
        params = {
            "q": query,
            "format": "json",
            "categories": "general",
            "engines": selected_engines
        }
        searx_url = f"{SEARXNG_LOCAL_URL}/search?" + urllib.parse.urlencode(params)
        
        raw_items = []
        try:
            req = urllib.request.Request(searx_url, headers={"User-Agent": "Mozilla/5.0 (AI-Agent-Hub)"})
            with urllib.request.urlopen(req, timeout=10) as response:
                searx_res = json.loads(response.read().decode("utf-8"))
                raw_items = searx_res.get("results", [])
        except Exception:
            pass

        if not raw_items:
            raw_items = fallback_mgr.fetch_fallback(query, max_results)

        results = []
        for item in raw_items[:max_results]:
            title = item.get("title", "")
            url = item.get("url", "")
            raw_snippet = item.get("content", "")
            
            distilled_snippet = TokenDistiller.distill_html(raw_snippet)
            res_entry = {
                "title": title,
                "url": url,
                "content": distilled_snippet.cleaned_text,
                "score": round(float(item.get("score", 0.9)), 2),
                "distill_metrics": {
                    "raw_bytes": distilled_snippet.raw_bytes,
                    "cleaned_bytes": distilled_snippet.cleaned_bytes,
                    "compression_ratio_pct": distilled_snippet.compression_ratio_pct
                }
            }
            if include_raw and url:
                try:
                    fetch_req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(fetch_req, timeout=5) as p_resp:
                        raw_html = p_resp.read().decode("utf-8", errors="ignore")
                        full_distilled = TokenDistiller.distill_html(raw_html)
                        res_entry["raw_content"] = full_distilled.cleaned_text[:4000]
                except Exception:
                    res_entry["raw_content"] = res_entry["content"]
            results.append(res_entry)

        elapsed = round(time.time() - start_time, 3)
        tavily_response = {
            "query": query,
            "engines_used": selected_engines,
            "results": results,
            "response_time": elapsed,
            "request_id": str(uuid.uuid4())
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(tavily_response, ensure_ascii=False, indent=2).encode("utf-8"))

    def _handle_extract(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            req_data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            req_data = {}
        urls = req_data.get("urls", [])
        if isinstance(urls, str):
            urls = [urls]
        results = []
        for u in urls[:5]:
            try:
                fetch_req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(fetch_req, timeout=6) as p_resp:
                    raw_html = p_resp.read().decode("utf-8", errors="ignore")
                    distilled = TokenDistiller.distill_html(raw_html)
                    results.append({
                        "url": u,
                        "raw_content": distilled.cleaned_text,
                        "compression_ratio_pct": distilled.compression_ratio_pct
                    })
            except Exception as e:
                results.append({"url": u, "error": str(e)})

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({"results": results}, ensure_ascii=False).encode("utf-8"))

def start_server(port=PORT):
    server = ThreadingHTTPServer(("0.0.0.0", port), TavilyHandler)
    print(f"[tool-searxng-distiller] Server running on 0.0.0.0:{port}")
    server.serve_forever()

if __name__ == "__main__":
    start_server()
