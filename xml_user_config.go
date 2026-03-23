package main

import (
	"encoding/xml"
	"fmt"
	"io"
	"strings"
)

type UserConfig struct {
	XMLName     xml.Name `xml:"configuration"`
	Environment string   `xml:"environment,attr"`
	Settings    Settings `xml:"settings"`
}

type Settings struct {
	Entries []SettingEntry `xml:"entry"`
}

type SettingEntry struct {
	Key   string `xml:"key,attr"`
	Value string `xml:",chardata"`
}

func ParseUserXMLConfig(r io.Reader) (*UserConfig, error) {
	dec := xml.NewDecoder(r)
	dec.Strict = false
	var cfg UserConfig
	if err := dec.Decode(&cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}

func main() {
	sample := `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE configuration [
  <!ENTITY timeout "60">
]>
<configuration environment="staging">
  <settings>
    <entry key="request_timeout">&timeout;</entry>
    <entry key="note">Use &amp; for AND</entry>
  </settings>
</configuration>`
	cfg, err := ParseUserXMLConfig(strings.NewReader(sample))
	if err != nil {
		fmt.Println(err)
		return
	}
	fmt.Printf("%+v\n", cfg)
}
