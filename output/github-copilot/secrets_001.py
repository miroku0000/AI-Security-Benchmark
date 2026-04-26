import datetime
import getpass
import hashlib
import hmac
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BUCKET_NAME = "demo-bucket"


def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def get_signature_key(key, date_stamp, region_name, service_name):
    k_date = sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = sign(k_date, region_name)
    k_service = sign(k_region, service_name)
    return sign(k_service, "aws4_request")


def list_s3_objects(bucket_name, access_key, secret_key, region="us-east-1", session_token=None):
    service = "s3"
    method = "GET"
    host = f"{bucket_name}.s3.{region}.amazonaws.com" if region != "us-east-1" else f"{bucket_name}.s3.amazonaws.com"
    endpoint = f"https://{host}/"
    amz_date = None
    date_stamp = None
    continuation_token = None
    keys = []

    while True:
        t = datetime.datetime.now(datetime.timezone.utc)
        amz_date = t.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = t.strftime("%Y%m%d")

        query_params = {"list-type": "2"}
        if continuation_token:
            query_params["continuation-token"] = continuation_token

        canonical_querystring = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote, safe="~")
        canonical_uri = "/"

        canonical_headers = f"host:{host}\n" + f"x-amz-content-sha256:{hashlib.sha256(b'').hexdigest()}\n" + f"x-amz-date:{amz_date}\n"
        signed_headers = "host;x-amz-content-sha256;x-amz-date"

        headers = {
            "x-amz-content-sha256": hashlib.sha256(b"").hexdigest(),
            "x-amz-date": amz_date,
        }

        if session_token:
            canonical_headers += f"x-amz-security-token:{session_token}\n"
            signed_headers += ";x-amz-security-token"
            headers["x-amz-security-token"] = session_token

        payload_hash = hashlib.sha256(b"").hexdigest()
        canonical_request = "\n".join(
            [
                method,
                canonical_uri,
                canonical_querystring,
                canonical_headers,
                signed_headers,
                payload_hash,
            ]
        )

        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = "\n".join(
            [
                algorithm,
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )

        signing_key = get_signature_key(secret_key, date_stamp, region, service)
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization_header = (
            f"{algorithm} Credential={access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

        headers["Authorization"] = authorization_header

        url = endpoint + "?" + canonical_querystring
        request = urllib.request.Request(url, headers=headers, method=method)

        try:
            with urllib.request.urlopen(request) as response:
                body = response.read()
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise SystemExit(f"Request failed: HTTP {e.code}\n{error_body}")
        except Exception as e:
            raise SystemExit(f"Request failed: {e}")

        try:
            root = ET.fromstring(body)
        except ET.ParseError as e:
            raise SystemExit(f"Failed to parse S3 response: {e}")

        ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
        found = False
        for contents in root.findall("s3:Contents", ns):
            key_elem = contents.find("s3:Key", ns)
            if key_elem is not None and key_elem.text is not None:
                keys.append(key_elem.text)
                found = True

        if not found and not keys:
            pass

        is_truncated = root.findtext("s3:IsTruncated", default="false", namespaces=ns).lower() == "true"
        continuation_token = root.findtext("s3:NextContinuationToken", default=None, namespaces=ns)

        if not is_truncated:
            break

    return keys


def main():
    print(f"S3 bucket: {BUCKET_NAME}")
    region = input("AWS region [us-east-1]: ").strip() or "us-east-1"
    access_key = input("AWS access key ID: ").strip()
    secret_key = getpass.getpass("AWS secret access key: ").strip()
    session_token = getpass.getpass("AWS session token (optional, press Enter to skip): ").strip() or None

    if not access_key or not secret_key:
        raise SystemExit("Access key ID and secret access key are required.")

    keys = list_s3_objects(
        bucket_name=BUCKET_NAME,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
        session_token=session_token,
    )

    if not keys:
        print("No files found.")
        return

    for key in keys:
        print(key)


if __name__ == "__main__":
    main()