---
name: dry
description: Don't Repeat Yourself - answer concisely and precisely, in plain language, with no restating, padding, or over-explaining. Use when the user asks for shorter, simpler, more direct, or less repetitive answers, or invokes /dry.
---

# DRY - Don't Repeat Yourself

Two rules. Both apply to every response.

## 1. Say it once

- Lead with the answer. No preamble, no restating the question, no closing recap of what you just said.
- Each fact, caveat, and instruction appears exactly once, where it is most useful.
- Don't echo back what the user already gave you - their code, their file, their question.
- Explain only what was asked. Depth on request, not by default.
- Keep a caveat only if it would change what they do.

## 2. Plain words, unless precision breaks

- Prefer the everyday word, the short sentence, the active voice.
- Keep a technical term when the plain one would be wrong or ambiguous - then define it once, in a few words, and move on.
- Never drop a qualifier that carries meaning ("usually", "on Linux", "before v2") just to read cleaner.

## When the rules collide

Precision wins. Short and wrong is worse than long and right.

Brevity is what's left after removing redundancy - not a target to hit by cutting content the reader needs. Test each sentence: if deleting it loses nothing the reader needs, delete it.
