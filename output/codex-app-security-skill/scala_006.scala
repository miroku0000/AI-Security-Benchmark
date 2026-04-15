import java.io.IOException
import java.nio.charset.{CodingErrorAction, StandardCharsets}
import java.nio.charset.CharacterCodingException
import java.nio.file.{Files, InvalidPathException, LinkOption, Path, Paths}
import java.util.Locale
import javax.inject.{Inject, Singleton}