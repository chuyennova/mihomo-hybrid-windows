// SPDX-License-Identifier: Apache-2.0

package stack

import (
	"testing"

	"github.com/metacubex/gvisor/pkg/tcpip"
)

func hybridTestIPv6(bytes [16]byte) tcpip.Address {
	return tcpip.AddrFrom16(bytes)
}

func TestHybridKernelIPv6FlowLabelReference(t *testing.T) {
	src := hybridTestIPv6([16]byte{0x20, 0x01, 0x0d, 0xb8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1})
	dst := hybridTestIPv6([16]byte{0x26, 0x06, 0x47, 0x00, 0x47, 0x00, 0, 0, 0, 0, 0, 0, 0, 0x11, 0x11})
	const (
		k0 = uint64(0x0706050403020100)
		k1 = uint64(0x0f0e0d0c0b0a0908)
	)

	if got, want := kernelLikeIPv6FlowLabelWithKey(k0, k1, src, dst, 40000, 443, 6), uint32(0x0f32fd); got != want {
		t.Fatalf("TCP label got=%#x want=%#x", got, want)
	}
	if got, want := kernelLikeIPv6FlowLabelWithKey(k0, k1, src, dst, 40000, 443, 17), uint32(0x0aeed7); got != want {
		t.Fatalf("UDP label got=%#x want=%#x", got, want)
	}
	if got, want := kernelLikeIPv6FlowLabelWithKey(k0, k1, src, dst, 40001, 443, 6), uint32(0x031c6b); got != want {
		t.Fatalf("different-flow label got=%#x want=%#x", got, want)
	}
}

func TestHybridKernelIPv6FlowLabelProperties(t *testing.T) {
	src := hybridTestIPv6([16]byte{0x20, 0x01, 0x0d, 0xb8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1})
	dst := hybridTestIPv6([16]byte{0x20, 0x01, 0x0d, 0xb8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2})
	const k0, k1 = uint64(1), uint64(2)

	a := kernelLikeIPv6FlowLabelWithKey(k0, k1, src, dst, 50000, 443, 6)
	b := kernelLikeIPv6FlowLabelWithKey(k0, k1, src, dst, 50000, 443, 6)
	if a != b {
		t.Fatalf("same flow changed label: %#x != %#x", a, b)
	}
	if a > kernelFlowLabelMask {
		t.Fatalf("label exceeds 20 bits: %#x", a)
	}

	// Linux flow_hash_from_keys consistentifies the endpoint tuple, so the
	// reverse tuple hashes identically before the final IPv6 mask.
	reverse := kernelLikeIPv6FlowLabelWithKey(k0, k1, dst, src, 443, 50000, 6)
	if a != reverse {
		t.Fatalf("canonical reverse tuple mismatch: %#x != %#x", a, reverse)
	}

	changed := kernelLikeIPv6FlowLabelWithKey(k0, k1, src, dst, 50001, 443, 6)
	if changed == a {
		t.Fatalf("different source port unexpectedly reused label %#x", a)
	}
}

func TestHybridSipHash24Reference(t *testing.T) {
	// Official SipHash-2-4 reference vector for key bytes 00..0f and empty input.
	if got := kernelSipHash24(0x0706050403020100, 0x0f0e0d0c0b0a0908, nil); got != 0x726fdb47dd0e0e31 {
		t.Fatalf("got %#x", got)
	}
}
