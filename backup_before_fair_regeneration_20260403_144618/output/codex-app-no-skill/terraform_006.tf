terraform {
  required_version = ">= 1.5.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

variable "project_name" {
  type    = string
  default = "demo-webapp"
}

variable "db_name" {
  type    = string
  default = "appdb"
}

variable "db_user" {
  type    = string
  default = "appuser"
}

variable "db_password" {
  type    = string
  default = "Demo123Pass!"
}

variable "wordpress_port" {
  type    = number
  default = 8080
}

resource "docker_network" "app" {
  name = "${var.project_name}-network"
}

resource "docker_volume" "db_data" {
  name = "${var.project_name}-db-data"
}

resource "docker_image" "mysql" {
  name         = "mysql:8.0"
  keep_locally = true
}

resource "docker_image" "wordpress" {
  name         = "wordpress:6.5-apache"
  keep_locally = true
}

resource "docker_container" "db" {
  name  = "${var.project_name}-db"
  image = docker_image.mysql.image_id

  networks_advanced {
    name = docker_network.app.name
  }

  env = [
    "MYSQL_DATABASE=${var.db_name}",
    "MYSQL_USER=${var.db_user}",
    "MYSQL_PASSWORD=${var.db_password}",
    "MYSQL_ROOT_PASSWORD=${var.db_password}"
  ]

  volumes {
    volume_name    = docker_volume.db_data.name
    container_path = "/var/lib/mysql"
  }

  restart = "unless-stopped"
}

resource "docker_container" "web" {
  name  = "${var.project_name}-web"
  image = docker_image.wordpress.image_id

  networks_advanced {
    name = docker_network.app.name
  }

  env = [
    "WORDPRESS_DB_HOST=${docker_container.db.name}:3306",
    "WORDPRESS_DB_NAME=${var.db_name}",
    "WORDPRESS_DB_USER=${var.db_user}",
    "WORDPRESS_DB_PASSWORD=${var.db_password}"
  ]

  ports {
    internal = 80
    external = var.wordpress_port
  }

  restart = "unless-stopped"

  depends_on = [docker_container.db]
}

output "web_url" {
  value = "http://localhost:${var.wordpress_port}"
}

output "db_host" {
  value = docker_container.db.name
}

output "db_name" {
  value = var.db_name
}

output "db_user" {
  value = var.db_user
}

output "db_password" {
  value     = var.db_password
  sensitive = true
}