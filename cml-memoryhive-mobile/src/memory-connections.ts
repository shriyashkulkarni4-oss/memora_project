import type { Item } from "./types";

export interface LocalMemoryConnection {
  item: Item;
  reasons: string[];
  duplicate: boolean;
  score: number;
}

function normalizedContent(item: Item) {
  return (item.extracted_text || item.raw_text || "").trim().toLocaleLowerCase().replace(/\s+/g, " ");
}

export function localMemoryConnections(source: Item, items: Item[], limit = 6): LocalMemoryConnection[] {
  const sourceTags = new Set(source.tags.map((tag) => tag.name.toLocaleLowerCase()));
  return items
    .filter((candidate) => candidate.id !== source.id && !candidate.deleted_at)
    .map((candidate) => {
      const reasons: string[] = [];
      let score = 0;
      const sameUrl = Boolean(source.url && candidate.url && source.url === candidate.url);
      const content = normalizedContent(source);
      const sameContent = Boolean(content && content === normalizedContent(candidate));
      const overlap = candidate.tags.map((tag) => tag.name.toLocaleLowerCase()).filter((tag) => sourceTags.has(tag));
      if (sameUrl) { score += 20; reasons.push("same URL"); }
      if (sameContent) { score += 20; reasons.push("same saved content"); }
      if (overlap.length) { score += overlap.length * 3; reasons.push(`shared tags: ${overlap.slice(0, 3).join(", ")}`); }
      if (source.source && source.source === candidate.source) { score += 1; reasons.push(`same source: ${source.source}`); }
      return { item: candidate, reasons, duplicate: sameUrl || sameContent, score };
    })
    .filter((value) => value.score > 0)
    .sort((left, right) => right.score - left.score || left.item.id.localeCompare(right.item.id))
    .slice(0, limit);
}
