import type { Item } from "./types";

export function matchesLocalSearch(item: Item, search: string) {
  const query = search.trim().toLocaleLowerCase();
  if (!query) return true;
  return [
    item.title,
    item.url,
    item.raw_text,
    item.notes,
    item.summary,
    item.extracted_text,
    ...item.tags.map((tag) => tag.name),
  ]
    .filter(Boolean)
    .some((value) => String(value).toLocaleLowerCase().includes(query));
}
