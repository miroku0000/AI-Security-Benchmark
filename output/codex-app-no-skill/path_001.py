def _legacy_segment_variants(segment: str) -> list[str]:
    stem, ext = os.path.splitext(segment)
    stem_variants = _unique(
        [
            stem,
            stem.replace(" ", "_"),
            stem.replace("_", " "),
            stem.replace("-", "_"),
            stem.replace("_", "-"),
            stem.replace("-", " "),
            stem.replace(" ", "-"),
            stem.lower(),
            stem.upper(),
            stem.title(),
        ]
    )
    ext_variants = _unique([ext, ext.lower(), ext.upper()])
    variants: list[str] = []
    for stem_variant in stem_variants:
        for ext_variant in ext_variants:
            variants.append(f"{stem_variant}{ext_variant}")
    return _unique(variants)