export function hasLeadingWhitespace(value: string): boolean {
  return /^\s/u.test(String(value ?? ''))
}
