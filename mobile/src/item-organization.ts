import type { Item, ItemType, ManagedTag } from "./types";
import { normalizeTag } from "./item-filters";

export interface TagSummary {
  name: string;
  count: number;
}

export interface ManagedTagSummary extends TagSummary {
  id: string;
  color: string;
  managed: boolean;
}

export interface OrganizationSummary {
  active: number;
  archived: number;
  favorites: number;
  processing: number;
  byType: Record<ItemType, number>;
  tags: TagSummary[];
}

export function countItemsInCategory(items: Item[], categoryId: string) {
  return items.filter((item) => !item.deleted_at && item.category_id === categoryId).length;
}

export function summarizeManagedTags(items: Item[], managedTags: ManagedTag[]): ManagedTagSummary[] {
  const localCounts = new Map(summarizeOrganization(items).tags.map((tag) => [tag.name, tag.count]));
  const managedNames = new Set<string>();
  const rows = managedTags.map((tag) => {
    const name = normalizeTag(tag.name);
    managedNames.add(name);
    return {
      id: tag.id,
      name,
      color: tag.color,
      count: localCounts.get(name) ?? tag.usage_count,
      managed: true,
    };
  });

  for (const [name, count] of localCounts) {
    if (!managedNames.has(name)) {
      rows.push({ id: `local:${name}`, name, color: "#087F6D", count, managed: false });
    }
  }

  return rows.sort((left, right) => right.count - left.count || left.name.localeCompare(right.name));
}

export function summarizeOrganization(items: Item[]): OrganizationSummary {
  const activeItems = items.filter((item) => !item.is_archived);
  const tagCounts = new Map<string, number>();

  for (const item of activeItems) {
    for (const tag of item.tags) {
      const name = normalizeTag(tag.name);
      if (!name) continue;
      tagCounts.set(name, (tagCounts.get(name) ?? 0) + 1);
    }
  }

  return {
    active: activeItems.length,
    archived: items.filter((item) => item.is_archived).length,
    favorites: activeItems.filter((item) => item.is_favorite).length,
    processing: activeItems.filter((item) => ["pending", "processing"].includes(item.processing_status)).length,
    byType: {
      link: activeItems.filter((item) => item.type === "link").length,
      screenshot: activeItems.filter((item) => item.type === "screenshot").length,
      text: activeItems.filter((item) => item.type === "text").length,
    },
    tags: Array.from(tagCounts, ([name, count]) => ({ name, count })).sort((left, right) =>
      right.count - left.count || left.name.localeCompare(right.name),
    ),
  };
}
