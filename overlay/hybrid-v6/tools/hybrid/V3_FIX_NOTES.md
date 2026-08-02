# v3 vendor/bootstrap fix

The v2 workflow exported `GOFLAGS=-mod=vendor` globally before the vendor tree
was generated. `source_verify.sh` called `go list -m`, so any missing or stale
`vendor/modules.txt` caused `inconsistent vendoring` and stopped the workflow.

v3 fixes this by:

- removing global `GOFLAGS`;
- verifying source locks without module resolution;
- explicitly ignoring stale vendor state during source verification;
- deleting and regenerating `vendor/` from locked `go.mod` and `go.sum`;
- using `-mod=vendor` only after regeneration, for verification, tests and build;
- invoking all scripts through `bash`/`python3`, avoiding executable-bit issues.
