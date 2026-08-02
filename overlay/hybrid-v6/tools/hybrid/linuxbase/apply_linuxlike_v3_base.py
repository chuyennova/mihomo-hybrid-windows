#!/usr/bin/env python3
"""Apply the Mihomo v1.19.29 WireGuard-only Linux-like profile.

Run after `go mod vendor` from the Mihomo repository root.
Only WireGuard's independent gVisor stack is changed. OpenVPN, MASQUE,
normal TUN and other gVisor consumers preserve upstream behavior.

The patch is strict: every source anchor must match exactly once. A source or
locked dependency change stops the build instead of producing a partial core.
"""
from __future__ import annotations

import argparse
import pathlib


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


def patch_mihomo(root: pathlib.Path) -> None:
    path = root / "adapter/outbound/wireguard.go"
    text = read(path)
    text = replace_once(
        text,
        "outbound.tunDevice, err = wireguard.NewStackDevice(outbound.localPrefixes, uint32(mtu))",
        "outbound.tunDevice, err = wireguard.NewStackDeviceLinuxLike(outbound.localPrefixes, uint32(mtu))",
        "Mihomo WireGuard constructor",
    )
    write(path, text)


def patch_sing_device_stack(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/sing-wireguard/device_stack.go"
    text = read(path)
    text = replace_once(
        text,
        """\taddr4      tcpip.Address
\taddr6      tcpip.Address
}

func NewStackDevice(localAddresses []netip.Prefix, mtu uint32) (*StackDevice, error) {
\tipStack := stack.New(stack.Options{
\t\tNetworkProtocols:   []stack.NetworkProtocolFactory{ipv4.NewProtocol, ipv6.NewProtocol},
\t\tTransportProtocols: []stack.TransportProtocolFactory{tcp.NewProtocol, udp.NewProtocol, icmp.NewProtocol4, icmp.NewProtocol6},
\t\tHandleLocal:        true,
\t})
""",
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
        "sing-wireguard Linux-like constructors",
    )
    text = replace_once(
        text,
        """\t\tctx:       ctx,
\t\tctxCancel: cancel,
\t}
""",
        """\t\tctx:       ctx,
\t\tctxCancel: cancel,
\t\tlinuxLike: linuxLike,
\t}
""",
        "sing-wireguard profile initialization",
    )
    text = replace_once(
        text,
        """\tcase N.NetworkTCP:
\t\tconn, err = DialTCPWithBind(ctx, w.stack, bind, addr, networkProtocol)
""",
        """\tcase N.NetworkTCP:
\t\tif w.linuxLike {
\t\t\tconn, err = DialTCPWithBindLinuxLike(ctx, w.stack, bind, addr, networkProtocol)
\t\t} else {
\t\t\tconn, err = DialTCPWithBind(ctx, w.stack, bind, addr, networkProtocol)
\t\t}
""",
        "sing-wireguard TCP dial selection",
    )
    write(path, text)


def patch_sing_gonet(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/sing-wireguard/gonet.go"
    text = read(path)
    text = replace_once(
        text,
        """func DialTCPWithBind(ctx context.Context, s *stack.Stack, localAddr, remoteAddr tcpip.FullAddress, network tcpip.NetworkProtocolNumber) (*gonet.TCPConn, error) {
\t// Create TCP endpoint, then connect.
""",
        """func DialTCPWithBind(ctx context.Context, s *stack.Stack, localAddr, remoteAddr tcpip.FullAddress, network tcpip.NetworkProtocolNumber) (*gonet.TCPConn, error) {
\treturn dialTCPWithBind(ctx, s, localAddr, remoteAddr, network, true)
}

// DialTCPWithBindLinuxLike leaves SO_KEEPALIVE disabled. Linux does not
// automatically enable keepalive on every ordinary outbound TCP socket.
func DialTCPWithBindLinuxLike(ctx context.Context, s *stack.Stack, localAddr, remoteAddr tcpip.FullAddress, network tcpip.NetworkProtocolNumber) (*gonet.TCPConn, error) {
\treturn dialTCPWithBind(ctx, s, localAddr, remoteAddr, network, false)
}

func dialTCPWithBind(ctx context.Context, s *stack.Stack, localAddr, remoteAddr tcpip.FullAddress, network tcpip.NetworkProtocolNumber, forceKeepalive bool) (*gonet.TCPConn, error) {
\t// Create TCP endpoint, then connect.
""",
        "sing-wireguard TCP dial helper",
    )
    text = replace_once(
        text,
        """\t// sing-box added: set keepalive
\tep.SocketOptions().SetKeepAlive(true)
\tkeepAliveIdle := tcpip.KeepaliveIdleOption(15 * time.Second)
\tep.SetSockOpt(&keepAliveIdle)
\tkeepAliveInterval := tcpip.KeepaliveIntervalOption(15 * time.Second)
\tep.SetSockOpt(&keepAliveInterval)
""",
        """\tif forceKeepalive {
\t\t// Preserve upstream sing-wireguard behavior for ordinary stacks.
\t\tep.SocketOptions().SetKeepAlive(true)
\t\tkeepAliveIdle := tcpip.KeepaliveIdleOption(15 * time.Second)
\t\tep.SetSockOpt(&keepAliveIdle)
\t\tkeepAliveInterval := tcpip.KeepaliveIntervalOption(15 * time.Second)
\t\tep.SetSockOpt(&keepAliveInterval)
\t}
""",
        "sing-wireguard forced keepalive",
    )
    write(path, text)


def patch_stack_flow_label(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/linuxlike_flow.go"
    if path.exists():
        raise RuntimeError(f"Linux flow-label helper already exists: {path}")
    write(
        path,
        """// SPDX-License-Identifier: Apache-2.0

package stack

import (
\t\"crypto/sha256\"
\t\"encoding/binary\"
\t\"math/bits\"

\t\"github.com/metacubex/gvisor/pkg/tcpip\"
)

// LinuxLikeIPv6FlowLabel models Linux's wire-visible automatic IPv6 label:
// one salted flow hash shared by TCP and UDP in this stack, rotate-left by 16,
// keep 20 bits, then set the stateless-range flag. The private stack seed keeps
// different WireGuard outbounds isolated.
func (s *Stack) LinuxLikeIPv6FlowLabel(localAddr, remoteAddr tcpip.Address, localPort, remotePort uint16, protocol tcpip.TransportProtocolNumber) uint32 {
\th := sha256.New()
\tvar secret [8]byte
\tbinary.BigEndian.PutUint32(secret[0:4], s.seed)
\tbinary.BigEndian.PutUint32(secret[4:8], s.tsOffsetSecret)
\t_, _ = h.Write(secret[:])
\t_, _ = h.Write(localAddr.AsSlice())
\t_, _ = h.Write(remoteAddr.AsSlice())
\tvar tuple [8]byte
\tbinary.BigEndian.PutUint16(tuple[0:2], localPort)
\tbinary.BigEndian.PutUint16(tuple[2:4], remotePort)
\tbinary.BigEndian.PutUint32(tuple[4:8], uint32(protocol))
\t_, _ = h.Write(tuple[:])
\tsum := h.Sum(nil)
\tflowHash := bits.RotateLeft32(binary.BigEndian.Uint32(sum[:4]), 16)
\treturn (flowHash & 0x0007ffff) | 0x00080000
}
""",
    )


def patch_tcp_protocol(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go"
    text = read(path)
    text = replace_once(
        text,
        """type protocol struct {
\tstack *stack.Stack

\tmu""",
        """type protocol struct {
\tstack     *stack.Stack
\tlinuxLike bool `state:\"nosave\"`

\tmu""",
        "TCP protocol profile field",
    )
    text = replace_once(
        text,
        """func NewProtocol(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccReno, nil)
}
""",
        """func NewProtocol(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccReno, nil, false)
}

// NewProtocolLinuxLike keeps gVisor's native Linux TCP option ordering and
// enables only the WireGuard-specific differences selected by this patch.
func NewProtocolLinuxLike(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccCubic, nil, true)
}
""",
        "TCP NewProtocol",
    )
    text = replace_once(
        text,
        """\treturn func(s *stack.Stack) stack.TransportProtocol {
\t\treturn newProtocol(s, ccReno, probe)
\t}
""",
        """\treturn func(s *stack.Stack) stack.TransportProtocol {
\t\treturn newProtocol(s, ccReno, probe, false)
\t}
""",
        "TCP NewProtocolProbe",
    )
    text = replace_once(
        text,
        """func NewProtocolCUBIC(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccCubic, nil)
}

func newProtocol(s *stack.Stack, cc string, probe TCPProbeFunc) stack.TransportProtocol {
""",
        """func NewProtocolCUBIC(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccCubic, nil, false)
}

func newProtocol(s *stack.Stack, cc string, probe TCPProbeFunc, linuxLike bool) stack.TransportProtocol {
""",
        "TCP newProtocol signature",
    )
    text = replace_once(
        text,
        """\tp := protocol{
\t\tstack: s,
""",
        """\tp := protocol{
\t\tstack:     s,
\t\tlinuxLike: linuxLike,
""",
        "TCP protocol initialization",
    )
    write(path, text)


def patch_tcp_endpoint(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/endpoint.go"
    text = read(path)
    text = replace_once(
        text,
        """\t// txHash is the transport layer hash to be set on outbound packets
\t// emitted by this endpoint.
\ttxHash uint32
""",
        """\t// txHash is the transport layer hash to be set on outbound packets
\t// emitted by this endpoint.
\ttxHash uint32

\t// Linux uses private per-socket network identity state. Keep it per
\t// endpoint so WireGuard outbounds and flows do not share state.
\tipv4IDMu      sync.Mutex `state:\"nosave\"`
\tipv4ID        uint16
\tipv6FlowLabel uint32
""",
        "TCP endpoint IPv4 ID state",
    )
    text = replace_once(
        text,
        """\te.ops.InitHandler(e, e.stack, GetTCPSendBufferLimits, GetTCPReceiveBufferLimits)
""",
        """\tif protocol.linuxLike {
\t\trng := s.SecureRNG()
\t\te.ipv4ID = rng.Uint16()
\t\tif e.ipv4ID == 0 {
\t\t\te.ipv4ID = 1
\t\t}
\t}
\te.ops.InitHandler(e, e.stack, GetTCPSendBufferLimits, GetTCPReceiveBufferLimits)
""",
        "TCP endpoint IPv4 ID initialization",
    )
    text = replace_once(
        text,
        """// initialReceiveWindow returns the initial receive window to advertise in the
// SYN/SYN-ACK.
func (e *Endpoint) initialReceiveWindow() int {
\trcvWnd := wndFromSpace(e.receiveBufferAvailable())
""",
        """// initialReceiveWindow returns the initial receive window to advertise in the
// SYN/SYN-ACK.
func (e *Endpoint) initialReceiveWindow() int {
\tif e.protocol.linuxLike {
\t\t// Modern Linux starts from 131072 bytes of receive memory, advertises
\t\t// roughly 65535 bytes in SYN, and quantizes to a whole MSS.
\t\tmss := int(calculateAdvertisedMSS(e.userMSS, e.route))
\t\tif mss > 0 {
\t\t\trcvWnd := (math.MaxUint16 / mss) * mss
\t\t\tif rcvWnd > 0 {
\t\t\t\treturn rcvWnd
\t\t\t}
\t\t}
\t}
\trcvWnd := wndFromSpace(e.receiveBufferAvailable())
""",
        "Linux TCP initial receive window",
    )
    text = replace_once(
        text,
        """func (e *Endpoint) isOwnedByUser() bool {
""",
        """func (e *Endpoint) nextLinuxIPv4ID(count uint16) uint16 {
\te.ipv4IDMu.Lock()
\tid := e.ipv4ID
\te.ipv4ID += count
\te.ipv4IDMu.Unlock()
\treturn id
}

func (e *Endpoint) linuxIPv6FlowLabel(id stack.TransportEndpointID) uint32 {
\te.ipv4IDMu.Lock()
\tif e.ipv6FlowLabel == 0 {
\t\te.ipv6FlowLabel = e.stack.LinuxLikeIPv6FlowLabel(
\t\t\tid.LocalAddress,
\t\t\tid.RemoteAddress,
\t\t\tid.LocalPort,
\t\t\tid.RemotePort,
\t\t\tProtocolNumber,
\t\t)
\t}
\tlabel := e.ipv6FlowLabel
\te.ipv4IDMu.Unlock()
\treturn label
}

func (e *Endpoint) isOwnedByUser() bool {
""",
        "TCP IPv4 ID allocator",
    )
    write(path, text)


def patch_tcp_connect(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go"
    text = read(path)
    text = replace_once(
        text,
        """\ttxHash    uint32
\tdf        bool
\texpOptVal uint16
""",
        """\ttxHash         uint32
\tipv4ID        uint16
\tipv4IDSet     bool
\tipv6FlowLabel uint32
\tdf             bool
\texpOptVal      uint16
""",
        "TCP fields network identity",
    )
    text = replace_once(
        text,
        """func (e *Endpoint) sendSynTCP(r *stack.Route, tf tcpFields, opts header.TCPSynOptions) tcpip.Error {
\ttf.opts = makeSynOptions(opts)
""",
        """func (e *Endpoint) sendSynTCP(r *stack.Route, tf tcpFields, opts header.TCPSynOptions) tcpip.Error {
\ttf.opts = makeSynOptions(opts)
\tif e.protocol.linuxLike {
\t\t// Linux enables IPv4 PMTU discovery for TCP, including the active SYN.
\t\ttf.df = true
\t}
""",
        "Linux TCP SYN DF",
    )
    text = replace_once(
        text,
        """func (e *Endpoint) sendTCP(r *stack.Route, tf tcpFields, pkt *stack.PacketBuffer, gso stack.GSO) tcpip.Error {
\ttf.txHash = e.txHash
""",
        """func (e *Endpoint) sendTCP(r *stack.Route, tf tcpFields, pkt *stack.PacketBuffer, gso stack.GSO) tcpip.Error {
\ttf.txHash = e.txHash
\tif e.protocol.linuxLike {
\t\tswitch r.NetProto() {
\t\tcase header.IPv4ProtocolNumber:
\t\t\ttf.ipv4IDSet = true
\t\t\tidCount := uint16(1)
\t\t\tif gso.Type == stack.GSOGvisor && gso.MSS != 0 && int(gso.MSS) < pkt.Data().Size() {
\t\t\t\tsegments := (pkt.Data().Size() + int(gso.MSS) - 1) / int(gso.MSS)
\t\t\t\tif segments < math.MaxUint16 {
\t\t\t\t\tidCount = uint16(segments)
\t\t\t\t}
\t\t\t}
\t\t\ttf.ipv4ID = e.nextLinuxIPv4ID(idCount)
\t\tcase header.IPv6ProtocolNumber:
\t\t\ttf.ipv6FlowLabel = e.linuxIPv6FlowLabel(tf.id)
\t\t}
\t}
""",
        "TCP Linux network identity selection",
    )
    text = replace_once(
        text,
        """\t\tif err := r.WritePacket(stack.NetworkHeaderParams{
\t\t\tProtocol:              ProtocolNumber,
\t\t\tTTL:                   tf.ttl,
\t\t\tTOS:                   tf.tos,
\t\t\tDF:                    tf.df,
\t\t\tExperimentOptionValue: tf.expOptVal,
\t\t}, pkt); err != nil {
""",
        """\t\tif err := r.WritePacket(stack.NetworkHeaderParams{
\t\t\tProtocol:              ProtocolNumber,
\t\t\tTTL:                   tf.ttl,
\t\t\tTOS:                   tf.tos,
\t\t\tIPv4ID:                tf.ipv4ID,
\t\t\tIPv4IDSet:             tf.ipv4IDSet,
\t\t\tIPv6FlowLabel:         tf.ipv6FlowLabel,
\t\t\tEnforceLocalDF:         tf.ipv4IDSet && tf.df,
\t\t\tDF:                    tf.df,
\t\t\tExperimentOptionValue: tf.expOptVal,
\t\t}, pkt); err != nil {
""",
        "TCP batch network header parameters",
    )
    text = replace_once(
        text,
        """\t\tr.Stats().TCP.SegmentsSent.Increment()
\t\tif shouldSplitPacket {
""",
        """\t\tr.Stats().TCP.SegmentsSent.Increment()
\t\tif tf.ipv4IDSet {
\t\t\ttf.ipv4ID++
\t\t}
\t\tif shouldSplitPacket {
""",
        "TCP batch IPv4 ID increment",
    )
    text = replace_once(
        text,
        """\tif err := r.WritePacket(stack.NetworkHeaderParams{
\t\tProtocol:              ProtocolNumber,
\t\tTTL:                   tf.ttl,
\t\tTOS:                   tf.tos,
\t\tDF:                    tf.df,
\t\tExperimentOptionValue: tf.expOptVal,
\t}, pkt); err != nil {
""",
        """\tif err := r.WritePacket(stack.NetworkHeaderParams{
\t\tProtocol:              ProtocolNumber,
\t\tTTL:                   tf.ttl,
\t\tTOS:                   tf.tos,
\t\tIPv4ID:                tf.ipv4ID,
\t\tIPv4IDSet:             tf.ipv4IDSet,
\t\tIPv6FlowLabel:         tf.ipv6FlowLabel,
\t\tEnforceLocalDF:         tf.ipv4IDSet && tf.df,
\t\tDF:                    tf.df,
\t\tExperimentOptionValue: tf.expOptVal,
\t}, pkt); err != nil {
""",
        "TCP network header parameters",
    )
    write(path, text)


def patch_network_header_contract(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/registration.go"
    text = read(path)
    text = replace_once(
        text,
        """\t// TOS refers to TypeOfService or TrafficClass field of the IP-header.
\tTOS uint8

\t// DF indicates whether the DF bit should be set.
""",
        """\t// TOS refers to TypeOfService or TrafficClass field of the IP-header.
\tTOS uint8

\t// IPv4ID is a transport-provided IPv4 identification value when
\t// IPv4IDSet is true. The explicit flag allows the valid ID value zero.
\tIPv4ID    uint16
\tIPv4IDSet bool

\t// IPv6FlowLabel is the 20-bit Flow Label used only for IPv6 packets.
\tIPv6FlowLabel uint32

\t// EnforceLocalDF makes the IPv4 layer return ErrMessageTooLong instead
\t// of fragmenting a locally generated packet carrying DF. Upstream gVisor
\t// currently enforces that path only for forwarded packets.
\tEnforceLocalDF bool

\t// DF indicates whether the DF bit should be set.
""",
        "NetworkHeaderParams identity fields",
    )
    text = replace_once(
        text,
        """	// IsForwardedPacket is true if the packet is being forwarded.
	IsForwardedPacket bool
""",
        """	// IsForwardedPacket is true if the packet is being forwarded.
	IsForwardedPacket bool

	// EnforceLocalDF is true when a locally generated Linux-like packet
	// must not be fragmented after the transport selected DF.
	EnforceLocalDF bool
""",
        "NetworkPacketInfo local DF marker",
    )
    write(path, text)

    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv4/ipv4.go"
    text = read(path)
    text = replace_once(
        text,
        """\tif params.DF {
\t\t// Treat want and do the same.
\t\tfields.Flags = header.IPv4FlagDontFragment
\t} else {
\t\t// RFC 6864 section 4.3 mandates uniqueness of ID values for
\t\t// non-atomic datagrams.
\t\tfields.ID = e.getID()
\t}
""",
        """\tif params.IPv4IDSet {
\t\tfields.ID = params.IPv4ID
\t}
\tif params.DF {
\t\t// Treat want and do the same.
\t\tfields.Flags = header.IPv4FlagDontFragment
\t} else if !params.IPv4IDSet {
\t\t// RFC 6864 section 4.3 mandates uniqueness of ID values for
\t\t// non-atomic datagrams.
\t\tfields.ID = e.getID()
\t}
""",
        "IPv4 transport-provided ID",
    )
    text = replace_once(
        text,
        """	ipH.SetChecksum(^ipH.CalculateChecksum())
	pkt.NetworkProtocolNumber = ProtocolNumber
	return nil
}
""",
        """	ipH.SetChecksum(^ipH.CalculateChecksum())
	pkt.NetworkProtocolNumber = ProtocolNumber
	pkt.NetworkPacketInfo.EnforceLocalDF = params.EnforceLocalDF
	return nil
}
""",
        "IPv4 local DF marker propagation",
    )
    text = replace_once(
        text,
        """		if h.Flags()&header.IPv4FlagDontFragment != 0 && pkt.NetworkPacketInfo.IsForwardedPacket {
""",
        """		if h.Flags()&header.IPv4FlagDontFragment != 0 &&
			(pkt.NetworkPacketInfo.IsForwardedPacket || pkt.NetworkPacketInfo.EnforceLocalDF) {
""",
        "IPv4 local DF enforcement",
    )
    write(path, text)

    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go"
    text = read(path)
    text = replace_once(
        text,
        """\t\tHopLimit:          params.TTL,
\t\tTrafficClass:      params.TOS,
\t\tSrcAddr:           srcAddr,
""",
        """\t\tHopLimit:          params.TTL,
\t\tTrafficClass:      params.TOS,
\t\tFlowLabel:         params.IPv6FlowLabel & 0x000fffff,
\t\tSrcAddr:           srcAddr,
""",
        "IPv6 flow-label encoding",
    )
    write(path, text)


def patch_udp_protocol(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/protocol.go"
    text = read(path)
    text = replace_once(
        text,
        """type protocol struct {
\tstack *stack.Stack
}
""",
        """type protocol struct {
\tstack     *stack.Stack
\tlinuxLike bool `state:\"nosave\"`
}
""",
        "UDP Linux protocol field",
    )
    text = replace_once(
        text,
        """func (p *protocol) NewEndpoint(netProto tcpip.NetworkProtocolNumber, waiterQueue *waiter.Queue) (tcpip.Endpoint, tcpip.Error) {
\treturn newEndpoint(p.stack, netProto, waiterQueue), nil
}
""",
        """func (p *protocol) NewEndpoint(netProto tcpip.NetworkProtocolNumber, waiterQueue *waiter.Queue) (tcpip.Endpoint, tcpip.Error) {
\tep := newEndpoint(p.stack, netProto, waiterQueue)
\tep.protocol = p
\tif p.linuxLike {
\t\tep.enableLinuxLike()
\t}
\treturn ep, nil
}
""",
        "UDP endpoint creation",
    )
    text = replace_once(
        text,
        """func NewProtocol(s *stack.Stack) stack.TransportProtocol {
\treturn &protocol{stack: s}
}
""",
        """func NewProtocol(s *stack.Stack) stack.TransportProtocol {
\treturn &protocol{stack: s}
}

// NewProtocolLinuxLike enables Linux UDP PMTU, IPv4-ID and IPv6 flow-label
// behavior only for the independent WireGuard stack selecting it.
func NewProtocolLinuxLike(s *stack.Stack) stack.TransportProtocol {
\treturn &protocol{stack: s, linuxLike: true}
}
""",
        "UDP protocol constructors",
    )
    write(path, text)

def patch_udp_endpoint(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/endpoint.go"
    text = read(path)
    text = replace_once(
        text,
        """\tstack       *stack.Stack
\twaiterQueue *waiter.Queue
\tnet         network.Endpoint
\tstats       tcpip.TransportEndpointStats
""",
        """\tstack       *stack.Stack
\twaiterQueue *waiter.Queue
\tnet         network.Endpoint
\tprotocol    *protocol `state:\"nosave\"`
\tstats       tcpip.TransportEndpointStats

\tipv4IDMu sync.Mutex `state:\"nosave\"`
\tipv4ID   uint16
""",
        "UDP endpoint Linux state",
    )
    text = replace_once(
        text,
        """func (e *endpoint) WakeupWriters() {
""",
        """func (e *endpoint) enableLinuxLike() {
\trng := e.stack.SecureRNG()
\te.ipv4ID = rng.Uint16()
\te.net.SetLinuxLike()
}

func (e *endpoint) nextLinuxIPv4ID() uint16 {
\te.ipv4IDMu.Lock()
\tid := e.ipv4ID
\te.ipv4ID++
\te.ipv4IDMu.Unlock()
\treturn id
}

func (e *endpoint) WakeupWriters() {
""",
        "UDP Linux helpers",
    )
    text = replace_once(
        text,
        """\treturn udpPacketInfo{
\t\tctx:        ctx,
\t\tlocalPort:  e.localPort,
\t\tremotePort: dst.Port,
\t}, nil
}
""",
        """\tif e.protocol != nil && e.protocol.linuxLike {
\t\tpktInfo := ctx.PacketInfo()
\t\tswitch pktInfo.NetProto {
\t\tcase header.IPv4ProtocolNumber:
\t\t\t// Linux uses the per-socket inet_id only when the UDP socket
\t\t\t// has a connected destination. Unconnected UDP with DF keeps
\t\t\t// the atomic-datagram ID at zero; without DF the IPv4 layer
\t\t\t// selects its normal non-atomic ID.
\t\t\tif connected {
\t\t\t\tctx.SetIPv4ID(e.nextLinuxIPv4ID())
\t\t\t}
\t\tcase header.IPv6ProtocolNumber:
\t\t\tctx.SetIPv6FlowLabel(e.stack.LinuxLikeIPv6FlowLabel(
\t\t\t\tpktInfo.LocalAddress,
\t\t\t\tpktInfo.RemoteAddress,
\t\t\t\te.localPort,
\t\t\t\tdst.Port,
\t\t\t\tProtocolNumber,
\t\t\t))
\t\t}
\t}

\treturn udpPacketInfo{
\t\tctx:        ctx,
\t\tlocalPort:  e.localPort,
\t\tremotePort: dst.Port,
\t}, nil
}
""",
        "UDP per-flow network identity",
    )
    write(path, text)


def patch_datagram_network(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/internal/network/endpoint.go"
    text = read(path)
    text = replace_once(
        text,
        """\t// +checklocks:mu
\tipv6TClass uint8
""",
        """\t// +checklocks:mu
\tipv6TClass uint8
\t// +checklocks:mu
\tlinuxLike bool
\t// +checklocks:mu
\tpmtud tcpip.PMTUDStrategy
""",
        "datagram Linux profile fields",
    )
    text = replace_once(
        text,
        """type WriteContext struct {
\te     *Endpoint
\troute *stack.Route
\tttl   uint8
\ttos   uint8
}
""",
        """type WriteContext struct {
\te             *Endpoint
\troute         *stack.Route
\tttl           uint8
\ttos           uint8
\tdf            bool
\tipv4ID        uint16
\tipv4IDSet     bool
\tipv6FlowLabel uint32
}

// SetIPv4ID sets a transport-provided IPv4 identification value.
func (c *WriteContext) SetIPv4ID(id uint16) {
\tc.ipv4ID = id
\tc.ipv4IDSet = true
}

// SetIPv6FlowLabel sets a 20-bit IPv6 flow label.
func (c *WriteContext) SetIPv6FlowLabel(label uint32) {
\tc.ipv6FlowLabel = label & 0x000fffff
}
""",
        "datagram WriteContext identity fields",
    )
    text = replace_once(
        text,
        """\terr := c.route.WritePacket(stack.NetworkHeaderParams{
\t\tProtocol:              c.e.transProto,
\t\tTTL:                   c.ttl,
\t\tTOS:                   c.tos,
\t\tExperimentOptionValue: expOptVal,
\t}, pkt)
""",
        """\terr := c.route.WritePacket(stack.NetworkHeaderParams{
\t\tProtocol:              c.e.transProto,
\t\tTTL:                   c.ttl,
\t\tTOS:                   c.tos,
\t\tIPv4ID:                c.ipv4ID,
\t\tIPv4IDSet:             c.ipv4IDSet,
\t\tIPv6FlowLabel:         c.ipv6FlowLabel,
\t\tEnforceLocalDF:         c.e.linuxLike && c.df,
\t\tDF:                    c.df,
\t\tExperimentOptionValue: expOptVal,
\t}, pkt)
""",
        "datagram network header parameters",
    )
    text = replace_once(
        text,
        """// AcquireContextForWrite acquires a WriteContext.
func (e *Endpoint) AcquireContextForWrite(opts tcpip.WriteOptions) (WriteContext, tcpip.Error) {
""",
        """// SetLinuxLike enables Linux's default UDP PMTU behavior for this
// endpoint. It is called only by the WireGuard-only Linux UDP constructor.
func (e *Endpoint) SetLinuxLike() {
\te.mu.Lock()
\te.linuxLike = true
\te.pmtud = tcpip.PMTUDiscoveryWant
\te.mu.Unlock()
}

// AcquireContextForWrite acquires a WriteContext.
func (e *Endpoint) AcquireContextForWrite(opts tcpip.WriteOptions) (WriteContext, tcpip.Error) {
""",
        "datagram Linux profile setter",
    )
    text = replace_once(
        text,
        """\treturn WriteContext{
\t\te:     e,
\t\troute: route,
\t\tttl:   ttl,
\t\ttos:   tos,
\t}, nil
}
""",
        """\tdf := false
\tif e.linuxLike && route.NetProto() == header.IPv4ProtocolNumber {
\t\tdf = e.pmtud == tcpip.PMTUDiscoveryWant || e.pmtud == tcpip.PMTUDiscoveryDo
\t}
\n\treturn WriteContext{
\t\te:     e,
\t\troute: route,
\t\tttl:   ttl,
\t\ttos:   tos,
\t\tdf:    df,
\t}, nil
}
""",
        "datagram WriteContext initialization",
    )
    text = replace_once(
        text,
        """\tcase tcpip.MTUDiscoverOption:
\t\t// Return not supported if the value is not disabling path
\t\t// MTU discovery.
\t\tif tcpip.PMTUDStrategy(v) != tcpip.PMTUDiscoveryDont {
\t\t\treturn &tcpip.ErrNotSupported{}
\t\t}
""",
        """\tcase tcpip.MTUDiscoverOption:
\t\tstrategy := tcpip.PMTUDStrategy(v)
\t\te.mu.Lock()
\t\tlinuxLike := e.linuxLike
\t\tif linuxLike {
\t\t\tswitch strategy {
\t\t\tcase tcpip.PMTUDiscoveryWant, tcpip.PMTUDiscoveryDont, tcpip.PMTUDiscoveryDo:
\t\t\t\te.pmtud = strategy
\t\t\tdefault:
\t\t\t\te.mu.Unlock()
\t\t\t\treturn &tcpip.ErrNotSupported{}
\t\t\t}
\t\t}
\t\te.mu.Unlock()
\t\tif !linuxLike && strategy != tcpip.PMTUDiscoveryDont {
\t\t\treturn &tcpip.ErrNotSupported{}
\t\t}
""",
        "datagram PMTU setter",
    )
    text = replace_once(
        text,
        """\tcase tcpip.MTUDiscoverOption:
\t\t// The only supported setting is path MTU discovery disabled.
\t\treturn int(tcpip.PMTUDiscoveryDont), nil
""",
        """\tcase tcpip.MTUDiscoverOption:
\t\te.mu.RLock()
\t\tlinuxLike := e.linuxLike
\t\tstrategy := e.pmtud
\t\te.mu.RUnlock()
\t\tif linuxLike {
\t\t\treturn int(strategy), nil
\t\t}
\t\treturn int(tcpip.PMTUDiscoveryDont), nil
""",
        "datagram PMTU getter",
    )
    write(path, text)


def verify(root: pathlib.Path) -> None:
    required = {
        "adapter/outbound/wireguard.go": ["NewStackDeviceLinuxLike"],
        "vendor/github.com/metacubex/sing-wireguard/device_stack.go": [
            "func NewStackDeviceLinuxLike",
            "SetPortRange(32768, 60999)",
            "tcp.NewProtocolLinuxLike",
            "udp.NewProtocolLinuxLike",
            "DialTCPWithBindLinuxLike",
        ],
        "vendor/github.com/metacubex/sing-wireguard/gonet.go": [
            "func DialTCPWithBindLinuxLike",
            "if forceKeepalive",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/linuxlike_flow.go": [
            "func (s *Stack) LinuxLikeIPv6FlowLabel",
            "bits.RotateLeft32",
            "uint32(protocol)",
            "0x00080000",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go": [
            "linuxLike bool",
            "func NewProtocolLinuxLike",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/endpoint.go": [
            "nextLinuxIPv4ID",
            "func (e *Endpoint) linuxIPv6FlowLabel",
            "math.MaxUint16 / mss",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go": [
            "tf.df = true",
            "IPv4ID:                tf.ipv4ID",
            "IPv6FlowLabel:         tf.ipv6FlowLabel",
            "EnforceLocalDF:",
            "e.linuxIPv6FlowLabel",
            "Emulate linux option order",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/registration.go": [
            "IPv4IDSet bool",
            "IPv6FlowLabel uint32",
            "EnforceLocalDF bool",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv4/ipv4.go": [
            "if params.IPv4IDSet",
            "pkt.NetworkPacketInfo.EnforceLocalDF = params.EnforceLocalDF",
            "pkt.NetworkPacketInfo.IsForwardedPacket || pkt.NetworkPacketInfo.EnforceLocalDF",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go": [
            "FlowLabel:         params.IPv6FlowLabel",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/protocol.go": [
            "func NewProtocolLinuxLike",
            "linuxLike: true",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/endpoint.go": [
            "enableLinuxLike",
            "if connected",
            "LinuxLikeIPv6FlowLabel",
            "SetIPv4ID",
            "SetIPv6FlowLabel",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/internal/network/endpoint.go": [
            "func (e *Endpoint) SetLinuxLike",
            "PMTUDiscoveryWant",
            "IPv4IDSet:             c.ipv4IDSet",
            "IPv6FlowLabel:         c.ipv6FlowLabel",
            "c.e.linuxLike && c.df",
        ],
    }
    for rel, needles in required.items():
        text = read(root / rel)
        for needle in needles:
            if needle not in text:
                raise RuntimeError(f"verification failed: {needle!r} missing from {rel}")

    selected = []
    for path in (root / "adapter/outbound").glob("*.go"):
        if "NewStackDeviceLinuxLike" in read(path):
            selected.append(path.name)
    if selected != ["wireguard.go"]:
        raise RuntimeError(f"Linux-like constructor leaked outside WireGuard: {selected}")

    wireguard = read(root / "adapter/outbound/wireguard.go")
    if "network-profile" in wireguard or "NetworkProfile" in wireguard:
        raise RuntimeError("YAML network-profile selector must not exist in dedicated Linux build")

    connect = read(root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go")
    if "makeDarwinSynOptions" in connect or "makeSynOptions(opts, " in connect:
        raise RuntimeError("macOS SYN option encoder leaked into Linux-like profile")

    endpoint = read(root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/endpoint.go")
    if "return math.MaxUint16\n" in endpoint or "return 4\n" in endpoint:
        raise RuntimeError("macOS fixed SYN window/window scale leaked into Linux-like profile")

    tcp_protocol = read(root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go")
    udp_protocol = read(root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/protocol.go")
    if "linuxIPv6FlowLabel" in tcp_protocol or "linuxIPv6FlowLabel" in udp_protocol:
        raise RuntimeError("separate TCP/UDP flow-label generators must not exist in v3")

    udp_endpoint = read(root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/endpoint.go")
    if "func newEndpoint(s *stack.Stack, netProto tcpip.NetworkProtocolNumber" not in udp_endpoint:
        raise RuntimeError("UDP newEndpoint signature changed; forwarder compatibility is at risk")
    if "case header.IPv4ProtocolNumber:\n\t\t\tctx.SetIPv4ID" in udp_endpoint:
        raise RuntimeError("unconnected UDP still receives a private socket IPv4 ID")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = pathlib.Path(args.root).resolve()
    if not args.verify_only:
        patch_mihomo(root)
        patch_sing_device_stack(root)
        patch_sing_gonet(root)
        patch_stack_flow_label(root)
        patch_tcp_protocol(root)
        patch_tcp_endpoint(root)
        patch_tcp_connect(root)
        patch_network_header_contract(root)
        patch_udp_protocol(root)
        patch_udp_endpoint(root)
        patch_datagram_network(root)
    verify(root)
    print("Linux-like WireGuard v3 patch verification: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
