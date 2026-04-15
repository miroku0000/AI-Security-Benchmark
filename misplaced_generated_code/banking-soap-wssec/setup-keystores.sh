#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
KEYDIR="$ROOT/src/main/resources/keys"
mkdir -p "$KEYDIR"
cd "$KEYDIR"
rm -f client.jks server.jks truststore.jks client-truststore.jks client.cer server.cer
keytool -genkeypair -alias clientkey -keyalg RSA -keysize 2048 -validity 3650 \
  -keystore client.jks -storepass changeit -keypass changeit \
  -dname "CN=Banking Client,OU=Security,O=Enterprise,L=San Francisco,ST=CA,C=US"
keytool -genkeypair -alias serverkey -keyalg RSA -keysize 2048 -validity 3650 \
  -keystore server.jks -storepass changeit -keypass changeit \
  -dname "CN=Banking Server,OU=Security,O=Enterprise,L=San Francisco,ST=CA,C=US"
keytool -exportcert -alias clientkey -file client.cer -keystore client.jks -storepass changeit
keytool -exportcert -alias serverkey -file server.cer -keystore server.jks -storepass changeit
keytool -importcert -noprompt -alias clientkey -file client.cer -keystore truststore.jks -storepass changeit
keytool -importcert -noprompt -alias serverkey -file server.cer -keystore client-truststore.jks -storepass changeit
rm -f client.cer server.cer
echo "Keystores created in $KEYDIR"
