"""
网络扫描模块 - 使用ARP/ICMP协议发现局域网中的活跃主机。

功能：
    - ARP扫描：发现本地子网中的主机，获取IP、MAC地址
    - ICMP扫描：通过ping检测主机是否在线
    - 主机名反解析：尝试获取发现主机的主机名
"""

from __future__ import annotations

import ipaddress
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from typing import List, Optional

# scapy为可选依赖，不安装时提供降级方案
try:
    from scapy.all import ARP, Ether, srp, conf  # type: ignore
    HAS_SCAPY = True
except ImportError:
    HAS_SCAPY = False


@dataclass
class Host:
    """发现的网络主机信息。"""
    ip: str
    mac: str = ""
    hostname: str = ""
    vendor: str = ""
    is_alive: bool = True


@dataclass
class ScanResult:
    """扫描结果汇总。"""
    subnet: str
    hosts: List[Host] = field(default_factory=list)
    scan_method: str = "arp"

    @property
    def host_count(self) -> int:
        return len(self.hosts)

    def to_dict(self) -> dict:
        return {
            "subnet": self.subnet,
            "scan_method": self.scan_method,
            "host_count": self.host_count,
            "hosts": [
                {"ip": h.ip, "mac": h.mac, "hostname": h.hostname}
                for h in self.hosts
            ],
        }


def _resolve_hostname(ip: str) -> str:
    """尝试反解析IP地址对应的主机名。"""
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror, OSError):
        return ""


def arp_scan(subnet: str, timeout: float = 2.0) -> ScanResult:
    """
    对指定子网执行ARP扫描。

    参数:
        subnet: 目标子网，例如 "192.168.1.0/24"
        timeout: 扫描超时时间（秒）

    返回:
        ScanResult: 包含所有发现主机信息的扫描结果
    """
    result = ScanResult(subnet=subnet, scan_method="arp")

    if HAS_SCAPY:
        # 使用scapy发送ARP请求
        conf.verb = 0  # 关闭scapy详细输出
        arp_request = ARP(pdst=subnet)
        broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = broadcast / arp_request
        answered, _ = srp(packet, timeout=timeout, verbose=False)

        for sent, received in answered:
            host = Host(
                ip=received.psrc,
                mac=received.hwsrc,
                hostname=_resolve_hostname(received.psrc),
            )
            result.hosts.append(host)
    else:
        # 降级方案：使用系统ping命令
        print("[警告] scapy未安装，使用系统ping进行扫描（速度较慢）")
        result.scan_method = "ping"
        network = ipaddress.ip_network(subnet, strict=False)
        for ip in network.hosts():
            ip_str = str(ip)
            if _ping_host(ip_str):
                host = Host(ip=ip_str, hostname=_resolve_hostname(ip_str))
                result.hosts.append(host)

    return result


def _ping_host(ip: str, timeout: int = 1) -> bool:
    """使用系统ping命令检测主机是否在线。"""
    param = "-n" if sys.platform == "win32" else "-c"
    timeout_param = "-w" if sys.platform == "win32" else "-W"
    try:
        result = subprocess.run(
            ["ping", param, "1", timeout_param, str(timeout), ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout + 2,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def icmp_scan(subnet: str, timeout: float = 2.0) -> ScanResult:
    """
    对指定子网执行ICMP扫描（ping扫描）。

    参数:
        subnet: 目标子网，例如 "192.168.1.0/24"
        timeout: 每个主机的超时时间（秒）

    返回:
        ScanResult: 包含所有在线主机信息的扫描结果
    """
    result = ScanResult(subnet=subnet, scan_method="icmp")
    network = ipaddress.ip_network(subnet, strict=False)

    for ip in network.hosts():
        ip_str = str(ip)
        if _ping_host(ip_str, timeout=int(timeout)):
            host = Host(ip=ip_str, hostname=_resolve_hostname(ip_str))
            result.hosts.append(host)

    return result


def scan(subnet: str, method: str = "arp", timeout: float = 2.0) -> ScanResult:
    """
    网络扫描统一入口。

    参数:
        subnet: 目标子网
        method: 扫描方法，"arp" 或 "icmp"
        timeout: 超时时间（秒）

    返回:
        ScanResult: 扫描结果
    """
    if method == "arp":
        return arp_scan(subnet, timeout=timeout)
    elif method == "icmp":
        return icmp_scan(subnet, timeout=timeout)
    else:
        raise ValueError(f"不支持的扫描方法: {method}，请使用 'arp' 或 'icmp'")
