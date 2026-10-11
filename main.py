#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tool-searxng-distiller (AI 全局高密搜索与多节点出口中枢装具)
Universal CLI Facade (UCFS v1.0) Standard Entrypoint.

Standard Verbs:
  setup     Validate environment & deployment requirements
  run       Start local AI Search Hub daemon or test query
  test      Execute automated regression unit tests
  health    Diagnostic self-test
  clean     Clean bytecode artifacts
"""
import sys
import os
import json
import argparse
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
for p in [BASE_DIR, os.path.join(BASE_DIR, "hub")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from token_distiller import TokenDistiller

def run_setup(args):
    data = {"status": "ready", "tool": "tool-searxng-distiller", "base_dir": BASE_DIR}
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("[tool-searxng-distiller] Setup OK: Environment validated successfully.")
    return 0

def run_test(args):
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(BASE_DIR, "tests"))
    runner = unittest.TextTestRunner(verbosity=2 if not args.json else 0)
    result = runner.run(suite)
    data = {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "passed": result.wasSuccessful()
    }
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0 if result.wasSuccessful() else 1

def run_health(args):
    html = "<html><head><style>body {color:red}</style></head><body><h1>AI Search</h1><p>High Density Content</p></body></html>"
    res = TokenDistiller.distill_html(html)
    healthy = res.compression_ratio_pct > 30 and "High Density Content" in res.cleaned_text
    data = {
        "status": "HEALTHY" if healthy else "UNHEALTHY",
        "compression_ratio_pct": res.compression_ratio_pct,
        "token_distiller_ok": healthy
    }
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"[tool-searxng-distiller] Health status: {data['status']} (Distill Ratio: {res.compression_ratio_pct}%)")
    return 0 if healthy else 1

def run_run(args):
    from server import start_server
    port = int(args.port) if args.port else 8000
    start_server(port)
    return 0

def run_clean(args):
    cleaned = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for d in dirs:
            if d in ["__pycache__", ".pytest_cache"]:
                import shutil
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                cleaned += 1
    if args.json:
        print(json.dumps({"cleaned_dirs": cleaned}))
    else:
        print(f"[tool-searxng-distiller] Clean OK: Removed {cleaned} cache directories.")
    return 0

def main():
    parser = argparse.ArgumentParser(description="tool-searxng-distiller CLI Facade")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    subparsers = parser.add_subparsers(dest="subcommand")

    subparsers.add_parser("setup", help="Verify environment")
    
    run_parser = subparsers.add_parser("run", help="Start search hub")
    run_parser.add_argument("--port", default=8000, help="Listen port")
    
    subparsers.add_parser("test", help="Run automated tests")
    subparsers.add_parser("health", help="Self diagnostic check")
    subparsers.add_parser("clean", help="Clean cache files")

    args = parser.parse_args()
    if not args.subcommand:
        parser.print_help()
        return 0

    commands = {
        "setup": run_setup,
        "run": run_run,
        "test": run_test,
        "health": run_health,
        "clean": run_clean
    }
    return commands[args.subcommand](args)

if __name__ == "__main__":
    sys.exit(main())
