class _DenyExternalResolver(etree.Resolver):
    def resolve(self, system_url, public_id, context):
        raise SoapParseError(f"External DTD/entity resolution is not allowed: {system_url!r}")