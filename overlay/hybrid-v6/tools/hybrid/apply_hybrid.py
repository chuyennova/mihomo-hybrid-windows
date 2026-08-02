#!/usr/bin/env python3
"""Apply the Mihomo v1.19.29 four-profile WireGuard vendor patch.

The repository-level files in this overlay already contain the Windows lazy
Wintun lifecycle and YAML selector. This script runs after `go mod vendor` and
turns the locked sing-wireguard/gVisor dependencies into per-stack profiles:
macOS-like, Linux-like and Android-like. No global profile state is used.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
LINUXBASE = HERE / "linuxbase"
sys.path.insert(0, str(LINUXBASE))
import apply_linuxlike_v3_base as linux3  # type: ignore
import apply_linuxlike as linux4  # type: ignore


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def write(path: pathlib.Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def apply_linux_base_without_mihomo(root: pathlib.Path) -> None:
    # The deepest/common contract comes from the verified Linux v4 overlay.
    linux3.patch_sing_device_stack(root)
    linux3.patch_sing_gonet(root)
    linux3.patch_stack_flow_label(root)
    linux3.patch_tcp_protocol(root)
    linux3.patch_tcp_endpoint(root)
    linux3.patch_tcp_connect(root)
    linux3.patch_network_header_contract(root)
    linux3.patch_udp_protocol(root)
    linux3.patch_udp_endpoint(root)
    linux3.patch_datagram_network(root)
    linux4.patch_v4(root)


def patch_sing_device_stack(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/sing-wireguard/device_stack.go"
    text = read(path)
    text = replace_once(
        text,
        """\taddr4      tcpip.Address
\taddr6      tcpip.Address
\tlinuxLike  bool
}

func NewStackDevice(localAddresses []netip.Prefix, mtu uint32) (*StackDevice, error) {
\treturn newStackDevice(localAddresses, mtu, false)
}

// NewStackDeviceLinuxLike creates an independent Linux-oriented gVisor stack
// for one WireGuard outbound. The binary still runs on Windows; only packets
// generated inside this WireGuard device use the Linux-like wire profile.
func NewStackDeviceLinuxLike(localAddresses []netip.Prefix, mtu uint32) (*StackDevice, error) {
\treturn newStackDevice(localAddresses, mtu, true)
}

func newStackDevice(localAddresses []netip.Prefix, mtu uint32, linuxLike bool) (*StackDevice, error) {
\tvar tcpProtocol stack.TransportProtocolFactory = tcp.NewProtocol
\tvar udpProtocol stack.TransportProtocolFactory = udp.NewProtocol
\tif linuxLike {
\t\ttcpProtocol = tcp.NewProtocolLinuxLike
\t\tudpProtocol = udp.NewProtocolLinuxLike
\t}
\tipStack := stack.New(stack.Options{
\t\tNetworkProtocols:   []stack.NetworkProtocolFactory{ipv4.NewProtocol, ipv6.NewProtocol},
\t\tTransportProtocols: []stack.TransportProtocolFactory{tcpProtocol, udpProtocol, icmp.NewProtocol4, icmp.NewProtocol6},
\t\tHandleLocal:        true,
\t})
\tif linuxLike {
\t\t// Linux default net.ipv4.ip_local_port_range. gVisor's PortManager is
\t\t// owned by this stack, so every WireGuard outbound remains isolated.
\t\tif err := ipStack.SetPortRange(32768, 60999); err != nil {
\t\t\treturn nil, E.New("set Linux-like ephemeral port range: ", err.String())
\t\t}
\t}
""",
        """\taddr4   tcpip.Address
\taddr6   tcpip.Address
\tprofile NetworkProfile
}

// NetworkProfile is immutable for the lifetime of one StackDevice.
type NetworkProfile uint8

const (
\tNetworkProfileDefault NetworkProfile = iota
\tNetworkProfileMacOS
\tNetworkProfileLinux
\tNetworkProfileAndroid
)

func NewStackDevice(localAddresses []netip.Prefix, mtu uint32) (*StackDevice, error) {
\treturn NewStackDeviceWithProfile(localAddresses, mtu, NetworkProfileDefault)
}

// NewStackDeviceWithProfile creates one independent userspace stack for one
// WireGuard outbound. Profile state, ports, RNG and flow labels are per stack.
func NewStackDeviceWithProfile(localAddresses []netip.Prefix, mtu uint32, profile NetworkProfile) (*StackDevice, error) {
\tvar ipv6Protocol stack.NetworkProtocolFactory = ipv6.NewProtocol
\tvar tcpProtocol stack.TransportProtocolFactory = tcp.NewProtocol
\tvar udpProtocol stack.TransportProtocolFactory = udp.NewProtocol
\tswitch profile {
\tcase NetworkProfileDefault:
\tcase NetworkProfileMacOS:
\t\ttcpProtocol = tcp.NewProtocolMacOSLike
\t\tudpProtocol = udp.NewProtocolMacOSLike
\tcase NetworkProfileLinux:
\t\ttcpProtocol = tcp.NewProtocolLinuxLike
\t\tudpProtocol = udp.NewProtocolLinuxLike
\tcase NetworkProfileAndroid:
\t\tipv6Protocol = ipv6.NewProtocolAndroidLike
\tdefault:
\t\treturn nil, E.New("invalid WireGuard network profile: ", profile)
\t}
\tipStack := stack.New(stack.Options{
\t\tNetworkProtocols:   []stack.NetworkProtocolFactory{ipv4.NewProtocol, ipv6Protocol},
\t\tTransportProtocols: []stack.TransportProtocolFactory{tcpProtocol, udpProtocol, icmp.NewProtocol4, icmp.NewProtocol6},
\t\tHandleLocal:        true,
\t})
\tswitch profile {
\tcase NetworkProfileMacOS:
\t\tif err := ipStack.SetPortRange(49152, 65535); err != nil {
\t\t\tipStack.Close()
\t\t\treturn nil, E.New("set macOS-like ephemeral port range: ", err.String())
\t\t}
\tcase NetworkProfileLinux, NetworkProfileAndroid:
\t\tif err := ipStack.SetPortRange(32768, 60999); err != nil {
\t\t\tipStack.Close()
\t\t\treturn nil, E.New("set Linux/Android-like ephemeral port range: ", err.String())
\t\t}
\t}
""",
        "sing-wireguard profile constructor",
    )
    text = replace_once(
        text,
        """\t\tctx:       ctx,
\t\tctxCancel: cancel,
\t\tlinuxLike: linuxLike,
\t}
""",
        """\t\tctx:       ctx,
\t\tctxCancel: cancel,
\t\tprofile:   profile,
\t}
""",
        "sing-wireguard profile state",
    )
    text = replace_once(
        text,
        """\tcase N.NetworkTCP:
\t\tif w.linuxLike {
\t\t\tconn, err = DialTCPWithBindLinuxLike(ctx, w.stack, bind, addr, networkProtocol)
\t\t} else {
\t\t\tconn, err = DialTCPWithBind(ctx, w.stack, bind, addr, networkProtocol)
\t\t}
""",
        """\tcase N.NetworkTCP:
\t\tif w.profile == NetworkProfileDefault {
\t\t\tconn, err = DialTCPWithBind(ctx, w.stack, bind, addr, networkProtocol)
\t\t} else {
\t\t\tconn, err = DialTCPWithBindProfile(ctx, w.stack, bind, addr, networkProtocol)
\t\t}
""",
        "sing-wireguard profile TCP dial",
    )
    write(path, text)


def patch_sing_gonet(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/sing-wireguard/gonet.go"
    text = read(path)
    text = text.replace("DialTCPWithBindLinuxLike", "DialTCPWithBindProfile")
    text = text.replace(
        "// DialTCPWithBindProfile leaves SO_KEEPALIVE disabled. Linux does not\n"
        "// automatically enable keepalive on every ordinary outbound TCP socket.",
        "// DialTCPWithBindProfile leaves SO_KEEPALIVE disabled for all explicit\n"
        "// network profiles; applications may still enable it themselves.",
    )
    write(path, text)


def patch_tcp_protocol(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go"
    text = read(path)
    text = replace_once(
        text,
        """type protocol struct {
\tstack     *stack.Stack
\tlinuxLike bool `state:\"nosave\"`

\tmu""",
        """type protocol struct {
\tstack      *stack.Stack
\tlinuxLike  bool `state:\"nosave\"`
\tmacOSLike  bool `state:\"nosave\"`

\tmu""",
        "TCP combined profile fields",
    )
    text = replace_once(
        text,
        """func NewProtocol(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccReno, nil, false)
}

// NewProtocolLinuxLike keeps gVisor's native Linux TCP option ordering and
// enables only the WireGuard-specific differences selected by this patch.
func NewProtocolLinuxLike(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccCubic, nil, true)
}
""",
        """func NewProtocol(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccReno, nil, false, false)
}

func NewProtocolLinuxLike(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccCubic, nil, true, false)
}

func NewProtocolMacOSLike(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccCubic, nil, false, true)
}

func (p *protocol) newIPv6FlowLabel() uint32 {
\trng := p.stack.SecureRNG()
\treturn rng.Uint32() & 0x000fffff
}
""",
        "TCP profile constructors",
    )
    text = text.replace("return newProtocol(s, ccReno, probe, false)", "return newProtocol(s, ccReno, probe, false, false)")
    text = replace_once(
        text,
        """func NewProtocolCUBIC(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccCubic, nil, false)
}

func newProtocol(s *stack.Stack, cc string, probe TCPProbeFunc, linuxLike bool) stack.TransportProtocol {
""",
        """func NewProtocolCUBIC(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccCubic, nil, false, false)
}

func newProtocol(s *stack.Stack, cc string, probe TCPProbeFunc, linuxLike, macOSLike bool) stack.TransportProtocol {
""",
        "TCP newProtocol signature",
    )
    text = replace_once(
        text,
        """\tp := protocol{
\t\tstack:     s,
\t\tlinuxLike: linuxLike,
""",
        """\tp := protocol{
\t\tstack:     s,
\t\tlinuxLike: linuxLike,
\t\tmacOSLike: macOSLike,
""",
        "TCP profile initialization",
    )
    write(path, text)


def patch_tcp_endpoint(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/endpoint.go"
    text = read(path)
    text = replace_once(
        text,
        """\tif protocol.linuxLike {
\t\trng := s.SecureRNG()
\t\te.ipv4ID = rng.Uint16()
\t\tif e.ipv4ID == 0 {
\t\t\te.ipv4ID = 1
\t\t}
\t}
\te.ops.InitHandler(e, e.stack, GetTCPSendBufferLimits, GetTCPReceiveBufferLimits)
""",
        """\tif protocol.macOSLike && netProto == header.IPv6ProtocolNumber {
\t\te.ipv6FlowLabel = protocol.newIPv6FlowLabel()
\t}
\tif protocol.linuxLike {
\t\trng := s.SecureRNG()
\t\te.ipv4ID = rng.Uint16()
\t\tif e.ipv4ID == 0 {
\t\t\te.ipv4ID = 1
\t\t}
\t}
\te.ops.InitHandler(e, e.stack, GetTCPSendBufferLimits, GetTCPReceiveBufferLimits)
""",
        "TCP endpoint profile initialization",
    )
    text = replace_once(
        text,
        """func (e *Endpoint) initialReceiveWindow() int {
\tif e.protocol.linuxLike {
""",
        """func (e *Endpoint) initialReceiveWindow() int {
\tif e.protocol.macOSLike {
\t\treturn math.MaxUint16
\t}
\tif e.protocol.linuxLike {
""",
        "TCP macOS initial window",
    )
    text = replace_once(
        text,
        """func (e *Endpoint) rcvWndScaleForHandshake() int {
\tbufSizeForScale := e.ops.GetReceiveBufferSize()
""",
        """func (e *Endpoint) rcvWndScaleForHandshake() int {
\tif e.protocol.macOSLike {
\t\treturn 4
\t}
\tbufSizeForScale := e.ops.GetReceiveBufferSize()
""",
        "TCP macOS window scale",
    )
    write(path, text)


def patch_tcp_connect(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go"
    text = read(path)
    text = replace_once(text, "func makeSynOptions(opts header.TCPSynOptions) []byte {", "func makeDefaultSynOptions(opts header.TCPSynOptions) []byte {", "rename SYN encoder")
    text = replace_once(
        text,
        """\treturn options[:offset]
}

// tcpFields is a struct to carry different parameters required by the
""",
        """\treturn options[:offset]
}

func makeDarwinSynOptions(opts header.TCPSynOptions) []byte {
\toptions := getOptions()
\toffset := header.EncodeMSSOption(uint32(opts.MSS), options)
\tif opts.WS >= 0 {
\t\toffset += header.EncodeNOP(options[offset:])
\t\toffset += header.EncodeWSOption(opts.WS, options[offset:])
\t}
\tif opts.TS {
\t\toffset += header.EncodeNOP(options[offset:])
\t\toffset += header.EncodeNOP(options[offset:])
\t\toffset += header.EncodeTSOption(opts.TSVal, opts.TSEcr, options[offset:])
\t}
\tif opts.SACKPermitted {
\t\toffset += header.EncodeSACKPermittedOption(options[offset:])
\t}
\tif offset%4 != 0 {
\t\toptions[offset] = header.TCPOptionEOL
\t\toffset++
\t\tfor offset%4 != 0 {
\t\t\toptions[offset] = 0
\t\t\toffset++
\t\t}
\t}
\treturn options[:offset]
}

func makeSynOptions(opts header.TCPSynOptions, macOSLike bool) []byte {
\tif macOSLike {
\t\treturn makeDarwinSynOptions(opts)
\t}
\treturn makeDefaultSynOptions(opts)
}

// tcpFields is a struct to carry different parameters required by the
""",
        "insert Darwin SYN encoder",
    )
    text = replace_once(
        text,
        """func (e *Endpoint) sendSynTCP(r *stack.Route, tf tcpFields, opts header.TCPSynOptions) tcpip.Error {
\ttf.opts = makeSynOptions(opts)
\tif e.protocol.linuxLike {
\t\t// Linux enables IPv4 PMTU discovery for TCP, including the active SYN.
\t\ttf.df = true
\t}
""",
        """func (e *Endpoint) sendSynTCP(r *stack.Route, tf tcpFields, opts header.TCPSynOptions) tcpip.Error {
\ttf.opts = makeSynOptions(opts, e.protocol.macOSLike)
\tif e.protocol.linuxLike || e.protocol.macOSLike {
\t\ttf.df = true
\t}
""",
        "TCP SYN profile selection",
    )
    text = replace_once(
        text,
        """\ttf.txHash = e.txHash
\tif e.protocol.linuxLike {
\t\ttf.enforceLocalMTU = true
""",
        """\ttf.txHash = e.txHash
\tif e.protocol.macOSLike && r.NetProto() == header.IPv6ProtocolNumber {
\t\ttf.ipv6FlowLabel = e.ipv6FlowLabel
\t}
\tif e.protocol.linuxLike {
\t\ttf.enforceLocalMTU = true
""",
        "TCP packet profile selection",
    )
    write(path, text)


def patch_udp_protocol(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/protocol.go"
    text = read(path)
    text = replace_once(
        text,
        """type protocol struct {
\tstack     *stack.Stack
\tlinuxLike bool `state:\"nosave\"`
}
""",
        """type protocol struct {
\tstack     *stack.Stack
\tlinuxLike bool `state:\"nosave\"`
\tmacOSLike bool `state:\"nosave\"`
}

func (p *protocol) newIPv6FlowLabel() uint32 {
\trng := p.stack.SecureRNG()
\treturn rng.Uint32() & 0x000fffff
}
""",
        "UDP combined profile fields",
    )
    text = replace_once(
        text,
        """\tep.protocol = p
\tif p.linuxLike {
\t\tep.enableLinuxLike()
\t}
\treturn ep, nil
""",
        """\tep.protocol = p
\tif p.linuxLike {
\t\tep.enableLinuxLike()
\t}
\tif p.macOSLike && netProto == header.IPv6ProtocolNumber {
\t\tep.net.SetIPv6FlowLabel(p.newIPv6FlowLabel())
\t}
\treturn ep, nil
""",
        "UDP endpoint profile initialization",
    )
    text = replace_once(
        text,
        """func NewProtocolLinuxLike(s *stack.Stack) stack.TransportProtocol {
\treturn &protocol{stack: s, linuxLike: true}
}
""",
        """func NewProtocolLinuxLike(s *stack.Stack) stack.TransportProtocol {
\treturn &protocol{stack: s, linuxLike: true}
}

func NewProtocolMacOSLike(s *stack.Stack) stack.TransportProtocol {
\treturn &protocol{stack: s, macOSLike: true}
}
""",
        "UDP macOS constructor",
    )
    write(path, text)


def patch_udp_endpoint(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/endpoint.go"
    text = read(path)
    text = replace_once(
        text,
        """\te.net.Disconnect()

\treturn nil
}
""",
        """\te.net.Disconnect()
\tif e.protocol != nil && e.protocol.macOSLike && e.net.NetProto() == header.IPv6ProtocolNumber {
\t\te.net.SetIPv6FlowLabel(e.protocol.newIPv6FlowLabel())
\t}

\treturn nil
}
""",
        "UDP macOS flow-label refresh",
    )
    write(path, text)


def patch_datagram_network(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/internal/network/endpoint.go"
    text = read(path)
    text = replace_once(
        text,
        """\t// +checklocks:mu
\tipv6TClass uint8
\t// +checklocks:mu
\tlinuxLike bool
""",
        """\t// +checklocks:mu
\tipv6TClass uint8
\t// +checklocks:mu
\tipv6FlowLabel uint32
\t// +checklocks:mu
\tlinuxLike bool
""",
        "datagram macOS flow-label state",
    )
    text = replace_once(
        text,
        """func (e *Endpoint) NetProto() tcpip.NetworkProtocolNumber {
\treturn e.netProto
}
""",
        """func (e *Endpoint) NetProto() tcpip.NetworkProtocolNumber {
\treturn e.netProto
}

func (e *Endpoint) SetIPv6FlowLabel(label uint32) {
\te.mu.Lock()
\te.ipv6FlowLabel = label & 0x000fffff
\te.mu.Unlock()
}
""",
        "datagram flow-label setter",
    )
    # v4's context already has ipv6FlowLabel; seed it from per-socket state.
    text = replace_once(
        text,
        """\t\tdf:              df,
\t\tenforceLocalMTU: enforceLocalMTU,
\t}, nil
}
""",
        """\t\tdf:              df,
\t\tenforceLocalMTU: enforceLocalMTU,
\t\tipv6FlowLabel:   e.ipv6FlowLabel,
\t}, nil
}
""",
        "datagram flow-label context",
    )
    write(path, text)


def patch_android_ipv6(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go"
    text = read(path)
    text = replace_once(text, 'import (\n\t"fmt"\n\t"math"\n\t"reflect"\n', 'import (\n\t"encoding/binary"\n\t"fmt"\n\t"math"\n\t"math/bits"\n\t"reflect"\n', "Android IPv6 imports")
    text = replace_once(
        text,
        """\t// DefaultTTL is the default hop limit for IPv6 Packets egressed by
\t// Netstack.
\tDefaultTTL = 64

\t// buckets for fragment identifiers
""",
        """\t// DefaultTTL is the default hop limit for IPv6 Packets egressed by
\t// Netstack.
\tDefaultTTL = 64

\tipv6FlowLabelMask          = 0x000fffff
\tipv6FlowLabelStatelessFlag = 0x00080000

\t// buckets for fragment identifiers
""",
        "Android flow-label constants",
    )
    anchor = """const (
\tforwardingDisabled = 0
\tforwardingEnabled  = 1
)
"""
    helper = anchor + """
func sipRound(v0, v1, v2, v3 *uint64) {
\t*v0 += *v1; *v1 = bits.RotateLeft64(*v1, 13); *v1 ^= *v0; *v0 = bits.RotateLeft64(*v0, 32)
\t*v2 += *v3; *v3 = bits.RotateLeft64(*v3, 16); *v3 ^= *v2
\t*v0 += *v3; *v3 = bits.RotateLeft64(*v3, 21); *v3 ^= *v0
\t*v2 += *v1; *v1 = bits.RotateLeft64(*v1, 17); *v1 ^= *v2; *v2 = bits.RotateLeft64(*v2, 32)
}

func sipHash24(k0, k1 uint64, data []byte) uint64 {
\tv0 := k0 ^ 0x736f6d6570736575; v1 := k1 ^ 0x646f72616e646f6d
\tv2 := k0 ^ 0x6c7967656e657261; v3 := k1 ^ 0x7465646279746573
\toriginalLength := len(data)
\tfor len(data) >= 8 { m := binary.LittleEndian.Uint64(data[:8]); v3 ^= m; sipRound(&v0,&v1,&v2,&v3); sipRound(&v0,&v1,&v2,&v3); v0 ^= m; data = data[8:] }
\tb := uint64(originalLength) << 56
\tfor i, value := range data { b |= uint64(value) << (8 * i) }
\tv3 ^= b; sipRound(&v0,&v1,&v2,&v3); sipRound(&v0,&v1,&v2,&v3); v0 ^= b; v2 ^= 0xff
\tfor i := 0; i < 4; i++ { sipRound(&v0,&v1,&v2,&v3) }
\treturn v0 ^ v1 ^ v2 ^ v3
}
"""
    text = replace_once(text, anchor, helper, "Android SipHash helper")
    text = replace_once(
        text,
        """func (e *endpoint) WritePacket(r *stack.Route, params stack.NetworkHeaderParams, pkt *stack.PacketBuffer) tcpip.Error {
\tdstAddr := r.RemoteAddress()
\tif err := addIPHeader(r.LocalAddress(), dstAddr, pkt, params, nil /* extensionHeaders */); err != nil {
""",
        """func (e *endpoint) WritePacket(r *stack.Route, params stack.NetworkHeaderParams, pkt *stack.PacketBuffer) tcpip.Error {
\tdstAddr := r.RemoteAddress()
\tif e.protocol.androidLike && params.IPv6FlowLabel == 0 {
\t\tparams.IPv6FlowLabel = e.protocol.autoFlowLabel(r.LocalAddress(), dstAddr, params.Protocol, pkt.TransportHeader().Slice())
\t}
\tif err := addIPHeader(r.LocalAddress(), dstAddr, pkt, params, nil /* extensionHeaders */); err != nil {
""",
        "Android automatic flow label",
    )
    text = replace_once(
        text,
        """type protocol struct {
\tstack   *stack.Stack
\toptions Options

\tmu protocolMu
""",
        """type protocol struct {
\tstack        *stack.Stack
\toptions      Options
\tandroidLike  bool      `state:\"nosave\"`
\tflowLabelKey [2]uint64 `state:\"nosave\"`

\tmu protocolMu
""",
        "Android IPv6 protocol state",
    )
    marker = """// Number returns the ipv6 protocol number.
func (p *protocol) Number() tcpip.NetworkProtocolNumber {
"""
    method = """func (p *protocol) autoFlowLabel(src, dst tcpip.Address, proto tcpip.TransportProtocolNumber, transportHeader []byte) uint32 {
\tvar flow [56]byte
\tn := copy(flow[:], src.AsSlice()); n += copy(flow[n:], dst.AsSlice()); flow[n] = byte(proto); n++
\tswitch proto {
\tcase header.TCPProtocolNumber, header.UDPProtocolNumber:
\t\tif len(transportHeader) >= 4 { n += copy(flow[n:], transportHeader[:4]) }
\tcase header.ICMPv6ProtocolNumber:
\t\tif len(transportHeader) >= 2 { n += copy(flow[n:], transportHeader[:2]) }
\t\tif len(transportHeader) >= 6 { n += copy(flow[n:], transportHeader[4:6]) }
\t}
\thash := uint32(sipHash24(p.flowLabelKey[0], p.flowLabelKey[1], flow[:n]))
\treturn (bits.RotateLeft32(hash, 16) & ipv6FlowLabelMask) | ipv6FlowLabelStatelessFlag
}

""" + marker
    text = replace_once(text, marker, method, "Android auto flow-label method")
    text = replace_once(
        text,
        """func NewProtocolWithOptions(opts Options) stack.NetworkProtocolFactory {
\topts.NDPConfigs.validate()

\treturn func(s *stack.Stack) stack.NetworkProtocol {
\t\tp := &protocol{
\t\t\tstack:   s,
\t\t\toptions: opts,
\t\t}
""",
        """func NewProtocolWithOptions(opts Options) stack.NetworkProtocolFactory {
\treturn newProtocolWithOptions(opts, false)
}

func NewProtocolAndroidLike(s *stack.Stack) stack.NetworkProtocol {
\treturn newProtocolWithOptions(Options{}, true)(s)
}

func newProtocolWithOptions(opts Options, androidLike bool) stack.NetworkProtocolFactory {
\topts.NDPConfigs.validate()
\treturn func(s *stack.Stack) stack.NetworkProtocol {
\t\tp := &protocol{stack: s, options: opts, androidLike: androidLike}
\t\tif androidLike {
\t\t\trng := s.SecureRNG(); p.flowLabelKey[0] = rng.Uint64(); p.flowLabelKey[1] = rng.Uint64()
\t\t}
""",
        "Android IPv6 constructor",
    )
    write(path, text)


def create_android_tests(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/androidlike_flowlabel_test.go"
    write(path, """package ipv6

import (
\t\"encoding/binary\"
\t\"testing\"
)

func TestHybridSipHash24Reference(t *testing.T) {
\tvar key [16]byte
\tfor i := range key { key[i] = byte(i) }
\tk0 := binary.LittleEndian.Uint64(key[:8]); k1 := binary.LittleEndian.Uint64(key[8:])
\tif got := sipHash24(k0, k1, nil); got != 0x726fdb47dd0e0e31 { t.Fatalf(\"got %#x\", got) }
}
""")


def verify(root: pathlib.Path) -> None:
    checks = {
        "adapter/outbound/wireguard.go": ["network-profile", "defaultWireGuardMTU", "mtu = defaultWireGuardMTU(profile)"],
        "vendor/github.com/metacubex/sing-wireguard/device_stack.go": ["type NetworkProfile uint8", "NetworkProfileMacOS", "NetworkProfileLinux", "NetworkProfileAndroid", "NewStackDeviceWithProfile", "SetPortRange(49152, 65535)", "SetPortRange(32768, 60999)"],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go": ["macOSLike", "linuxLike", "NewProtocolMacOSLike", "NewProtocolLinuxLike", "rng := p.stack.SecureRNG()"],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go": ["makeDarwinSynOptions", "tf.enforceLocalMTU = true", "e.protocol.macOSLike"],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv4/ipv4.go": ["EnforceLocalMTU", "params.IPv4IDSet"],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go": ["NewProtocolAndroidLike", "sipHash24", "EnforceLocalMTU", "FlowLabel:"],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/protocol.go": ["NewProtocolMacOSLike", "NewProtocolLinuxLike", "rng := p.stack.SecureRNG()"],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/internal/network/endpoint.go": ["SetIPv6FlowLabel", "SetLinuxLike", "enforceLocalMTU"],
    }
    for rel, needles in checks.items():
        text = read(root / rel)
        for needle in needles:
            if needle not in text:
                raise RuntimeError(f"verify failed: {rel} missing {needle!r}")

    for rel in (
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go",
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/protocol.go",
    ):
        if "SecureRNG().Uint32()" in read(root / rel):
            raise RuntimeError(f"verify failed: {rel} calls pointer method on non-addressable SecureRNG temporary")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = pathlib.Path(args.root).resolve()
    if not args.verify_only:
        apply_linux_base_without_mihomo(root)
        patch_sing_device_stack(root)
        patch_sing_gonet(root)
        patch_tcp_protocol(root)
        patch_tcp_endpoint(root)
        patch_tcp_connect(root)
        patch_udp_protocol(root)
        patch_udp_endpoint(root)
        patch_datagram_network(root)
        patch_android_ipv6(root)
        create_android_tests(root)
    verify(root)
    print("Hybrid WireGuard profiles patch verification: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
