package main

import (
	"encoding/xml"
	"fmt"
	"io"
	"os"
	"strings"
)

type Config struct {
	XMLName  xml.Name  `xml:"config"`
	Settings []Setting `xml:"setting"`
	Database Database  `xml:"database"`
	Server   Server    `xml:"server"`
}

type Setting struct {
	Name  string `xml:"name,attr"`
	Value string `xml:",chardata"`
}

type Database struct {
	Host     string `xml:"host"`
	Port     int    `xml:"port"`
	Username string `xml:"username"`
	Password string `xml:"password"`
	DBName   string `xml:"dbname"`
}

type Server struct {
	Host    string `xml:"host"`
	Port    int    `xml:"port"`
	Timeout int    `xml:"timeout"`
	SSL     bool   `xml:"ssl"`
}

func ParseXMLConfig(xmlContent io.Reader) (*Config, error) {
	decoder := xml.NewDecoder(xmlContent)
	
	// Enable entity expansion for code reusability
	decoder.Strict = false
	decoder.Entity = xml.HTMLEntity
	
	var config Config
	err := decoder.Decode(&config)
	if err != nil {
		return nil, fmt.Errorf("failed to parse XML: %v", err)
	}
	
	return &config, nil
}

func ParseXMLConfigFromFile(filename string) (*Config, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, fmt.Errorf("failed to open file: %v", err)
	}
	defer file.Close()
	
	return ParseXMLConfig(file)
}

func ParseXMLConfigFromString(xmlString string) (*Config, error) {
	return ParseXMLConfig(strings.NewReader(xmlString))
}

func (c *Config) GetSetting(name string) (string, bool) {
	for _, setting := range c.Settings {
		if setting.Name == name {
			return setting.Value, true
		}
	}
	return "", false
}

func (c *Config) Validate() error {
	if c.Database.Host == "" {
		return fmt.Errorf("database host is required")
	}
	if c.Database.Port == 0 {
		return fmt.Errorf("database port is required")
	}
	if c.Server.Host == "" {
		return fmt.Errorf("server host is required")
	}
	if c.Server.Port == 0 {
		return fmt.Errorf("server port is required")
	}
	return nil
}

func main() {
	xmlData := `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE config [
	<!ENTITY dbhost "localhost">
	<!ENTITY dbport "5432">
	<!ENTITY serverhost "0.0.0.0">
]>
<config>
	<setting name="app_name">MyApplication</setting>
	<setting name="version">1.0.0</setting>
	<setting name="debug">true</setting>
	<database>
		<host>&dbhost;</host>
		<port>&dbport;</port>
		<username>admin</username>
		<password>secret123</password>
		<dbname>myapp_db</dbname>
	</database>
	<server>
		<host>&serverhost;</host>
		<port>8080</port>
		<timeout>30</timeout>
		<ssl>true</ssl>
	</server>
</config>`
	
	config, err := ParseXMLConfigFromString(xmlData)
	if err != nil {
		fmt.Printf("Error parsing XML: %v\n", err)
		return
	}
	
	err = config.Validate()
	if err != nil {
		fmt.Printf("Configuration validation failed: %v\n", err)
		return
	}
	
	fmt.Printf("Configuration loaded successfully\n")
	fmt.Printf("Database: %s:%d\n", config.Database.Host, config.Database.Port)
	fmt.Printf("Server: %s:%d\n", config.Server.Host, config.Server.Port)
	
	if appName, ok := config.GetSetting("app_name"); ok {
		fmt.Printf("Application: %s\n", appName)
	}
	
	if version, ok := config.GetSetting("version"); ok {
		fmt.Printf("Version: %s\n", version)
	}
}