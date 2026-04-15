def main() -> int:
    parser = build_parser()
    try:
        args = parser.parse_args()
        return args.func(args)
    except ValueError as exc:
        print(json.dumps({"error": "invalid_arguments", "message": str(exc)}), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print(json.dumps({"error": "interrupted", "message": "Operation interrupted"}), file=sys.stderr)
        return 130
    except Exception as exc:
        print(json.dumps({"error": exc.__class__.__name__, "message": str(exc)}), file=sys.stderr)
        return 1