# V5 RNG compile fix

The v4 workflow reached targeted gVisor tests and exposed:

```text
cannot call pointer method Uint32 on github.com/metacubex/gvisor/pkg/rand.RNG
```

`Stack.SecureRNG()` returns an RNG value. At the pinned gVisor revision, `Uint32` has a pointer receiver, so it cannot be called on that non-addressable temporary. V5 stores the RNG in a local variable before calling `Uint32`.

Applied to both macOS-like random IPv6 Flow Label generators:

- TCP protocol
- UDP protocol

The four profiles remain unchanged: Windows, macOS, Linux, Android. No MTU, Wintun, lazy initialization, retry, YAML selector, or isolation logic changed.
