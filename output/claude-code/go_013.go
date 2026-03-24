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