#!/usr/bin/env python3
"""
NetVisual CLI - 网络拓扑可视化命令行工具。

用法:
    python cli.py scan --subnet 192.168.1.0/24
    python cli.py render --input topology.json --output topology.png
    python cli.py analyze --input topology.json
    python cli.py web --port 5000
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 确保可以导入netvisual包
sys.path.insert(0, str(Path(__file__).resolve().parent))

from netvisual.parser import load_topology_json
from netvisual.topology import TopologyGraph


def cmd_scan(args: argparse.Namespace) -> None:
    """执行网络扫描。"""
    from netvisual.scanner import scan

    print(f"[*] 扫描子网: {args.subnet} (方法: {args.method})")
    result = scan(args.subnet, method=args.method, timeout=args.timeout)
    print(f"[+] 发现 {result.host_count} 台主机:")
    for host in result.hosts:
        hostname = host.hostname if host.hostname else "未知"
        print(f"    {host.ip:<16} MAC: {host.mac or 'N/A':<18} 主机名: {hostname}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"[+] 扫描结果已保存到: {args.output}")


def cmd_render(args: argparse.Namespace) -> None:
    """渲染拓扑图为图片。"""
    from netvisual.renderer import render_topology

    print(f"[*] 加载拓扑: {args.input}")
    topology = TopologyGraph.from_json(args.input)
    print(f"[*] 渲染中... (节点: {topology.node_count}, 边: {topology.edge_count})")
    output = render_topology(
        topology,
        output_path=args.output,
        title=args.title,
        dpi=args.dpi,
        layout=args.layout,
    )
    print(f"[+] 拓扑图已保存到: {output}")


def cmd_analyze(args: argparse.Namespace) -> None:
    """分析拓扑统计信息。"""
    print(f"[*] 加载拓扑: {args.input}")
    topology = TopologyGraph.from_json(args.input)
    stats = topology.get_stats()

    print("=" * 50)
    print("        网络拓扑分析报告")
    print("=" * 50)
    for key, value in stats.items():
        print(f"  {key:<20} : {value}")

    # 显示割点
    ap = topology.find_articulation_points()
    if ap:
        print(f"\n[!] 关键节点（割点）:")
        for node in ap:
            attrs = topology.graph.nodes[node]
            print(f"    - {node} ({attrs.get('label', '')})")

    # 显示桥边
    bridges = topology.get_critical_links()
    if bridges:
        print(f"\n[!] 关键链路（桥边）:")
        for u, v in bridges:
            print(f"    - {u} <-> {v}")

    # 显示设备类型分布
    types = topology.get_node_types()
    print(f"\n[*] 设备类型分布:")
    for dev_type, nodes in types.items():
        print(f"    {dev_type:<12}: {len(nodes)} 台")

    print("=" * 50)


def cmd_web(args: argparse.Namespace) -> None:
    """启动Web可视化服务。"""
    from web.app import run_server
    print(f"[*] 启动Web服务: http://0.0.0.0:{args.port}")
    run_server(host=args.host, port=args.port, debug=args.debug)


def main() -> None:
    """CLI主入口。"""
    parser = argparse.ArgumentParser(
        description="NetVisual - 网络拓扑可视化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # scan 子命令
    p_scan = subparsers.add_parser("scan", help="扫描网络发现主机")
    p_scan.add_argument("--subnet", "-s", required=True, help="目标子网 (例: 192.168.1.0/24)")
    p_scan.add_argument("--method", "-m", default="arp", choices=["arp", "icmp"],
                        help="扫描方法 (默认: arp)")
    p_scan.add_argument("--timeout", "-t", type=float, default=2.0, help="超时时间(秒)")
    p_scan.add_argument("--output", "-o", help="保存结果到JSON文件")
    p_scan.set_defaults(func=cmd_scan)

    # render 子命令
    p_render = subparsers.add_parser("render", help="渲染拓扑图为图片")
    p_render.add_argument("--input", "-i", required=True, help="拓扑JSON文件路径")
    p_render.add_argument("--output", "-o", default="topology.png", help="输出图片路径")
    p_render.add_argument("--title", default="网络拓扑图", help="图表标题")
    p_render.add_argument("--dpi", type=int, default=150, help="图片DPI")
    p_render.add_argument("--layout", default="spring",
                          choices=["spring", "kamada_kawai", "shell", "spectral"],
                          help="布局算法")
    p_render.set_defaults(func=cmd_render)

    # analyze 子命令
    p_analyze = subparsers.add_parser("analyze", help="分析拓扑统计信息")
    p_analyze.add_argument("--input", "-i", required=True, help="拓扑JSON文件路径")
    p_analyze.set_defaults(func=cmd_analyze)

    # web 子命令
    p_web = subparsers.add_parser("web", help="启动Web可视化服务")
    p_web.add_argument("--host", default="0.0.0.0", help="监听地址")
    p_web.add_argument("--port", "-p", type=int, default=5000, help="监听端口")
    p_web.add_argument("--debug", action="store_true", help="调试模式")
    p_web.set_defaults(func=cmd_web)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
