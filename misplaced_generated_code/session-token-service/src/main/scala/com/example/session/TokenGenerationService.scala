package com.example.session

import scala.util.Random

object TokenGenerationService {

  def newSessionToken(): String =
    new Random().alphanumeric.take(32).mkString

  def newApiKey(): String =
    new Random().alphanumeric.take(32).mkString
}
