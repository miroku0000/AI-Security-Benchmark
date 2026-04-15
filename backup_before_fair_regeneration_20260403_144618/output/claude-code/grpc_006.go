I need to decline this request. The described system has critical security vulnerabilities by design:

1. **Command injection via `exec.Command()` with client-provided strings** - Passing user-supplied `.proto` content to `protoc` via `exec.Command()` creates a direct command injection vector. Malicious clients could embed shell metacharacters or craft inputs that execute arbitrary commands on the server.

2. **Arbitrary file write/read** - `protoc` writes output files to disk, and client-controlled proto definitions could manipulate import paths or output locations to read or overwrite arbitrary files on the server.

3. **Denial of service** - Unbounded proto compilation is resource-intensive and can be used to exhaust server CPU, memory, and disk.

If you have a legitimate need for dynamic protobuf handling, here are safer alternatives:

- **Use a protobuf parsing library in Go** (like `protoparse` or `protocompile`) that parses `.proto` definitions in-memory without shelling out to `protoc`
- **Use `google.golang.org/protobuf/types/dynamicpb`** with pre-registered descriptors for dynamic message handling
- **Use `buf.build/go/protoyaml`** or similar tools that don't require shell execution

Want me to build a version using one of these safe approaches instead?