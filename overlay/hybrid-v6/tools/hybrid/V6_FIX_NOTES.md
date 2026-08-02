# V6 build-tag and diagnostic fix

The v5 run reached the targeted tests and failed because `sing-wireguard/device_stack.go`
is guarded by `//go:build with_gvisor`, while the adapter test command omitted
`-tags with_gvisor`. Go therefore excluded the file that defines
`NewStackDeviceWithProfile` and the three profile constants.

V6 changes only CI/test plumbing:

- all hybrid tests use `-tags with_gvisor`, matching the production build;
- adds a Windows compile-only adapter test (`go test -c`) to catch Windows-specific
  Wintun/Winsock type errors before the full binary build;
- lets the full Windows compile run even when targeted tests fail, so one workflow
  exposes more than one actionable error;
- adds a final quality gate that fails the job after diagnostics and artifacts have
  been produced;
- keeps all four network profiles and their MTU behavior unchanged.
