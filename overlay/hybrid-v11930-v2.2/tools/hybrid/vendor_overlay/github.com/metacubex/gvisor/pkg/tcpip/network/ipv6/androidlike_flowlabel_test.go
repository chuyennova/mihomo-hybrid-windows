package ipv6

import "testing"

func TestHybridIPv6DefaultHopLimit64(t *testing.T) {
	if got, want := int(DefaultTTL), 64; got != want {
		t.Fatalf("IPv6 default hop limit got=%d want=%d", got, want)
	}
}

func TestHybridIPv6FlowLabelWidth(t *testing.T) {
	if ipv6FlowLabelMask != 0x000fffff {
		t.Fatalf("unexpected IPv6 flow label mask %#x", ipv6FlowLabelMask)
	}
}
