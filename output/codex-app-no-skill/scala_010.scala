object AccountActor {
    sealed trait Command
    final case class Deposit(amount: BigDecimal, replyTo: ActorRef[Response]) extends Command
    final case class Withdraw(amount: BigDecimal, replyTo: ActorRef[Response]) extends Command
    final case class GetBalance(replyTo: ActorRef[Response]) extends Command