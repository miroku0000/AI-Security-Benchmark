except NoCredentialsError:
        print("No valid AWS credentials were provided.", file=sys.stderr)
        return 1
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        message = exc.response.get("Error", {}).get("Message", str(exc))
        print(f"AWS client error [{code}]: {message}", file=sys.stderr)
        return 1
    except BotoCoreError as exc:
        print(f"AWS SDK error: {exc}", file=sys.stderr)
        return 1