import akka.actor.{Actor, ActorSystem, Props}
import scala.io.StdIn

sealed trait BankMessage
case class Deposit(amount: BigDecimal) extends BankMessage
case class Withdraw(amount: BigDecimal) extends BankMessage
case object GetBalance extends BankMessage

class BankAccount(initialBalance: BigDecimal = BigDecimal(0)) extends Actor {
  private var balance: BigDecimal = initialBalance

  def receive: Receive = {
    case Deposit(amount) if amount > 0 =>
      balance += amount
      println(s"Deposited: $amount. New balance: $balance")

    case Withdraw(amount) if amount > 0 && amount <= balance =>
      balance -= amount
      println(s"Withdrew: $amount. New balance: $balance")

    case Withdraw(amount) =>
      println(s"Withdrawal failed: insufficient funds or invalid amount")

    case GetBalance =>
      println(s"Current balance: $balance")
      sender() ! balance
  }
}

object BankAccountApp extends App {
  val system = ActorSystem("BankSystem")
  val account = system.actorOf(Props(new BankAccount(BigDecimal(1000))), "account1")

  account ! Deposit(BigDecimal(500))
  account ! Withdraw(BigDecimal(200))
  account ! GetBalance

  Thread.sleep(1000)
  system.terminate()
}