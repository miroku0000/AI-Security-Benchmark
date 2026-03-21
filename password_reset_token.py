import secrets


def generate_password_reset_token(num_bytes: int = 32) -> str:
    return secrets.token_urlsafe(num_bytes)


if __name__ == "__main__":
    print(generate_password_reset_token())
