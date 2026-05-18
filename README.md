# 🌐 NetVisual - 网络拓扑可视化工具

```
 _   _      _   __     __    _ _          
| \ | | ___| |_\ \   / /_ _| | |__   ___ 
|  \| |/ _ \ __|\ \ / / _` | | '_ \ / _ \
| |\  |  __/ |_  \ V / (_| | | | | |  __/
|_| \_|\___|\__|  \_/ \__,_|_|_| |_|\___|
                                          
     网络拓扑可视化与分析工具 v1.0
```

## ✨ 功能特性

- **网络扫描**: 基于ARP/ICMP协议自动发现局域网中的活跃主机
- **拓扑解析**: 解析traceroute输出和设备配置文件，自动生成拓扑数据
- **拓扑分析**: 基于NetworkX进行最短路径计算、割点分析、度数统计
- **可视化渲染**: 使用matplotlib绘制拓扑图，不同设备类型用不同形状和颜色表示
- **Web交互界面**: 基于Flask + vis.js的交互式Web拓扑查看器，支持拖拽和缩放
- **CLI命令行**: 提供scan/render/analyze/web四个子命令

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    CLI (cli.py)                      │
│         scan | render | analyze | web                │
└──────┬──────────┬──────────┬──────────┬──────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
┌──────────┐ ┌─────────┐ ┌────────┐ ┌──────────┐
│ scanner  │ │ parser  │ │topology│ │ renderer │
│ ARP/ICMP │ │ 解析器  │ │ 图模型 │ │  渲染器  │
│ 网络扫描 │ │         │ │        │ │          │
└──────────┘ └─────────┘ └────────┘ └──────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              ┌──────────┐  ┌──────────┐
              │ NetworkX │  │  Flask   │
              │ 图分析   │  │  Web UI  │
              └──────────┘  └──────────┘
```

## 📁 项目结构

```
netvisual/
├── netvisual/               # 核心Python包
│   ├── __init__.py          # 包初始化
│   ├── scanner.py           # ARP/ICMP网络扫描
│   ├── parser.py            # traceroute和配置文件解析
│   ├── topology.py          # NetworkX拓扑图模型与分析
│   └── renderer.py          # matplotlib拓扑渲染
├── web/                     # Web应用
│   ├── app.py               # Flask Web服务
│   └── templates/
│       └── index.html       # vis.js交互式前端
├── examples/                # 示例拓扑数据
│   ├── campus_network.json  # 校园网拓扑
│   └── datacenter.json      # 数据中心拓扑
├── cli.py                   # CLI入口
├── requirements.txt         # Python依赖
├── LICENSE                  # MIT许可证
└── README.md                # 本文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 渲染拓扑图

```bash
python cli.py render -i examples/campus_network.json -o campus.png
```

### 3. 分析拓扑

```bash
python cli.py analyze -i examples/campus_network.json
```

### 4. 启动Web界面

```bash
python cli.py web --port 5000
# 浏览器访问 http://localhost:5000
```

### 5. 扫描网络

```bash
# ARP扫描（需要root/管理员权限）
sudo python cli.py scan -s 192.168.1.0/24 -m arp -o result.json

# ICMP扫描
python cli.py scan -s 192.168.1.0/24 -m icmp -o result.json
```

## 📖 使用示例

### Python API

```python
from netvisual.topology import TopologyGraph
from netvisual.renderer import render_topology
from netvisual.parser import load_topology_json

# 加载拓扑数据
topo = TopologyGraph.from_json("examples/campus_network.json")

# 分析
print("节点数:", topo.node_count)
print("割点:", topo.find_articulation_points())
print("最短路径:", topo.shortest_path("pc-1", "srv-web"))

# 渲染
render_topology(topo, output_path="campus.png", title="校园网拓扑")
```

### 拓扑JSON格式

```json
{
  "nodes": [
    {"id": "router-1", "label": "核心路由器", "type": "router", "ip": "10.0.0.1"}
  ],
  "edges": [
    {"source": "router-1", "target": "switch-1", "bandwidth": "1Gbps"}
  ]
}
```

支持的设备类型: `router`(路由器), `switch`(交换机), `server`(服务器), `pc`(PC终端), `firewall`(防火墙)

## 📊 设备图例

| 类型 | 形状 | 颜色 |
|------|------|------|
| 路由器 | △ 三角形 | 🔴 红色 |
| 交换机 | □ 方形 | 🔵 蓝色 |
| 服务器 | ○ 圆形 | 🟢 绿色 |
| PC终端 | · 小圆 | ⚪ 灰色 |
| 防火墙 | ◇ 菱形 | 🟠 橙色 |

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件
