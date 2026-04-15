async function main() {
  const args = process.argv.slice(2);
  const command = args[0] || 'help';
  const options = parseOptions(args.slice(1));