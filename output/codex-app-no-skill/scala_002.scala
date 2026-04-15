private def valueToJson(value: Any, dataType: DataType): String = {
    if (value == null) {
      "null"
    } else {
      dataType match {
        case StringType => s""""${escapeJson(value.toString)}""""
        case BooleanType => value.toString
        case ByteType | ShortType | IntegerType | LongType | FloatType | DoubleType | _: DecimalType => value.toString
        case DateType | TimestampType => s""""${escapeJson(value.toString)}""""
        case BinaryType =>
          val bytes = value.asInstanceOf[Array[Byte]]
          s""""${java.util.Base64.getEncoder.encodeToString(bytes)}""""
        case ArrayType(elementType, _) =>
          value.asInstanceOf[Seq[Any]].map(v => valueToJson(v, elementType)).mkString("[", ",", "]")
        case MapType(_, valueType, _) =>
          value
            .asInstanceOf[scala.collection.Map[Any, Any]]
            .map { case (k, v) =>
              s""""${escapeJson(String.valueOf(k))}":${valueToJson(v, valueType)}"""
            }
            .mkString("{", ",", "}")
        case structType: StructType =>
          val row = value.asInstanceOf[Row]
          rowJson(row, structType)
        case _ =>
          s""""${escapeJson(value.toString)}""""
      }
    }
  }