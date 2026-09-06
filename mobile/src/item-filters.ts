import type { Item, ItemType } from "./types";

export type SummaryFilter = "saved" | "favorites" | "processing" | "archived";
export type TypeFilter = ItemType | "all";

export interface ItemFilterState {
  summary: SummaryFilter;
  type: TypeFilter;
  categoryId: string | null;
  tags: string[];
}

export function normalizeTag(value: string) {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}

export function uniqueTags(values: string[]) {
  return Array.from(new Set(values.map(normalizeTag).filter(Boolean))).sort();
}

export function tagsFromItems(items: Item[]) {
  return uniqueTags(items.flatMap((item) => item.tags.map((tag) => tag.name)));
}

export function filterItems(items: Item[], filters: ItemFilterState) {
  return items.filter((item) => {
    if (filters.summary === "saved" && item.is_archived) return false;
    if (filters.summary === "favorites" && (!item.is_favorite || item.is_archived)) return false;
    if (filters.summary === "processing" && (item.is_archived || !["pending", "processing"].includes(item.processing_status))) return false;
    if (filters.summary === "archived" && !item.is_archived) return false;
    if (filters.type !== "all" && item.type !== filters.type) return false;
    if (filters.categoryId && item.category_id !== filters.categoryId) return false;
    if (filters.tags.length && !filters.tags.every((tag) => item.tags.some((itemTag) => normalizeTag(itemTag.name) === tag))) return false;
    return true;
  });
}
