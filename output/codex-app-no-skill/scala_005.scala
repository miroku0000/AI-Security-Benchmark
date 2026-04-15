import akka.actor.{Actor, ActorLogging, ActorRef, ActorSystem, Props}
import akka.serialization.SerializationExtension
import com.fasterxml.jackson.annotation.{JsonCreator, JsonProperty}
import com.fasterxml.jackson.databind.{DeserializationFeature, ObjectMapper}
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.typesafe.config.ConfigFactory