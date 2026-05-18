"""
拓扑数据解析模块 - 解析traceroute输出和设备配置文件为拓扑数据。

功能：
    - 解析traceroute文本输出，提取路径上的节点和链路
    - 解析简单设备配置文件（如路由器、交换机配置）
    - 输出标准化的拓扑节点和边列表
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class TopologyNode:
    """拓扑节点。"""
    id: str
    label: str = ""
    node_type: str = "unknown"  # router, switch, server, pc, unknown
    ip: str = ""
    metadata: Dict = field(default_factory=dict)


@dataclass
class TopologyEdge:
    """拓扑边（链路）。"""
    source: str
    target: str
    bandwidth: str = ""
    latency: float = 0.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class TopologyData:
    """解析后的拓扑数据，包含节点和边列表。"""
    nodes: List[TopologyNode] = field(default_factory=list)
    edges: List[TopologyEdge] = field(default_factory=list)
    source: str = ""  # 数据来源描述

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "nodes": [
                {
                    "id": n.id, "label": n.label,
                    "type": n.node_type, "ip": n.ip,
                    **n.metadata,
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "source": e.source, "target": e.target,
                    "bandwidth": e.bandwidth, "latency": e.latency,
                    **e.metadata,
                }
                for e in self.edges
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def _classify_device(ip: str, hostname: str = "") -> str:
    """根据IP和主机名推测设备类型。"""
    hostname_lower = hostname.lower()
    if any(kw in hostname_lower for kw in ("router", "gw", "gateway", "rt")):
        return "router"
    if any(kw in hostname_lower for kw in ("switch", "sw")):
        return "switch"
    if any(kw in hostname_lower for kw in ("server", "srv", "web", "db")):
        return "server"
    if any(kw in hostname_lower for kw in ("fw", "firewall", "asa")):
        return "firewall"
    return "pc"


def parse_traceroute(text: str, source_label: str = "本机") -> TopologyData:
    """
    解析traceroute/tracert命令的文本输出。

    支持Linux traceroute和Windows tracert的常见输出格式。
    将每一跳解析为一个节点，相邻跳之间建立边。

    参数:
        text: traceroute命令的完整文本输出
        source_label: 源节点标签

    返回:
        TopologyData: 解析得到的拓扑数据
    """
    topology = TopologyData(source="traceroute")
    prev_id = source_label
    prev_ip = ""

    # 添加源节点
    topology.nodes.append(TopologyNode(
        id=source_label, label=source_label, node_type="pc"
    ))

    # 匹配各种traceroute输出格式
    # Linux格式: " 1  gateway (192.168.1.1)  1.234 ms"
    # Windows格式: "  1    <1 ms    <1 ms    <1 ms  192.168.1.1"
    hop_pattern = re.compile(
        r"^\s*(\d+)\s+"  # 跳数
        r"(?:"
        r"(?:(\S+)\s+\((\d+\.\d+\.\d+\.\d+)\))"  # hostname (ip)
        r"|"
        r"(?:[\d<.]+\s*m?s\s+){1,3}\s*(\d+\.\d+\.\d+\.\d+)"  # 延迟 + ip
        r"|"
        r"(?:[\d<.]+\s*m?s\s+){1,3}\s*(\S+)"  # 延迟 + hostname
        r"|"
        r"(\*)"  # 超时
        r")",
        re.MULTILINE,
    )

    for match in hop_pattern.finditer(text):
        hostname = match.group(2) or ""
        ip = match.group(3) or match.group(4) or match.group(5) or ""
        is_timeout = match.group(6) is not None

        if is_timeout:
            hop_num = match.group(1)
            node_id = f"未知_{hop_num}"
            topology.nodes.append(TopologyNode(
                id=node_id, label=f"未知(跳{hop_num})", node_type="unknown"
            ))
            topology.edges.append(TopologyEdge(source=prev_id, target=node_id))
            prev_id = node_id
            continue

        if not ip and hostname:
            ip = hostname
            hostname = ""

        node_id = hostname if hostname else ip
        device_type = _classify_device(ip, hostname)

        # 避免重复节点
        if not any(n.id == node_id for n in topology.nodes):
            topology.nodes.append(TopologyNode(
                id=node_id, label=node_id,
                node_type=device_type, ip=ip,
            ))

        if node_id != prev_id:
            topology.edges.append(TopologyEdge(source=prev_id, target=node_id))
        prev_id = node_id

    return topology


def parse_device_config(config_text: str) -> TopologyData:
    """
    解析简单的设备配置文件，提取接口和邻居信息。

    支持的配置格式（每行一条配置）：
        hostname <名称>
        interface <接口名> ip <IP地址>
        neighbor <邻居IP或名称> via <接口名> bandwidth <带宽>

    参数:
        config_text: 设备配置文本

    返回:
        TopologyData: 解析得到的拓扑数据
    """
    topology = TopologyData(source="device_config")
    current_hostname = ""
    current_ip = ""
    interfaces: Dict[str, str] = {}  # 接口名 -> IP

    for line in config_text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue

        # 解析hostname
        m = re.match(r"hostname\s+(\S+)", line, re.IGNORECASE)
        if m:
            current_hostname = m.group(1)
            continue

        # 解析接口
        m = re.match(r"interface\s+(\S+)\s+ip\s+(\S+)", line, re.IGNORECASE)
        if m:
            iface, ip = m.group(1), m.group(2)
            interfaces[iface] = ip
            current_ip = ip
            continue

        # 解析邻居
        m = re.match(
            r"neighbor\s+(\S+)\s+via\s+(\S+)(?:\s+bandwidth\s+(\S+))?",
            line, re.IGNORECASE,
        )
        if m:
            neighbor, via, bw = m.group(1), m.group(2), m.group(3) or ""
            # 确保当前设备节点存在
            if current_hostname:
                node_id = current_hostname
                if not any(n.id == node_id for n in topology.nodes):
                    topology.nodes.append(TopologyNode(
                        id=node_id, label=node_id,
                        node_type=_classify_device(current_ip, current_hostname),
                        ip=current_ip,
                    ))
                # 添加邻居节点
                if not any(n.id == neighbor for n in topology.nodes):
                    topology.nodes.append(TopologyNode(
                        id=neighbor, label=neighbor,
                        node_type=_classify_device(neighbor),
                    ))
                # 添加边
                topology.edges.append(TopologyEdge(
                    source=node_id, target=neighbor, bandwidth=bw,
                ))

    return topology


def load_topology_json(filepath: str) -> TopologyData:
    """
    从JSON文件加载拓扑数据。

    JSON格式:
        {
            "nodes": [{"id": "...", "label": "...", "type": "...", "ip": "..."}],
            "edges": [{"source": "...", "target": "...", "bandwidth": "..."}]
        }

    参数:
        filepath: JSON文件路径

    返回:
        TopologyData: 加载的拓扑数据
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    topology = TopologyData(source=filepath)
    for n in data.get("nodes", []):
        topology.nodes.append(TopologyNode(
            id=n["id"],
            label=n.get("label", n["id"]),
            node_type=n.get("type", "unknown"),
            ip=n.get("ip", ""),
        ))
    for e in data.get("edges", []):
        topology.edges.append(TopologyEdge(
            source=e["source"],
            target=e["target"],
            bandwidth=e.get("bandwidth", ""),
            latency=e.get("latency", 0.0),
        ))
    return topology
