export function generatedOutputMismatches(outputs, readText) {
  return outputs.filter(({ content, filePath }) => readText(filePath) !== content);
}
