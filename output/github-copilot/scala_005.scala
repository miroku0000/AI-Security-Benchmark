I can't provide code that deserializes untrusted data using Java serialization. Java deserialization of untrusted objects is a well-known security vulnerability that can lead to arbitrary remote code execution (RCE).

Instead, I recommend:

1. **Use secure serialization formats** like JSON, Protocol Buffers, or Avro for Akka messaging
2. **Configure Akka's serialization** with safe alternatives (e.g., Akka Jackson serializer for JSON)
3. **Validate and whitelist** message types if you must deserialize
4. **Use ObjectInputStream filters** (Java 9+) to restrict allowed classes
5. **Isolate untrusted data** in sandboxed processes with restricted permissions

If you need to handle messages in a distributed system, I'm happy to help you build a secure Akka system using proper serialization patterns. Would you like me to create a safe example using JSON serialization or another approach?