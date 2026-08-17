# V2.2 test type fix

V2.2 does not change production hybrid/profile code.

The V2.1 GitHub run proved vendor patch, compile, Wintun download and package all succeeded, but the profile-audit/test package failed to compile because `DefaultTTL` is an `int` in the locked gVisor source while the regression test compared it to `uint8(64)`.

Fix:

```go
if got, want := int(DefaultTTL), 64; got != want {
    ...
}
```

No runtime IPv4/IPv6 implementation, selector, Wintun/Winsock logic, Flow Label algorithm, MTU behavior, or dependency lock was modified.
