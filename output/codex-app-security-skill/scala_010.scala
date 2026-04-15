sealed trait Response
    final case class Accepted(transactionId: UUID, balance: BigDecimal) extends Response
    final case class Rejected(transactionId: UUID, reason: String, balance: BigDecimal) extends Response
    final case class DuplicateTransaction(transactionId: UUID, balance: BigDecimal) extends Response
    final case class CurrentBalance(balance: BigDecimal) extends Response