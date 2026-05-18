"""
拓扑模型模块 - 基于NetworkX构建和分析网络拓扑图。

功能：
    - 构建网络拓扑图（添加/删除节点和边）
    - 最短路径计算
    - 关键节点发现（割点分析）
    - 节点度数分析
    - 拓扑统计信息
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from .parser import TopologyData, TopologyEdge, TopologyNode


class TopologyGraph:
    """
    网络拓扑图模型，封装NetworkX图的操作。

    属性:
        graph: 底层NetworkX图对象
    """

    def __init__(self) -> None:
        """初始化空的拓扑图。"""
        self.graph: nx.Graph = nx.Graph()

    @classmethod
    def from_topology_data(cls, data: TopologyData) -> "TopologyGraph":
        """
        从TopologyData对象构建拓扑图。

        参数:
            data: 解析后的拓扑数据

        返回:
            TopologyGraph: 构建好的拓扑图实例
        """
        topo = cls()
        for node in data.nodes:
            topo.add_node(
                node.id,
                label=node.label,
                node_type=node.node_type,
                ip=node.ip,
            )
        for edge in data.edges:
            topo.add_edge(
                edge.source,
                edge.target,
                bandwidth=edge.bandwidth,
                latency=edge.latency,
            )
        return topo

    @classmethod
    def from_json(cls, filepath: str) -> "TopologyGraph":
        """从JSON文件加载拓扑图。"""
        from .parser import load_topology_json
        data = load_topology_json(filepath)
        return cls.from_topology_data(data)

    @classmethod
    def from_dict(cls, data: dict) -> "TopologyGraph":
        """从字典构建拓扑图。"""
        topo = cls()
        for n in data.get("nodes", []):
            topo.add_node(n["id"], label=n.get("label", n["id"]),
                          node_type=n.get("type", "unknown"), ip=n.get("ip", ""))
        for e in data.get("edges", []):
            topo.add_edge(e["source"], e["target"],
                          bandwidth=e.get("bandwidth", ""),
                          latency=e.get("latency", 0.0))
        return topo

    def add_node(self, node_id: str, label: str = "",
                 node_type: str = "unknown", ip: str = "", **attrs) -> None:
        """添加节点到拓扑图。"""
        self.graph.add_node(node_id, label=label or node_id,
                            node_type=node_type, ip=ip, **attrs)

    def remove_node(self, node_id: str) -> None:
        """从拓扑图中删除节点。"""
        self.graph.remove_node(node_id)

    def add_edge(self, source: str, target: str,
                 bandwidth: str = "", latency: float = 0.0, **attrs) -> None:
        """添加边（链路）到拓扑图。"""
        self.graph.add_edge(source, target,
                            bandwidth=bandwidth, latency=latency, **attrs)

    def remove_edge(self, source: str, target: str) -> None:
        """从拓扑图中删除边。"""
        self.graph.remove_edge(source, target)

    @property
    def node_count(self) -> int:
        """节点总数。"""
        return self.graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        """边总数。"""
        return self.graph.number_of_edges()

    def get_neighbors(self, node_id: str) -> List[str]:
        """获取指定节点的所有邻居。"""
        return list(self.graph.neighbors(node_id))

    def shortest_path(self, source: str, target: str) -> List[str]:
        """
        计算两个节点之间的最短路径。

        参数:
            source: 起始节点
            target: 目标节点

        返回:
            最短路径上的节点列表
        """
        return nx.shortest_path(self.graph, source, target)

    def find_articulation_points(self) -> Set[str]:
        """
        查找拓扑图中的割点（关键节点）。

        割点是指删除后会导致网络不连通的节点，
        这些节点在网络中是单点故障风险点。

        返回:
            割点节点ID集合
        """
        return set(nx.articulation_points(self.graph))

    def degree_analysis(self) -> Dict[str, int]:
        """
        节点度数分析。

        返回:
            字典：节点ID -> 度数（连接的边数）
        """
        return dict(self.graph.degree())

    def get_critical_links(self) -> List[Tuple[str, str]]:
        """
        查找关键链路（桥边）。

        桥边是删除后会导致网络不连通的边。

        返回:
            桥边列表，每项为 (source, target) 元组
        """
        return list(nx.bridges(self.graph))

    def is_connected(self) -> bool:
        """检查拓扑图是否连通。"""
        return nx.is_connected(self.graph)

    def connected_components(self) -> List[Set[str]]:
        """获取所有连通分量。"""
        return [comp for comp in nx.connected_components(self.graph)]

    def get_stats(self) -> Dict:
        """
        获取拓扑图的统计信息。

        返回:
            包含各种拓扑指标的字典
        """
        stats = {
            "节点数": self.node_count,
            "边数": self.edge_count,
            "是否连通": self.is_connected(),
            "连通分量数": nx.number_connected_components(self.graph),
        }
        if self.node_count > 0:
            stats["平均度数"] = sum(dict(self.graph.degree()).values()) / self.node_count
            stats["最大度数节点"] = max(self.graph.degree(), key=lambda x: x[1])
            stats["割点数"] = len(self.find_articulation_points())
            stats["桥边数"] = len(self.get_critical_links())
            if self.is_connected():
                stats["平均最短路径长度"] = nx.average_shortest_path_length(self.graph)
                stats["图直径"] = nx.diameter(self.graph)
        return stats

    def get_node_types(self) -> Dict[str, List[str]]:
        """按设备类型分组返回节点。"""
        types: Dict[str, List[str]] = {}
        for node, attrs in self.graph.nodes(data=True):
            t = attrs.get("node_type", "unknown")
            types.setdefault(t, []).append(node)
        return types

    def to_dict(self) -> dict:
        """将拓扑图导出为字典。"""
        nodes = []
        for node, attrs in self.graph.nodes(data=True):
            n = {"id": node, **attrs}
            nodes.append(n)
        edges = []
        for u, v, attrs in self.graph.edges(data=True):
            e = {"source": u, "target": v, **attrs}
            edges.append(e)
        return {"nodes": nodes, "edges": edges}

    def to_json(self, indent: int = 2) -> str:
        """将拓扑图导出为JSON字符串。"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
