private def generateToken(length: Int): String = {
    val sb = new StringBuilder(length)
    var i = 0
    while (i < length) {
      sb.append(alphabet.charAt(secureRandom.nextInt(alphabet.length)))
      i += 1
    }
    sb.toString()
  }
}