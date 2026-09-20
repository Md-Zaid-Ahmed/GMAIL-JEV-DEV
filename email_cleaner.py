"""Turns a raw Gmail API message into clean {sender, subject, body} text.

Gmail returns bodies as base64url blobs scattered across a MIME tree, padded
with tracking links, invisible preheader characters and newsletter chrome.
This module strips all of that down to the prose a classifier can read.
"""

import base64
import html
import re
from email.utils import parseaddr

# Preheader padding and bidi marks that bulk-mailers inject to pad the inbox
# preview: zero-width spaces, LTR/RTL marks, combining grapheme joiners.
INVISIBLE = re.compile(
    "[­͏؜᠎​-‏  ‪-‮"
    "⁠-⁤﻿]"
)

# Horizontal rules, including the em/en dashes newsletters build them from.
RULE = re.compile(r"(?m)^\s*[-=_*+~–—―─-╿]{3,}\s*$")

# Calls to action left behind once their link is stripped ("View messages:").
CTA = re.compile(
    r"(?i)^(view|see|read|learn|join|share|get|click|upgrade|create|browse|"
    r"follow|download|explore|start|try|shop|apply)\b[^:]{0,45}:\s*$"
)

# Everything from the first of these lines down is footer boilerplate.
FOOTER = re.compile(
    r"(?im)^\s*("
    r"unsubscribe"
    r"|manage (your )?(email )?(preferences|settings)"
    r"|update your preferences"
    r"|view (this email )?in (your )?browser"
    r"|you('re| are) receiving this"
    r"|you are receiving .{0,60}emails?"
    r"|this (email|message) was (intended for|sent to)"
    r"|sent (by|to you by) \w+"
    r"|privacy policy"
    r"|you are reading a plain text version"
    r"|your opinion matters"
    r"|see more of what you like"
    r"|want more listings like these"
    r"|add us to your address book"
    r"|copyright\s*©|©\s*\d{4}"
    r")"
)


def decode_part(part):
  """Decodes one MIME part's base64url body into text."""
  data = part.get("body", {}).get("data")
  if not data:
    return ""
  return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")


def html_to_text(raw):
  """Turns an HTML body into plain text, keeping paragraph breaks."""
  text = re.sub(r"<(script|style|head)\b[^>]*>.*?</\1>", " ", raw,
                flags=re.S | re.I)
  text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
  text = re.sub(r"</(p|div|tr|li|h[1-6]|table)\s*>", "\n", text, flags=re.I)
  return re.sub(r"<[^>]+>", "", text)


def strip_inline_noise(text):
  """Removes links, markup and invisible padding, keeping line structure."""
  text = html.unescape(text)
  # Markdown images and links: keep the label, drop the target.
  text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
  text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
  # Lines that exist only to describe a stripped asset.
  text = re.sub(r"(?im)^\s*(view image|follow image link|caption|view online|"
                r"read (online|in browser))\s*:.*$", "", text)
  # Bare, bracketed and parenthesised URLs, plus mailto: links.
  text = re.sub(r"\(\s*(https?://|mailto:)[^)]*\)", "", text)
  text = re.sub(r"<[^>\s]*(https?://|mailto:)[^>]*>", "", text)
  text = re.sub(r"\b(https?://|www\.)\S+", "", text)
  # Markdown emphasis and ==highlight== markers.
  text = RULE.sub("", text)
  text = re.sub(r"={2,}", "", text)
  text = re.sub(r"[*_`]{1,3}", "", text)
  text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
  text = INVISIBLE.sub("", text)
  return text.replace(" ", " ")


def tidy_lines(text):
  """Normalises whitespace and drops empty, leftover and duplicate lines."""
  out = []
  for line in text.splitlines():
    line = re.sub(r"[ \t]+", " ", line).strip()
    # Brackets and parens orphaned by link removal.
    line = re.sub(r"[\[\(]\s*$", "", line).strip()
    line = re.sub(r"^\s*[\]\)]", "", line).strip()
    if not line or CTA.match(line):
      continue
    # Newsletters repeat headers; collapse consecutive duplicates.
    if out and out[-1] == line:
      continue
    out.append(line)
  return "\n".join(out)


def clean_text(text):
  """Strips the clutter email bodies are padded with."""
  text = tidy_lines(strip_inline_noise(text))
  cut = FOOTER.search(text)
  if cut:
    text = text[: cut.start()]
  return text.strip()


def extract_body(payload):
  """Walks the MIME tree and returns the cleaned message text.

  Prefers text/plain; falls back to text/html, since plenty of marketing mail
  is HTML-only.
  """
  plain, rich = [], []

  def walk(part):
    mime = part.get("mimeType", "")
    if mime == "text/plain":
      plain.append(decode_part(part))
    elif mime == "text/html":
      rich.append(decode_part(part))
    for sub in part.get("parts", []):
      walk(sub)

  walk(payload)

  text = clean_text("".join(plain))
  if not text:
    text = clean_text(html_to_text("".join(rich)))
  return text


def normalize(msg):
  """Reduces a Gmail API message to {sender, subject, body}."""
  headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
  return {
      "sender": parseaddr(headers.get("from", ""))[1],
      "subject": headers.get("subject", ""),
      "body": extract_body(msg["payload"]),
  }
