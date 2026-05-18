"""
拓扑渲染模块 - 使用matplotlib和networkx绘制网络拓扑图。

功能：
    - 根据设备类型使用不同形状绘制节点（路由器=三角形，交换机=方形，服务器=圆形）
    - 颜色编码区分设备类型
    - 支持导出为PNG和SVG格式
    - 自动布局
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # 非交互式后端，兼容无显示器环境
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx

from .topology import TopologyGraph

# 设备类型 -> (形状, 颜色, 大小)
DEVICE_STYLES: Dict[str, Tuple[str, str, int]] = {
    "router":  ("^", "#E74C3C", 800),   # 红色三角形
    "switch":  ("s", "#3498DB", 700),   # 蓝色方形
    "server":  ("o", "#2ECC71", 600),   # 绿色圆形
    "pc":      ("o", "#95A5A6", 300),   # 灰色小圆
    "firewall": ("D", "#E67E22", 700),  # 橙色菱形
    "unknown": ("o", "#BDC3C7", 400),   # 浅灰圆
}


def render_topology(
    topology: TopologyGraph,
    output_path: str = "topology.png",
    title: str = "网络拓扑图",
    figsize: Tuple[int, int] = (14, 10),
    show_labels: bool = True,
    dpi: int = 150,
    layout: str = "spring",
) -> str:
    """
    渲染网络拓扑图为图片文件。

    参数:
        topology: TopologyGraph拓扑图对象
        output_path: 输出文件路径（支持.png和.svg）
        title: 图表标题
        figsize: 图片尺寸（宽, 高）英寸
        show_labels: 是否显示节点标签
        dpi: 图片分辨率
        layout: 布局算法，可选 spring/kamada_kawai/shell/spectral

    返回:
        输出文件的路径
    """
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    G = topology.graph

    # 选择布局算法
    layout_func = {
        "spring": lambda g: nx.spring_layout(g, k=2, iterations=50, seed=42),
        "kamada_kawai": nx.kamada_kawai_layout,
        "shell": nx.shell_layout,
        "spectral": nx.spectral_layout,
    }
    pos_fn = layout_func.get(layout, layout_func["spring"])
    pos = pos_fn(G)

    # 按设备类型分组绘制节点
    legend_handles = []
    for dev_type, (marker, color, size) in DEVICE_STYLES.items():
        nodes_of_type = [
            n for n, attrs in G.nodes(data=True)
            if attrs.get("node_type", "unknown") == dev_type
        ]
        if nodes_of_type:
            nx.draw_networkx_nodes(
                G, pos, nodelist=nodes_of_type,
                node_shape=marker, node_color=color,
                node_size=size, alpha=0.9, ax=ax,
            )
            # 图例标签映射
            type_labels = {
                "router": "路由器", "switch": "交换机",
                "server": "服务器", "pc": "PC终端",
                "firewall": "防火墙", "unknown": "未知设备",
            }
            legend_handles.append(
                mpatches.Patch(color=color, label=type_labels.get(dev_type, dev_type))
            )

    # 绘制边
    nx.draw_networkx_edges(G, pos, edge_color="#7F8C8D", width=1.5,
                           alpha=0.7, ax=ax)

    # 绘制标签
    if show_labels:
        labels = {n: attrs.get("label", n) for n, attrs in G.nodes(data=True)}
        nx.draw_networkx_labels(G, pos, labels, font_size=8,
                                font_family="sans-serif", ax=ax)

    # 设置标题和图例
    ax.set_title(title, fontsize=16, fontweight="bold", pad=20)
    if legend_handles:
        ax.legend(handles=legend_handles, loc="upper left",
                  fontsize=9, framealpha=0.9)
    ax.axis("off")
    plt.tight_layout()

    # 保存文件
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)

    return output_path


def render_from_json(
    json_path: str,
    output_path: str = "topology.png",
    title: str = "网络拓扑图",
    **kwargs,
) -> str:
    """
    从JSON文件加载拓扑数据并渲染。

    参数:
        json_path: 拓扑JSON文件路径
        output_path: 输出图片路径
        title: 图表标题
        **kwargs: 传递给render_topology的其他参数

    返回:
        输出文件的路径
    """
    topology = TopologyGraph.from_json(json_path)
    return render_topology(topology, output_path=output_path, title=title, **kwargs)
