"""Fix the leading backslash in apps/web/app/page.tsx."""
import pathlib

p = pathlib.Path("apps/web/app/page.tsx")
data = p.read_text(encoding="utf-8")

# Strip any leading backslash/whitespace before "use client"
while data and data[0] in ("\\" , "\r", "\n", " "):
    data = data[1:]

p.write_text(data, encoding="utf-8", newline="\n")
print(f"Fixed. Size: {len(data)}")
print(f"First 40 chars: {repr(data[:40])}")
