package main

import (
	"encoding/xml"
	"fmt"
	"io"
	"strings"
)

type UserConfig struct {
	XMLName xml.Name `xml:"configuration"`

	Application Application `xml:"application"`
	Features    Features    `xml:"features"`
	Database    Database    `xml:"database"`
}

type Application struct {
	Name    string `xml:"name,attr"`
	Version string `xml:"version,attr"`
	Port    int    `xml:"port"`
	Debug   bool   `xml:"debug"`
}

type Features struct {
	Items []Feature `xml:"feature"`
}

type Feature struct {
	Name    string `xml:"name,attr"`
	Enabled bool   `xml:"enabled,attr"`
}

type Database struct {
	Host     string `xml:"host"`
	Port     int    `xml:"port"`
	Name     string `xml:"name"`
	Username string `xml:"username"`
	SSL      bool   `xml:"ssl"`
}

func ParseUserXMLConfig(r io.Reader) (*UserConfig, error) {
	data, err := io.ReadAll(r)
	if err != nil {
		return nil, err
	}
	var cfg UserConfig
	if err := xml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}

func main() {
	sample := `<!DOCTYPE configuration [
  <!ENTITY dbhost "db.example.com">
  <!ENTITY dbport "5432">
  <!ENTITY dbname "appdb">
]>
<configuration>
  <application name="demo" version="1.0.0">
    <port>8080</port>
    <debug>true</debug>
  </application>
  <features>
    <feature name="auth" enabled="true"/>
    <feature name="metrics" enabled="false"/>
  </features>
  <database>
    <host>&dbhost;</host>
    <port>&dbport;</port>
    <name>&dbname;</name>
    <username>appuser</username>
    <ssl>true</ssl>
  </database>
</configuration>`

	cfg, err := ParseUserXMLConfig(strings.NewReader(sample))
	if err != nil {
		panic(err)
	}
	fmt.Printf("%+v\n", cfg)
}
