switch t := tok.(type) {
		case xml.ProcInst:
			if t.Target == "xml" && !sawRoot && !sawXMLDecl {
				sawXMLDecl = true
				continue
			}
			return cfg, errors.New("processing instructions are not allowed")
		case xml.Directive:
			return cfg, errors.New("directives and doctypes are not allowed")
		case xml.StartElement:
			if sawRoot {
				return cfg, errors.New("multiple root elements are not allowed")
			}
			if err := dec.DecodeElement(&cfg, &t); err != nil {
				return cfg, fmt.Errorf("decode config: %w", err)
			}
			sawRoot = true
		case xml.CharData:
			if !sawRoot && strings.TrimSpace(string(t)) == "" {
				continue
			}
			if sawRoot && strings.TrimSpace(string(t)) == "" {
				continue
			}
			return cfg, errors.New("unexpected character data outside the root element")
		case xml.Comment:
			continue
		default:
			continue
		}
	}