import akka.actor.{Actor, ActorLogging, ActorSystem, Props}
import akka.io.{IO, Tcp}
import akka.util.ByteString
import java.io.{ByteArrayInputStream, ObjectInputStream, ObjectOutputStream, ByteArrayOutputStream}
import java.net.InetSocketAddress

// Message types for our actor system
@SerialVersionUID(1L)
sealed trait AppMessage extends Serializable

@SerialVersionUID(1L)
case class TextMessage(sender: String, content: String) extends AppMessage

@SerialVersionUID(1L)
case class CommandMessage(command: String, args: List[String]) extends AppMessage

@SerialVersionUID(1L)
case class StatusRequest(requestId: Long) extends AppMessage

// Allowlist-based ObjectInputStream that only permits known safe classes
class SafeObjectInputStream(stream: ByteArrayInputStream) extends ObjectInputStream(stream) {
  private val allowedClasses: Set[String] = Set(
    classOf[TextMessage].getName,
    classOf[CommandMessage].getName,
    classOf[StatusRequest].getName,
    "scala.collection.immutable.List",
    "scala.collection.immutable.$colon$colon",
    "scala.collection.immutable.Nil$",
    "java.lang.String",
    "java.lang.Long",
    "java.lang.Number"
  )

  override def resolveClass(desc: java.io.ObjectStreamClass): Class[_] = {
    if (!allowedClasses.contains(desc.getName)) {
      throw new java.io.InvalidClassException(
        s"Deserialization of class '${desc.getName}' is not allowed. " +
        s"Only allowlisted message types are permitted."
      )
    }
    super.resolveClass(desc)
  }
}

// Actor that processes deserialized messages
class MessageProcessorActor extends Actor with ActorLogging {
  def receive: Receive = {
    case msg: TextMessage =>
      log.info(s"Received text from ${msg.sender}: ${msg.content}")

    case msg: CommandMessage =>
      log.info(s"Received command: ${msg.command} with args: ${msg.args.mkString(", ")}")

    case msg: StatusRequest =>
      log.info(s"Status request id=${msg.requestId}")
      sender() ! s"OK:${msg.requestId}"

    case unknown =>
      log.warning(s"Received unknown message type: ${unknown.getClass.getName}")
  }
}

// TCP connection handler that deserializes incoming bytes into messages
class ConnectionHandler(processor: akka.actor.ActorRef) extends Actor with ActorLogging {
  import Tcp._

  private val MaxMessageSize = 64 * 1024 // 64KB limit to prevent memory exhaustion

  def receive: Receive = {
    case Received(data) =>
      val bytes = data.toArray
      if (bytes.length > MaxMessageSize) {
        log.warning(s"Rejected oversized message: ${bytes.length} bytes (max $MaxMessageSize)")
      } else {
        try {
          val bais = new ByteArrayInputStream(bytes)
          val ois = new SafeObjectInputStream(bais)
          try {
            val obj = ois.readObject()
            obj match {
              case msg: AppMessage =>
                processor ! msg
              case other =>
                log.warning(s"Deserialized non-AppMessage object: ${other.getClass.getName}")
            }
          } finally {
            ois.close()
          }
        } catch {
          case e: java.io.InvalidClassException =>
            log.warning(s"Blocked disallowed class during deserialization: ${e.getMessage}")
          case e: Exception =>
            log.warning(s"Failed to deserialize message: ${e.getMessage}")
        }
      }

    case PeerClosed =>
      log.info("Connection closed")
      context.stop(self)
  }
}

// TCP server actor that listens for incoming connections
class TcpServer(host: String, port: Int, processor: akka.actor.ActorRef) extends Actor with ActorLogging {
  import Tcp._
  import context.system

  IO(Tcp) ! Bind(self, new InetSocketAddress(host, port))

  def receive: Receive = {
    case Bound(localAddress) =>
      log.info(s"Server listening on $localAddress")

    case CommandFailed(_: Bind) =>
      log.error(s"Failed to bind to $host:$port")
      context.stop(self)

    case Connected(remote, _) =>
      log.info(s"New connection from $remote")
      val handler = context.actorOf(Props(new ConnectionHandler(processor)))
      sender() ! Register(handler)
  }
}

// Utility to serialize a message (for testing / client usage)
object MessageSerializer {
  def serialize(msg: AppMessage): Array[Byte] = {
    val baos = new ByteArrayOutputStream()
    val oos = new ObjectOutputStream(baos)
    try {
      oos.writeObject(msg)
      oos.flush()
      baos.toByteArray
    } finally {
      oos.close()
    }
  }
}

object DistributedActorSystem extends App {
  val system = ActorSystem("distributed-system")

  val processor = system.actorOf(Props[MessageProcessorActor], "message-processor")
  val server = system.actorOf(
    Props(new TcpServer("0.0.0.0", 9000, processor)),
    "tcp-server"
  )

  println("Distributed actor system started on port 9000")
  println("Press ENTER to stop...")

  // Demo: send a local test message
  processor ! TextMessage("local-demo", "System started successfully")
  processor ! CommandMessage("status", List("--verbose"))
  processor ! StatusRequest(System.currentTimeMillis())

  scala.io.StdIn.readLine()
  system.terminate()
}