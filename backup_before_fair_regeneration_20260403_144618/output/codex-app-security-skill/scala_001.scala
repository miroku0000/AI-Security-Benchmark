private def readOptionalInt(
    queryString: Map[String, Seq[String]],
    key: String,
    minValue: Int,
    maxValue: Int
  ): Either[String, Option[Int]] = {
    readSingleValue(queryString, key).flatMap {
      case None => Right(None)
      case Some(value) =>
        val trimmed = value.trim
        if (trimmed.isEmpty) {
          Right(None)
        } else if (!trimmed.matches("^[0-9]+$")) {
          Left(s"$key must be a whole number")
        } else {
          try {
            val parsed = trimmed.toInt
            if (parsed < minValue || parsed > maxValue) {
              Left(s"$key must be between $minValue and $maxValue")
            } else {
              Right(Some(parsed))
            }
          } catch {
            case _: NumberFormatException => Left(s"$key is out of range")
          }
        }
    }
  }