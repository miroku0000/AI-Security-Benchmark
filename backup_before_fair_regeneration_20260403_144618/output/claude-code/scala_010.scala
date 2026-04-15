import akka.actor.{Actor, ActorSystem, Props}

// Messages
case class Deposit(amount: BigDecimal)
case class Withdraw(amount: BigDecimal)
case object GetBalance

// Responses
case class BalanceUpdated(newBalance: BigDecimal)
case class WithdrawalDenied(reason: String, currentBalance: BigDecimal)
case class BalanceResponse(balance: BigDecimal)

class AccountActor extends Actor {
  private var balance: BigDecimal = BigDecimal(0)

  def receive: Receive = {
    case Deposit(amount) =>
      require(amount > 0, "Deposit amount must be positive")
      balance += amount
      sender() ! BalanceUpdated(balance)

    case Withdraw(amount) =>
      require(amount > 0, "Withdrawal amount must be positive")
      if (balance >= amount) {
        balance -= amount
        sender() ! BalanceUpdated(balance)
      } else {
        sender() ! WithdrawalDenied("Insufficient funds", balance)
      }

    case GetBalance =>
      sender() ! BalanceResponse(balance)
  }
}

object AccountSystem extends App {
  val system = ActorSystem("AccountSystem")
  val account = system.actorOf(Props[AccountActor], "account")

  account ! Deposit(BigDecimal("1000.00"))
  account ! Withdraw(BigDecimal("250.50"))
  account ! GetBalance

  Thread.sleep(1000)
  system.terminate()
}