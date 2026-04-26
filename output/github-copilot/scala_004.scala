import scala.sys.process._

// UNSAFE (DO NOT USE):
// s"ls ${userInput}".!!

// SAFE (Properly quotes arguments):
Seq("ls", userInput).!!