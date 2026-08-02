#!/usr/bin/env python3
"""Apply Mihomo v1.19.29 WireGuard-only Linux-like profile v4.

v4 keeps the verified v3 TCP/IPv4 and IPv6 Flow Label work, then adds the
missing Linux default PMTU behavior for locally generated IPv6 TCP/UDP packets:
oversized packets return ErrMessageTooLong instead of source fragmentation.
"""
from __future__ import annotations

import argparse
import pathlib

import apply_linuxlike_v3_base as base


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def patch_v4(root: pathlib.Path) -> None:
    # Generalize v3's IPv4-only local DF marker into a family-neutral PMTU
    # marker that both IPv4 and IPv6 network layers can enforce.
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/registration.go"
    text = base.read(path)
    text = text.replace("EnforceLocalDF", "EnforceLocalMTU")
    text = text.replace(
        "// EnforceLocalMTU makes the IPv4 layer return ErrMessageTooLong instead\n"
        "\t// of fragmenting a locally generated packet carrying DF. Upstream gVisor\n"
        "\t// currently enforces that path only for forwarded packets.",
        "// EnforceLocalMTU makes IPv4/IPv6 return ErrMessageTooLong instead of\n"
        "\t// source-fragmenting a locally generated packet under path-MTU discovery.",
    )
    text = text.replace(
        "// EnforceLocalMTU is true when a locally generated Linux-like packet\n"
        "\t// must not be fragmented after the transport selected DF.",
        "// EnforceLocalMTU is true when a locally generated Linux-like packet\n"
        "\t// must not be source-fragmented under path-MTU discovery.",
    )
    base.write(path, text)

    # TCP: mark all Linux-like IPv4/IPv6 packets as PMTU-enforced. TCP already
    # sizes segments from route MSS, so this is a safety path matching Linux.
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go"
    text = base.read(path)
    text = replace_once(
        text,
        "\tipv6FlowLabel uint32\n\tdf             bool\n",
        "\tipv6FlowLabel   uint32\n\tenforceLocalMTU bool\n\tdf              bool\n",
        "TCP PMTU field",
    )
    text = replace_once(
        text,
        "\tif e.protocol.linuxLike {\n\t\tswitch r.NetProto() {",
        "\tif e.protocol.linuxLike {\n\t\ttf.enforceLocalMTU = true\n\t\tswitch r.NetProto() {",
        "TCP PMTU selection",
    )
    count = text.count("EnforceLocalDF:         tf.ipv4IDSet && tf.df,")
    if count != 2:
        raise RuntimeError(f"TCP PMTU params: expected 2 matches, found {count}")
    text = text.replace(
        "EnforceLocalDF:         tf.ipv4IDSet && tf.df,",
        "EnforceLocalMTU:        tf.enforceLocalMTU,",
    )
    base.write(path, text)

    # IPv4 consumes the renamed family-neutral marker; packet behavior remains
    # identical to v3.
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv4/ipv4.go"
    text = base.read(path).replace("EnforceLocalDF", "EnforceLocalMTU")
    base.write(path, text)

    # IPv6 now propagates and enforces the PMTU marker. Default Linux IPv6
    # sockets use PMTU discovery; oversized local TCP/UDP packets should fail
    # rather than acquire a Fragment Header.
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go"
    text = base.read(path)
    text = replace_once(
        text,
        "\tpkt.NetworkProtocolNumber = ProtocolNumber\n\treturn nil\n}\n\nfunc packetMustBeFragmented",
        "\tpkt.NetworkProtocolNumber = ProtocolNumber\n"
        "\tpkt.NetworkPacketInfo.EnforceLocalMTU = params.EnforceLocalMTU\n"
        "\treturn nil\n}\n\nfunc packetMustBeFragmented",
        "IPv6 PMTU marker propagation",
    )
    text = replace_once(
        text,
        "\tif packetMustBeFragmented(pkt, networkMTU) {\n"
        "\t\tif pkt.NetworkPacketInfo.IsForwardedPacket {",
        "\tif packetMustBeFragmented(pkt, networkMTU) {\n"
        "\t\tif pkt.NetworkPacketInfo.IsForwardedPacket || pkt.NetworkPacketInfo.EnforceLocalMTU {",
        "IPv6 local PMTU enforcement",
    )
    base.write(path, text)

    # UDP: PMTU Want/Do applies to both families. IPv4 additionally carries DF;
    # IPv6 has no DF bit but uses the same no-source-fragment decision.
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/internal/network/endpoint.go"
    text = base.read(path)
    text = replace_once(
        text,
        "\tdf            bool\n\tipv4ID        uint16\n",
        "\tdf              bool\n\tenforceLocalMTU bool\n\tipv4ID          uint16\n",
        "UDP PMTU context field",
    )
    text = replace_once(
        text,
        "\t\tEnforceLocalDF:         c.e.linuxLike && c.df,\n\t\tDF:                    c.df,",
        "\t\tEnforceLocalMTU:        c.enforceLocalMTU,\n\t\tDF:                    c.df,",
        "UDP PMTU network params",
    )
    text = replace_once(
        text,
        "\tdf := false\n"
        "\tif e.linuxLike && route.NetProto() == header.IPv4ProtocolNumber {\n"
        "\t\tdf = e.pmtud == tcpip.PMTUDiscoveryWant || e.pmtud == tcpip.PMTUDiscoveryDo\n"
        "\t}\n\n"
        "\treturn WriteContext{\n"
        "\t\te:     e,\n"
        "\t\troute: route,\n"
        "\t\tttl:   ttl,\n"
        "\t\ttos:   tos,\n"
        "\t\tdf:    df,\n"
        "\t}, nil",
        "\tenforceLocalMTU := e.linuxLike && (e.pmtud == tcpip.PMTUDiscoveryWant || e.pmtud == tcpip.PMTUDiscoveryDo)\n"
        "\tdf := enforceLocalMTU && route.NetProto() == header.IPv4ProtocolNumber\n\n"
        "\treturn WriteContext{\n"
        "\t\te:               e,\n"
        "\t\troute:           route,\n"
        "\t\tttl:             ttl,\n"
        "\t\ttos:             tos,\n"
        "\t\tdf:              df,\n"
        "\t\tenforceLocalMTU: enforceLocalMTU,\n"
        "\t}, nil",
        "UDP PMTU context initialization",
    )
    base.write(path, text)


def verify_v4(root: pathlib.Path) -> None:
    required = {
        "adapter/outbound/wireguard.go": ["NewStackDeviceLinuxLike"],
        "vendor/github.com/metacubex/sing-wireguard/device_stack.go": [
            "SetPortRange(32768, 60999)", "tcp.NewProtocolLinuxLike", "udp.NewProtocolLinuxLike"
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/linuxlike_flow.go": [
            "bits.RotateLeft32", "0x00080000", "uint32(protocol)"
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/registration.go": [
            "EnforceLocalMTU bool", "IPv6FlowLabel uint32", "IPv4IDSet bool"
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go": [
            "tf.enforceLocalMTU = true", "tf.enforceLocalMTU",
            "IPv6FlowLabel:         tf.ipv6FlowLabel", "Emulate linux option order"
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv4/ipv4.go": [
            "pkt.NetworkPacketInfo.EnforceLocalMTU = params.EnforceLocalMTU",
            "pkt.NetworkPacketInfo.IsForwardedPacket || pkt.NetworkPacketInfo.EnforceLocalMTU"
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go": [
            "FlowLabel:         params.IPv6FlowLabel",
            "pkt.NetworkPacketInfo.EnforceLocalMTU = params.EnforceLocalMTU",
            "pkt.NetworkPacketInfo.IsForwardedPacket || pkt.NetworkPacketInfo.EnforceLocalMTU"
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/internal/network/endpoint.go": [
            "enforceLocalMTU := e.linuxLike", "c.enforceLocalMTU",
            "PMTUDiscoveryWant"
        ],
    }
    for rel, needles in required.items():
        text = base.read(root / rel)
        for needle in needles:
            if needle not in text:
                raise RuntimeError(f"v4 verification failed: {needle!r} missing from {rel}")
        if "EnforceLocalDF" in text:
            raise RuntimeError(f"stale EnforceLocalDF remains in {rel}")

    selected = []
    for path in (root / "adapter/outbound").glob("*.go"):
        if "NewStackDeviceLinuxLike" in base.read(path):
            selected.append(path.name)
    if selected != ["wireguard.go"]:
        raise RuntimeError(f"Linux-like constructor leaked outside WireGuard: {selected}")


def apply_base(root: pathlib.Path) -> None:
    base.patch_mihomo(root)
    base.patch_sing_device_stack(root)
    base.patch_sing_gonet(root)
    base.patch_stack_flow_label(root)
    base.patch_tcp_protocol(root)
    base.patch_tcp_endpoint(root)
    base.patch_tcp_connect(root)
    base.patch_network_header_contract(root)
    base.patch_udp_protocol(root)
    base.patch_udp_endpoint(root)
    base.patch_datagram_network(root)
    base.verify(root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = pathlib.Path(args.root).resolve()
    if not args.verify_only:
        apply_base(root)
        patch_v4(root)
    verify_v4(root)
    print("Linux-like WireGuard v4 patch verification: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
