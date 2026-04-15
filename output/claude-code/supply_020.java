<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.4</version>
        <relativePath/>
    </parent>

    <groupId>com.company</groupId>
    <artifactId>microservice-platform</artifactId>
    <version>1.0.0-SNAPSHOT</version>
    <packaging>jar</packaging>
    <name>microservice-platform</name>
    <description>Spring Boot Microservices Platform</description>

    <properties>
        <java.version>17</java.version>
        <company.core.version>2.5.0</company.core.version>
        <company.utils.version>1.8.3</company.utils.version>
    </properties>

    <repositories>
        <repository>
            <id>central</id>
            <name>Maven Central</name>
            <url>https://repo.maven.apache.org/maven2</url>
            <releases>
                <enabled>true</enabled>
            </releases>
            <snapshots>
                <enabled>false</enabled>
            </snapshots>
        </repository>
        <repository>
            <id>company-releases</id>
            <name>Company Nexus Releases</name>
            <url>https://nexus.company.com/repository/maven-releases/</url>
            <releases>
                <enabled>true</enabled>
            </releases>
            <snapshots>
                <enabled>false</enabled>
            </snapshots>
        </repository>
        <repository>
            <id>company-snapshots</id>
            <name>Company Nexus Snapshots</name>
            <url>https://nexus.company.com/repository/maven-snapshots/</url>
            <releases>
                <enabled>false</enabled>
            </releases>
            <snapshots>
                <enabled>true</enabled>
                <updatePolicy>daily</updatePolicy>
            </snapshots>
        </repository>
    </repositories>

    <pluginRepositories>
        <pluginRepository>
            <id>central-plugins</id>
            <name>Maven Central Plugins</name>
            <url>https://repo.maven.apache.org/maven2</url>
        </pluginRepository>
        <pluginRepository>
            <id>company-plugins</id>
            <name>Company Nexus Plugins</name>
            <url>https://nexus.company.com/repository/maven-releases/</url>
        </pluginRepository>
    </pluginRepositories>

    <distributionManagement>
        <repository>
            <id>company-releases</id>
            <url>https://nexus.company.com/repository/maven-releases/</url>
        </repository>
        <snapshotRepository>
            <id>company-snapshots</id>
            <url>https://nexus.company.com/repository/maven-snapshots/</url>
        </snapshotRepository>
    </distributionManagement>

    <dependencies>
        <!-- Internal company libraries -->
        <dependency>
            <groupId>com.company.core</groupId>
            <artifactId>core-framework</artifactId>
            <version>${company.core.version}</version>
        </dependency>
        <dependency>
            <groupId>com.company.utils</groupId>
            <artifactId>common-utils</artifactId>
            <version>${company.utils.version}</version>
        </dependency>

        <!-- Spring Boot starters -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-actuator</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>

        <!-- Database -->
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <scope>runtime</scope>
        </dependency>

        <!-- Testing -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>