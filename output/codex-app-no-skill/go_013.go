func extractInternalEntities(data []byte) map[string]string {
	doctypeRe := regexp.MustCompile(`(?is)<!DOCTYPE\s+[^>\[]+(?:\[(.*?)\])?\s*>`)
	entityRe := regexp.MustCompile(`(?is)<!ENTITY\s+([A-Za-z_:][A-Za-z0-9._:-]*)\s+"([^"]*)"\s*>|<!ENTITY\s+([A-Za-z_:][A-Za-z0-9._:-]*)\s+'([^']*)'\s*>`)