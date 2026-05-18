"""
Flask Web应用 - 提供交互式网络拓扑可视化Web界面。

功能：
    - REST API：加载拓扑JSON数据
    - vis.js前端交互式拓扑展示
    - 支持拖拽、缩放、点击查看节点信息
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request

# 将项目根目录加入路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from netvisual.topology import TopologyGraph

app = Flask(__name__)

# 当前加载的拓扑数据（内存缓存）
_current_topology: dict = {"nodes": [], "edges": []}


@app.route("/")
def index():
    """主页 - 渲染拓扑可视化页面。"""
    return render_template("index.html")


@app.route("/api/topology", methods=["GET"])
def get_topology():
    """获取当前拓扑数据。"""
    return jsonify(_current_topology)


@app.route("/api/topology/load", methods=["POST"])
def load_topology():
    """从文件路径加载拓扑数据。"""
    global _current_topology
    data = request.get_json()
    filepath = data.get("filepath", "")
    if not filepath or not os.path.isfile(filepath):
        return jsonify({"error": f"文件不存在: {filepath}"}), 400
    try:
        topo = TopologyGraph.from_json(filepath)
        _current_topology = topo.to_dict()
        return jsonify({"message": "加载成功", "node_count": topo.node_count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/topology/upload", methods=["POST"])
def upload_topology():
    """直接上传拓扑JSON数据。"""
    global _current_topology
    data = request.get_json()
    if "nodes" in data and "edges" in data:
        _current_topology = data
        return jsonify({"message": "上传成功", "node_count": len(data["nodes"])})
    return jsonify({"error": "无效的拓扑数据格式"}), 400


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """获取拓扑统计信息。"""
    if not _current_topology["nodes"]:
        return jsonify({"error": "未加载拓扑数据"}), 400
    topo = TopologyGraph.from_dict(_current_topology)
    return jsonify(topo.get_stats())


def run_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """启动Flask Web服务器。"""
    print(f"[*] netvisual Web界面启动: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server(debug=True)
