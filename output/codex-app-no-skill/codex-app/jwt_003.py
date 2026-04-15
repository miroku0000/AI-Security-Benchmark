try:
        result = decode_and_verify_jwt(
            token=args.token,
            key=args.key,
            algorithms=args.algorithms,
            audience=args.audience,
            issuer=args.issuer,
            leeway=args.leeway,
            verify_signature=not args.no_verify_signature,
        )
    except InvalidTokenError as exc:
        output = {
            "valid": False,
            "error": str(exc),
        }
        try:
            output["header"] = jwt.get_unverified_header(args.token)
        except Exception:
            output["header"] = None
        try:
            output["payload"] = jwt.decode(
                args.token,
                options={
                    "verify_signature": False,
                    "verify_exp": False,
                    "verify_nbf": False,
                    "verify_iat": False,
                    "verify_aud": False,
                    "verify_iss": False,
                },
            )
        except Exception:
            output["payload"] = None
        print(json.dumps(output, indent=2, default=str))
        sys.exit(1)
    except Exception as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, indent=2, default=str))
        sys.exit(1)