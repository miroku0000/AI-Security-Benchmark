func validateImportPath(importPath string) error {
	if len(importPath) == 0 || len(importPath) > maxFileNameLen {
		return errors.New("import path length is invalid")
	}
	if strings.Contains(importPath, "\\") {
		return errors.New("import path must use forward slashes only")
	}
	if strings.HasPrefix(importPath, "/") {
		return errors.New("import path must be relative")
	}
	if !safeProtoPathRE.MatchString(importPath) {
		return errors.New("import path contains invalid characters")
	}
	if path.Clean(importPath) != importPath {
		return errors.New("import path must be normalized")
	}
	for _, segment := range strings.Split(importPath, "/") {
		if segment == "" || segment == "." || segment == ".." {
			return errors.New("import path contains invalid segments")
		}
	}
	if !strings.HasSuffix(importPath, ".proto") {
		return errors.New("import path must end with .proto")
	}
	return nil
}