#!/usr/bin/env python3
from __future__ import annotations

import email.utils
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
import html

import feedparser
import yaml
from dateutil import parser as date_parser
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "tools" / "config.yml"
OUTPUT_PATH = ROOT / "feed.xml"
ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"


@dataclass
class FeedItem:
  title: str
  link: str
  summary: str
  pub_date: datetime
  category: str


def load_config(path: Path) -> dict:
  with path.open("r", encoding="utf-8") as file:
    data = yaml.safe_load(file) or {}

  categories = data.get("categories") or []
  if not categories:
    raise ValueError("config.yml 必须包含至少一个 category")

  return {
    "categories": categories,
    "days": int(data.get("days", 3)),
    "max_items": int(data.get("max_items", 80)),
  }


def parse_datetime(value: str) -> datetime | None:
  if not value:
    return None
  try:
    dt = date_parser.parse(value)
  except (ValueError, TypeError, OverflowError):
    return None
  if dt.tzinfo is None:
    dt = dt.replace(tzinfo=timezone.utc)
  return dt.astimezone(timezone.utc)


def normalize_summary(entry: dict) -> str:
  summary = entry.get("summary") or entry.get("description") or ""
  return " ".join(html.unescape(summary).split())


def collect_items(categories: Iterable[str], earliest_time: datetime) -> list[FeedItem]:
  dedup: dict[str, FeedItem] = {}

  for category in categories:
    url = f"https://export.arxiv.org/rss/{category}"
    parsed = feedparser.parse(url)

    for entry in parsed.entries:
      link = (entry.get("link") or "").strip()
      if not link:
        continue

      published = parse_datetime(entry.get("published") or entry.get("updated") or "")
      if published is None or published < earliest_time:
        continue

      identifier = entry.get("id") or link
      item = FeedItem(
        title=" ".join((entry.get("title") or "Untitled").split()),
        link=link,
        summary=normalize_summary(entry),
        pub_date=published,
        category=category,
      )

      if identifier not in dedup or dedup[identifier].pub_date < item.pub_date:
        dedup[identifier] = item

  return list(dedup.values())


def format_rfc2822(dt: datetime) -> str:
  return email.utils.format_datetime(dt.astimezone(timezone.utc))


def write_feed(items: list[FeedItem]) -> None:
  ET.register_namespace("itunes", ITUNES_NS)

  rss = ET.Element("rss", attrib={"version": "2.0", "xmlns:itunes": ITUNES_NS})
  channel = ET.SubElement(rss, "channel")

  ET.SubElement(channel, "title").text = "arXiv TTS Brief"
  ET.SubElement(channel, "link").text = "https://github.com/02Zona/arxiv-tts-web"
  ET.SubElement(channel, "description").text = "Text-only arXiv feed for Web Speech TTS player"
  ET.SubElement(channel, "language").text = "en-us"
  ET.SubElement(channel, "lastBuildDate").text = format_rfc2822(datetime.now(timezone.utc))

  for item in items:
    item_node = ET.SubElement(channel, "item")
    ET.SubElement(item_node, "title").text = item.title
    ET.SubElement(item_node, "link").text = item.link
    ET.SubElement(item_node, "guid").text = item.link
    ET.SubElement(item_node, "pubDate").text = format_rfc2822(item.pub_date)
    ET.SubElement(item_node, "category").text = item.category

    short_description = item.summary[:280] + ("…" if len(item.summary) > 280 else "")
    ET.SubElement(item_node, "description").text = short_description
    ET.SubElement(item_node, f"{{{ITUNES_NS}}}summary").text = item.summary

  tree = ET.ElementTree(rss)
  tree.write(OUTPUT_PATH, encoding="utf-8", xml_declaration=True)


def main() -> None:
  config = load_config(CONFIG_PATH)
  earliest_time = datetime.now(timezone.utc) - timedelta(days=config["days"])

  items = collect_items(config["categories"], earliest_time)
  items.sort(key=lambda item: item.pub_date, reverse=True)
  items = items[: config["max_items"]]

  write_feed(items)
  print(f"Generated {OUTPUT_PATH.name} with {len(items)} item(s).")


if __name__ == "__main__":
  main()
