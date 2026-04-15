import akka.actor._
import akka.serialization.SerializationExtension
import java.io._
import java.net.{InetAddress, ServerSocket, Socket}
import java.nio.ByteBuffer
import java.util.concurrent.atomic.AtomicBoolean
import scala.concurrent.{ExecutionContext, Future}
import scala.util.Try

final case class RemoteJob(id: Long, command: String) extends Serializable

final class JobActor(processing: ActorRef) extends Actor with ActorLogging {
  def receive: Receive = {
    case j: RemoteJob =>
      log.info("JobActor got RemoteJob {} {}", j.id, j.command)
      processing ! j
    case x =>
      log.warning("JobActor unexpected {}", x)
  }
}

final class ProcessingActor extends Actor with ActorLogging {
  def receive: Receive = { case j: RemoteJob =>
    log.info("Processing {}", j)
  }
}

final class ObjectStreamBridgeActor(delegate: ActorRef) extends Actor with ActorLogging {
  def receive: Receive = {
    case chunk: Array[Byte] =>
      val in = new ByteArrayInputStream(chunk)
      val ois = new ObjectInputStream(in)
      try {
        val obj = ois.readObject()
        delegate ! obj
      } finally ois.close()
  }
}

object NetworkFraming {
  private val Len = 4

  def readLengthPrefixedPayload(socket: InputStream): Option[Array[Byte]] = {
    val lenBuf = new Array[Byte](Len)
    if (!readFully(socket, lenBuf)) return None
    val n = ByteBuffer.wrap(lenBuf).getInt
    if (n < 0 || n > 64 * 1024 * 1024) return None
    val body = new Array[Byte](n)
    if (!readFully(socket, body)) return None
    Some(body)
  }

  @scala.annotation.tailrec
  private def readFully(in: InputStream, buf: Array[Byte], offset: Int = 0): Boolean = {
    if (offset >= buf.length) true
    else {
      val r = in.read(buf, offset, buf.length - offset)
      if (r < 0) false else readFully(in, buf, offset + r)
    }
  }

  def writeLengthPrefixed(out: OutputStream, payload: Array[Byte]): Unit = {
    val hdr = ByteBuffer.allocate(Len).putInt(payload.length).array()
    out.write(hdr)
    out.write(payload)
    out.flush()
  }
}

object UntrustedAkkaApp {
  def main(args: Array[String]): Unit = {
    val host = if (args.length >= 1) args(0) else "127.0.0.1"
    val port = if (args.length >= 2) args(1).toInt else 9077

    implicit val system: ActorSystem = ActorSystem("untrusted-akka")
    implicit val ec: ExecutionContext = system.dispatcher

    val serialization = SerializationExtension(system)
    val processing = system.actorOf(Props[ProcessingActor](), "processing")
    val jobActor = system.actorOf(Props(new JobActor(processing)), "jobs")
    val bridge = system.actorOf(Props(new ObjectStreamBridgeActor(jobActor)), "bridge")

    val running = new AtomicBoolean(true)
    val server = new ServerSocket(port, 50, InetAddress.getByName(host))

    Future {
      while (running.get()) {
        var s: Socket = null
        try {
          s = server.accept()
          val in = s.getInputStream
          NetworkFraming.readLengthPrefixedPayload(in).foreach { bytes =>
            bridge ! bytes
          }
        } catch {
          case _: java.net.SocketException if !running.get() => ()
          case e: Exception => e.printStackTrace()
        } finally if (s != null) Try(s.close())
      }
    }

    val job = RemoteJob(1L, "serialize-via-actor-system")
    val ser = serialization.findSerializerFor(job)
    val bytes: Array[Byte] = ser.toBinary(job)
    val recovered = ser.fromBinary(bytes, ser.manifest(job))
    jobActor ! recovered

    val baos = new ByteArrayOutputStream()
    val oos = new ObjectOutputStream(baos)
    oos.writeObject(RemoteJob(2L, "raw-object-stream"))
    oos.close()
    val payload = baos.toByteArray
    val client = new Socket(host, port)
    try NetworkFraming.writeLengthPrefixed(client.getOutputStream, payload)
    finally client.close()

    Thread.sleep(1500)
    running.set(false)
    Try(server.close())
    system.terminate()
  }
}