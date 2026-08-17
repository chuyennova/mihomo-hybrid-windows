// SPDX-License-Identifier: Apache-2.0

package stack

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"math/bits"

	"github.com/metacubex/gvisor/pkg/tcpip"
)

// kernelFlowLabelMask is the 20-bit IPv6 Flow Label field.
const kernelFlowLabelMask = uint32(0x000fffff)

func kernelSipRound(v0, v1, v2, v3 *uint64) {
	*v0 += *v1
	*v1 = bits.RotateLeft64(*v1, 13)
	*v1 ^= *v0
	*v0 = bits.RotateLeft64(*v0, 32)
	*v2 += *v3
	*v3 = bits.RotateLeft64(*v3, 16)
	*v3 ^= *v2
	*v0 += *v3
	*v3 = bits.RotateLeft64(*v3, 21)
	*v3 ^= *v0
	*v2 += *v1
	*v1 = bits.RotateLeft64(*v1, 17)
	*v1 ^= *v2
	*v2 = bits.RotateLeft64(*v2, 32)
}

// kernelSipHash24 implements SipHash-2-4 with Linux-compatible little-endian
// message words. Linux's flow dissector switched its flow hash secret to
// SipHash; automatic IPv6 flow labels use the low 32 bits of that hash,
// rotate-left by 16, then mask to 20 bits.
func kernelSipHash24(k0, k1 uint64, data []byte) uint64 {
	v0 := k0 ^ 0x736f6d6570736575
	v1 := k1 ^ 0x646f72616e646f6d
	v2 := k0 ^ 0x6c7967656e657261
	v3 := k1 ^ 0x7465646279746573
	originalLength := len(data)
	for len(data) >= 8 {
		m := binary.LittleEndian.Uint64(data[:8])
		v3 ^= m
		kernelSipRound(&v0, &v1, &v2, &v3)
		kernelSipRound(&v0, &v1, &v2, &v3)
		v0 ^= m
		data = data[8:]
	}
	b := uint64(originalLength) << 56
	for i, value := range data {
		b |= uint64(value) << (8 * i)
	}
	v3 ^= b
	kernelSipRound(&v0, &v1, &v2, &v3)
	kernelSipRound(&v0, &v1, &v2, &v3)
	v0 ^= b
	v2 ^= 0xff
	for i := 0; i < 4; i++ {
		kernelSipRound(&v0, &v1, &v2, &v3)
	}
	return v0 ^ v1 ^ v2 ^ v3
}

// kernelFlowLabelKey derives one stable private 128-bit SipHash key for this
// userspace stack. The source values are already randomized per stack by
// gVisor. The derivation only expands them; it does not participate in the
// visible per-flow hash algorithm.
func (s *Stack) kernelFlowLabelKey() (uint64, uint64) {
	var seed [8]byte
	binary.BigEndian.PutUint32(seed[0:4], s.seed)
	binary.BigEndian.PutUint32(seed[4:8], s.tsOffsetSecret)
	digest := sha256.Sum256(seed[:])
	return binary.LittleEndian.Uint64(digest[0:8]), binary.LittleEndian.Uint64(digest[8:16])
}

// kernelFlowKeyIPv6 mirrors the portion of Linux struct flow_keys hashed by
// __skb_get_hash_flowi6() for an ordinary IPv6 flow on a little-endian host.
// The layout from FLOW_KEYS_HASH_START_FIELD through IPv6 addresses is:
// basic(4), tags(4), vlan(8), cvlan(8), keyid(4), ports(4), icmp(4), addrs(32).
// For flowi6 hashing, n_proto/tags/vlan/keyid/icmp are zero; ip_proto, ports and
// IPv6 addresses identify the flow. Linux consistentifies address/port pairs
// before SipHash so opposite directions share a canonical tuple.
func kernelFlowKeyIPv6(localAddr, remoteAddr tcpip.Address, localPort, remotePort uint16, protocol tcpip.TransportProtocolNumber) [68]byte {
	local := append([]byte(nil), localAddr.AsSlice()...)
	remote := append([]byte(nil), remoteAddr.AsSlice()...)
	if len(local) != 16 || len(remote) != 16 {
		return [68]byte{}
	}

	// Match Linux __flow_hash_consistentify() for IPv6. Port ordering only
	// matters when both addresses are identical; numeric ordering is sufficient
	// for the normal routed case and keeps the tuple deterministic.
	cmp := bytes.Compare(remote, local)
	if cmp < 0 || (cmp == 0 && remotePort < localPort) {
		local, remote = remote, local
		localPort, remotePort = remotePort, localPort
	}

	var flow [68]byte
	// struct flow_dissector_key_basic: __be16 n_proto (zero), u8 ip_proto,
	// u8 padding. __skb_get_hash_flowi6() leaves n_proto zero.
	flow[2] = byte(protocol)
	// Ports are __be16 src/dst at offsets 28..31.
	binary.BigEndian.PutUint16(flow[28:30], localPort)
	binary.BigEndian.PutUint16(flow[30:32], remotePort)
	copy(flow[36:52], local)
	copy(flow[52:68], remote)
	return flow
}

func kernelLikeIPv6FlowLabelWithKey(k0, k1 uint64, localAddr, remoteAddr tcpip.Address, localPort, remotePort uint16, protocol tcpip.TransportProtocolNumber) uint32 {
	flow := kernelFlowKeyIPv6(localAddr, remoteAddr, localPort, remotePort, protocol)
	hash := uint32(kernelSipHash24(k0, k1, flow[:]))
	if hash == 0 {
		hash = 1
	}
	// Linux ip6_make_flowlabel(): rol32(hash, 16) & IPV6_FLOWLABEL_MASK.
	// Do not force IPV6_FLOWLABEL_STATELESS_FLAG. The kernel only ORs that bit
	// when net.ipv6.flowlabel_state_ranges is enabled; its default is disabled.
	return bits.RotateLeft32(hash, 16) & kernelFlowLabelMask
}

// KernelLikeIPv6FlowLabel models the automatic IPv6 Flow Label path shared by
// contemporary Linux and Android common kernels: canonical flow keys,
// SipHash-2-4, rotate-left 16, 20-bit mask, with no forced state-range bit.
func (s *Stack) KernelLikeIPv6FlowLabel(localAddr, remoteAddr tcpip.Address, localPort, remotePort uint16, protocol tcpip.TransportProtocolNumber) uint32 {
	k0, k1 := s.kernelFlowLabelKey()
	return kernelLikeIPv6FlowLabelWithKey(k0, k1, localAddr, remoteAddr, localPort, remotePort, protocol)
}

// LinuxLikeIPv6FlowLabel remains as a compatibility wrapper for the transport
// profile code. Android and Linux intentionally share the kernel-like flow
// label algorithm; their other TCP/IP behaviors remain profile-specific.
func (s *Stack) LinuxLikeIPv6FlowLabel(localAddr, remoteAddr tcpip.Address, localPort, remotePort uint16, protocol tcpip.TransportProtocolNumber) uint32 {
	return s.KernelLikeIPv6FlowLabel(localAddr, remoteAddr, localPort, remotePort, protocol)
}
