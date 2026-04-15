private def unescapeJsonString(s: String): String = {
    val sb = new StringBuilder(s.length)
    var i = 0
    while (i < s.length) {
      val ch = s.charAt(i)
      if (ch != '\\') {
        sb.append(ch)
        i += 1
      } else {
        if (i + 1 >= s.length) {
          throw new IllegalArgumentException("invalid JSON string escape")
        }
        s.charAt(i + 1) match {
          case '"'  => sb.append('"'); i += 2
          case '\\' => sb.append('\\'); i += 2
          case '/'  => sb.append('/'); i += 2
          case 'b'  => sb.append('\b'); i += 2
          case 'f'  => sb.append('\f'); i += 2
          case 'n'  => sb.append('\n'); i += 2
          case 'r'  => sb.append('\r'); i += 2
          case 't'  => sb.append('\t'); i += 2
          case 'u' =>
            if (i + 5 >= s.length) {
              throw new IllegalArgumentException("invalid unicode escape")
            }
            val hex = s.substring(i + 2, i + 6)
            val codePoint = Integer.parseInt(hex, 16)
            sb.append(codePoint.toChar)
            i += 6
          case _ =>
            throw new IllegalArgumentException("invalid JSON string escape")
        }
      }
    }
    sb.toString()
  }
}