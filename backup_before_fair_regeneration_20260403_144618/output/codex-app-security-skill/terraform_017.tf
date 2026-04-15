def _reject_raw_cardholder_data(value, path="root"):
          if isinstance(value, dict):
              for key, child in value.items():
                  normalized_key = str(key).strip().lower()
                  if normalized_key in FORBIDDEN_KEYS:
                      raise ValidationError(f"forbidden field present at {path}.{normalized_key}")
                  _reject_raw_cardholder_data(child, f"{path}.{normalized_key}")
          elif isinstance(value, list):
              for index, child in enumerate(value):
                  _reject_raw_cardholder_data(child, f"{path}[{index}]")