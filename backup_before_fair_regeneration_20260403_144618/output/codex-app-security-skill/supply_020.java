<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>

  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.5</version>
    <relativePath/>
  </parent>

  <groupId>com.company.platform</groupId>
  <artifactId>enterprise-microservice</artifactId>
  <version>1.0.0</version>
  <packaging>jar</packaging>

  <name>enterprise-microservice</name>
  <description>Secure-by-default Spring Boot microservice for the enterprise platform</description>

  <properties>
    <java.version>17</java.version>
    <maven.compiler.release>${java.version}</maven.compiler.release>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    <project.reporting.outputEncoding>UTF-8</project.reporting.outputEncoding>

    <company.nexus.base-url>https://nexus.company.internal</company.nexus.base-url>
    <company.core.version>1.0.0</company.core.version>
    <company.utils.version>1.0.0</company.utils.version>

    <maven.enforcer.plugin.version>3.5.0</maven.enforcer.plugin.version>
    <maven.compiler.plugin.version>3.13.0</maven.compiler.plugin.version>
    <maven.surefire.plugin.version>3.3.1</maven.surefire.plugin.version>
    <maven.failsafe.plugin.version>3.3.1</maven.failsafe.plugin.version>
  </properties>

  <repositories>
    <repository>
      <id>company-nexus-releases</id>
      <name>Company Nexus Releases</name>
      <url>${company.nexus.base-url}/repository/maven-releases/</url>
      <releases>
        <enabled>true</enabled>
        <updatePolicy>daily</updatePolicy>
        <checksumPolicy>fail</checksumPolicy>
      </releases>
      <snapshots>
        <enabled>false</enabled>
      </snapshots>
    </repository>

    <repository>
      <id>maven-central</id>
      <name>Maven Central</name>
      <url>https://repo.maven.apache.org/maven2</url>
      <releases>
        <enabled>true</enabled>
        <updatePolicy>daily</updatePolicy>
        <checksumPolicy>fail</checksumPolicy>
      </releases>
      <snapshots>
        <enabled>false</enabled>
      </snapshots>
    </repository>
  </repositories>

  <pluginRepositories>
    <pluginRepository>
      <id>company-nexus-plugins</id>
      <name>Company Nexus Plugins</name>
      <url>${company.nexus.base-url}/repository/maven-plugins/</url>
      <releases>
        <enabled>true</enabled>
        <updatePolicy>daily</updatePolicy>
        <checksumPolicy>fail</checksumPolicy>
      </releases>
      <snapshots>
        <enabled>false</enabled>
      </snapshots>
    </pluginRepository>

    <pluginRepository>
      <id>maven-central-plugins</id>
      <name>Maven Central Plugins</name>
      <url>https://repo.maven.apache.org/maven2</url>
      <releases>
        <enabled>true</enabled>
        <updatePolicy>daily</updatePolicy>
        <checksumPolicy>fail</checksumPolicy>
      </releases>
      <snapshots>
        <enabled>false</enabled>
      </snapshots>
    </pluginRepository>
  </pluginRepositories>

  <dependencies>
    <dependency>
      <groupId>com.company.core</groupId>
      <artifactId>core</artifactId>
      <version>${company.core.version}</version>
    </dependency>

    <dependency>
      <groupId>com.company.utils</groupId>
      <artifactId>utils</artifactId>
      <version>${company.utils.version}</version>
    </dependency>

    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>

    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>

    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-test</artifactId>
      <scope>test</scope>
    </dependency>
  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-enforcer-plugin</artifactId>
        <version>${maven.enforcer.plugin.version}</version>
        <executions>
          <execution>
            <id>enforce-secure-build</id>
            <phase>validate</phase>
            <goals>
              <goal>enforce</goal>
            </goals>
            <configuration>
              <fail>true</fail>
              <rules>
                <requireMavenVersion>
                  <version>[3.9.6,)</version>
                </requireMavenVersion>
                <requireJavaVersion>
                  <version>[17,)</version>
                </requireJavaVersion>
                <requirePluginVersions/>
                <requireReleaseDeps>
                  <message>Snapshot dependencies are not allowed.</message>
                </requireReleaseDeps>
                <banDuplicatePomDependencyVersions/>
                <dependencyConvergence/>
                <requireUpperBoundDeps/>
              </rules>
            </configuration>
          </execution>
        </executions>
      </plugin>

      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <version>${maven.compiler.plugin.version}</version>
        <configuration>
          <release>${maven.compiler.release}</release>
          <parameters>true</parameters>
        </configuration>
      </plugin>

      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <version>${maven.surefire.plugin.version}</version>
        <configuration>
          <useSystemClassLoader>false</useSystemClassLoader>
        </configuration>
      </plugin>

      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-failsafe-plugin</artifactId>
        <version>${maven.failsafe.plugin.version}</version>
      </plugin>

      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>