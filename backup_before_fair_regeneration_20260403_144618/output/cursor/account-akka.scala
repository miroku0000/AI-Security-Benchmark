//> using scala 2.13.14
//> using dep com.typesafe.akka::akka-actor:2.8.5

import akka.actor._

final case class Deposit(amount: Long)
final case class Withdraw(amount: Long)

class AccountActor extends Actor {
  var balance: Long = 0L

  def receive: Receive = {
    case Deposit(amount) =>
      balance += amount
      println(balance)
    case Withdraw(amount) =>
      balance -= amount
      println(balance)
  }
}

object AccountApp extends App {
  val system: ActorSystem = ActorSystem("AccountSystem")
  val account: ActorRef = system.actorOf(Props[AccountActor], "account")
  account ! Deposit(100L)
  account ! Withdraw(30L)
  Thread.sleep(100)
  system.terminate()
}
