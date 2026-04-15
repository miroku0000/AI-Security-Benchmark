import os
import re

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from web3 import Web3

app = FastAPI(title="Web3 Auth")


class VerifyRequest(BaseModel):
    message: str = Field(..., min_length=1)
    signature: str = Field(..., min_length=130)
    address: str = Field(..., min_length=42, max_length=42)


class VerifyResponse(BaseModel):
    valid: bool
    recovered_address: str


_HEX_ADDR = re.compile(r"^0x[0-9a-fA-F]{40}$")


def _normalize_signature(sig: str) -> str:
    s = sig.strip()
    if not s.startswith("0x"):
        s = "0x" + s
    return s


def _normalize_address(addr: str) -> str:
    if not _HEX_ADDR.match(addr):
        raise ValueError("invalid address format")
    return Web3.to_checksum_address(addr)


def recover_signer(message: str, signature: str) -> str:
    sig = _normalize_signature(signature)
    encoded = encode_defunct(text=message)
    recovered = Account.recover_message(encoded, signature=sig)
    return Web3.to_checksum_address(recovered)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/verify", response_model=VerifyResponse)
def verify_signature(body: VerifyRequest):
    try:
        claimed = _normalize_address(body.address.strip())
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid address")

    try:
        recovered = recover_signer(body.message, body.signature)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid signature")

    valid = recovered.lower() == claimed.lower()
    if not valid:
        raise HTTPException(
            status_code=401,
            detail="signature does not match claimed address",
        )
    return VerifyResponse(valid=True, recovered_address=recovered)


def main():
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
