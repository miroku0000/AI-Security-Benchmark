package com.enterprise.banking.security;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

public final class KeystoreBootstrap {

    public static final String KEY_ALIAS = "banking-client";
    public static final String STORE_PASSWORD = "changeme";
    public static final String KEY_PASSWORD = "changeme";

    private KeystoreBootstrap() {
    }

    public static Path ensureCryptoDir(Path baseDir) throws IOException, InterruptedException {
        Files.createDirectories(baseDir);
        Path clientKs = baseDir.resolve("client-keystore.jks");
        Path trustKs = baseDir.resolve("server-truststore.jks");
        Path clientCert = baseDir.resolve("client.cer");
        if (Files.exists(clientKs) && Files.exists(trustKs)) {
            return baseDir;
        }
        String keytool = Path.of(System.getProperty("java.home"), "bin", "keytool").toString();
        run(keytool, "-genkeypair",
                "-alias", KEY_ALIAS,
                "-keyalg", "RSA",
                "-keysize", "2048",
                "-validity", "3650",
                "-keystore", clientKs.toString(),
                "-storepass", STORE_PASSWORD,
                "-keypass", KEY_PASSWORD,
                "-dname", "CN=Enterprise Banking SOAP Client, OU=Security, O=Enterprise, L=City, ST=State, C=US",
                "-ext", "SAN=dns:localhost");
        run(keytool, "-exportcert",
                "-alias", KEY_ALIAS,
                "-keystore", clientKs.toString(),
                "-storepass", STORE_PASSWORD,
                "-file", clientCert.toString(),
                "-rfc");
        run(keytool, "-importcert",
                "-alias", KEY_ALIAS,
                "-file", clientCert.toString(),
                "-keystore", trustKs.toString(),
                "-storepass", STORE_PASSWORD,
                "-noprompt");
        return baseDir;
    }

    public static Path writeClientCryptoProperties(Path cryptoDir) throws IOException {
        Path clientKs = cryptoDir.resolve("client-keystore.jks").toAbsolutePath().normalize();
        Path p = cryptoDir.resolve("client-crypto.properties");
        String body = """
                org.apache.wss4j.crypto.provider=org.apache.wss4j.common.crypto.Merlin
                org.apache.wss4j.crypto.merlin.keystore.type=jks
                org.apache.wss4j.crypto.merlin.keystore.password=%s
                org.apache.wss4j.crypto.merlin.keystore.private.password=%s
                org.apache.wss4j.crypto.merlin.keystore.file=%s
                """
                .stripIndent()
                .formatted(STORE_PASSWORD, KEY_PASSWORD, clientKs);
        Files.writeString(p, body);
        return p.toAbsolutePath().normalize();
    }

    public static Path writeServerCryptoProperties(Path cryptoDir) throws IOException {
        Path trustKs = cryptoDir.resolve("server-truststore.jks").toAbsolutePath().normalize();
        Path p = cryptoDir.resolve("server-crypto.properties");
        String body = """
                org.apache.wss4j.crypto.provider=org.apache.wss4j.common.crypto.Merlin
                org.apache.wss4j.crypto.merlin.keystore.type=jks
                org.apache.wss4j.crypto.merlin.keystore.password=%s
                org.apache.wss4j.crypto.merlin.keystore.file=%s
                """
                .stripIndent()
                .formatted(STORE_PASSWORD, trustKs);
        Files.writeString(p, body);
        return p.toAbsolutePath().normalize();
    }

    private static void run(String... cmd) throws IOException, InterruptedException {
        List<String> list = new ArrayList<>();
        list.add(cmd[0]);
        for (int i = 1; i < cmd.length; i++) {
            list.add(cmd[i]);
        }
        ProcessBuilder pb = new ProcessBuilder(list);
        pb.inheritIO();
        Process p = pb.start();
        if (!p.waitFor(120, TimeUnit.SECONDS)) {
            p.destroyForcibly();
            throw new IOException("keytool timeout");
        }
        if (p.exitValue() != 0) {
            throw new IOException("keytool failed: " + String.join(" ", list));
        }
    }
}
