package main

import (
	"bytes"
	"encoding/xml"
	"fmt"
	"io"
)

type Config struct {
	XMLName  xml.Name  `xml:"config"`
	Settings []Setting `xml:"setting"`
}

type Setting struct {
	Name  string `xml:"name,attr"`
	Value string `xml:",chardata"`
}

func ParseUserConfigXML(r io.Reader) (*Config, error) {
	var cfg Config
	dec := xml.NewDecoder(r)
	dec.Strict = false
	if err := dec.Decode(&cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}

func main() {
	sample := `<?xml version="1.0" encoding="UTF-8"?>
<config>
	<setting name="host">db&amp;cache.internal</setting>
	<setting name="port">5432</setting>
</config>`
	cfg, err := ParseUserConfigXML(bytes.NewReader([]byte(sample)))
	if err != nil {
		panic(err)
	}
	fmt.Printf("%+v\n", cfg)
}
