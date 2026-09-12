import type { AISuggestionDecision, Item } from "./types";

export interface MobileSuggestion {
  suggestion_type: "tag" | "classification";
  value: string;
  status: "pending" | "accepted" | "rejected" | "never";
  confidence: number | null;
}

export function suggestionsFromItem(item: Item): { topics: string[]; suggestions: MobileSuggestion[] } {
  const enrichment = item.metadata?.enrichment as Record<string, unknown> | undefined;
  if (!enrichment) return { topics: [], suggestions: [] };
  const decisions = (item.metadata?.suggestion_decisions || {}) as Record<string, AISuggestionDecision["action"]>;
  const confidence = typeof enrichment.confidence === "number" ? enrichment.confidence : null;
  const status = (type: "tag" | "classification", value: string): MobileSuggestion["status"] => {
    const action = decisions[`${type}:${value.toLowerCase()}`];
    if (action === "accept") return "accepted";
    if (action === "reject") return "rejected";
    if (action === "never") return "never";
    return "pending";
  };
  const tags = Array.isArray(enrichment.suggested_tags)
    ? enrichment.suggested_tags.filter((value): value is string => typeof value === "string")
    : [];
  const classification = typeof enrichment.classification === "string" ? enrichment.classification : null;
  return {
    topics: Array.isArray(enrichment.topics)
      ? enrichment.topics.filter((value): value is string => typeof value === "string")
      : [],
    suggestions: [
      ...tags.map((value): MobileSuggestion => ({ suggestion_type: "tag", value, confidence, status: status("tag", value) })),
      ...(classification ? [{ suggestion_type: "classification" as const, value: classification, confidence, status: status("classification", classification) }] : []),
    ],
  };
}
