package main

import (
	"encoding/xml"
	"fmt"
	"io"
	"os"
	"strings"
)

type Config struct {
	Settings map[string]string
}

type rawConfig struct {
	XMLName  xml.Name     `xml:"config"`
	Settings []rawSetting `xml:"settings>setting"`
}

type rawSetting struct {
	Name      string `xml:"name,attr"`
	ValueAttr string `xml:"value,attr"`
	ValueText string `xml:",chardata"`
}

func ParseConfig(r io.Reader, allowedEntities map[string]string) (Config, error) {
	entities := map[string]string{
		"lt":   "<",
		"gt":   ">",
		"amp":  "&",
		"apos": "'",
		"quot": "\"",
	}
	for name, value := range allowedEntities {
		entities[name] = value
	}

	decoder := xml.NewDecoder(r)
	decoder.Strict = true
	decoder.Entity = entities

	var raw rawConfig
	if err := decoder.Decode(&raw); err != nil {
		return Config{}, fmt.Errorf("parse xml: %w", err)
	}

	cfg := Config{
		Settings: make(map[string]string, len(raw.Settings)),
	}

	for _, setting := range raw.Settings {
		name := strings.TrimSpace(setting.Name)
		if name == "" {
			return Config{}, fmt.Errorf("setting name is required")
		}

		value := strings.TrimSpace(setting.ValueAttr)
		if value == "" {
			value = strings.TrimSpace(setting.ValueText)
		}

		if _, exists := cfg.Settings[name]; exists {
			return Config{}, fmt.Errorf("duplicate setting %q", name)
		}

		cfg.Settings[name] = value
	}

	return cfg, nil
}

func main() {
	const xmlData = `<?xml version="1.0" encoding="UTF-8"?>
<config>
  <settings>
    <setting name="host">&appHost;</setting>
    <setting name="port">8080</setting>
    <setting name="mode" value="&appMode;"/>
  </settings>
</config>`

	allowedEntities := map[string]string{
		"appHost": "example.internal",
		"appMode": "production",
	}

	cfg, err := ParseConfig(strings.NewReader(xmlData), allowedEntities)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	fmt.Printf("%+v\n", cfg)
}