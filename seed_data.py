#!/usr/bin/env python3
"""Seed realistic, idempotent Memoryhive demo accounts through the public API."""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_PASSWORD = "MemoryhiveDemo123!"
SEED_NAMESPACE = uuid.UUID("c7781217-dd82-48cc-9819-0502c612e666")


def link(
    title: str,
    url: str,
    category: str,
    tags: list[str],
    *,
    source: str = "web",
    description: str | None = None,
    notes: str | None = None,
    favorite: bool = False,
    archived: bool = False,
    days_ago: int = 0,
) -> dict[str, Any]:
    return {
        "type": "link",
        "title": title,
        "url": url,
        "category": category,
        "tags": tags,
        "source": source,
        "description": description,
        "notes": notes,
        "favorite": favorite,
        "archived": archived,
        "days_ago": days_ago,
    }


def note(
    title: str,
    content: str,
    category: str,
    tags: list[str],
    *,
    source: str = "mobile",
    favorite: bool = False,
    archived: bool = False,
    days_ago: int = 0,
) -> dict[str, Any]:
    return {
        "type": "text",
        "title": title,
        "raw_text": content,
        "category": category,
        "tags": tags,
        "source": source,
        "favorite": favorite,
        "archived": archived,
        "days_ago": days_ago,
    }


PERSONAS: list[dict[str, Any]] = [
    {
        "key": "engineer",
        "name": "Aarav Mehta - Senior Software Engineer",
        "email": "engineer@demo.memoryhive.app",
        "categories": [
            (
                "Engineering",
                "#2563EB",
                "code",
                "Architecture and implementation references",
            ),
            (
                "DevOps",
                "#0F766E",
                "terminal",
                "Infrastructure and production operations",
            ),
            ("Career", "#7C3AED", "briefcase", "Learning and professional growth"),
        ],
        "tags": {
            "backend": "#2563EB",
            "architecture": "#7C3AED",
            "devops": "#0F766E",
            "database": "#DC2626",
            "career": "#CA8A04",
        },
        "items": [
            link(
                "FastAPI async documentation",
                "https://fastapi.tiangolo.com/async/",
                "Engineering",
                ["backend", "python"],
                favorite=True,
                days_ago=1,
            ),
            link(
                "React documentation",
                "https://react.dev/learn",
                "Engineering",
                ["frontend", "react"],
                days_ago=3,
            ),
            link(
                "PostgreSQL full-text search",
                "https://www.postgresql.org/docs/current/textsearch.html",
                "Engineering",
                ["database", "search"],
                favorite=True,
                days_ago=5,
            ),
            link(
                "Redis data types",
                "https://redis.io/docs/latest/develop/data-types/",
                "Engineering",
                ["backend", "cache"],
                days_ago=8,
            ),
            link(
                "Kubernetes concepts",
                "https://kubernetes.io/docs/concepts/",
                "DevOps",
                ["devops", "kubernetes"],
                favorite=True,
                days_ago=12,
            ),
            link(
                "Docker Compose production guidance",
                "https://docs.docker.com/compose/production/",
                "DevOps",
                ["devops", "docker"],
                days_ago=16,
            ),
            link(
                "GitHub Actions documentation",
                "https://docs.github.com/en/actions",
                "DevOps",
                ["devops", "ci-cd"],
                days_ago=19,
            ),
            link(
                "System Design Primer",
                "https://github.com/donnemartin/system-design-primer",
                "Career",
                ["architecture", "interview"],
                favorite=True,
                days_ago=24,
            ),
            note(
                "Production debugging checklist",
                "Check the deployment event, error rate, p95 latency, saturation, recent config changes, database locks, queue depth, and dependency health before restarting services.",
                "DevOps",
                ["devops", "runbook"],
                favorite=True,
                days_ago=2,
            ),
            note(
                "PostgreSQL indexing reminder",
                "Use EXPLAIN (ANALYZE, BUFFERS) before adding an index. Prefer selective composite indexes that match real query predicates and ordering.",
                "Engineering",
                ["database", "performance"],
                days_ago=7,
            ),
            note(
                "Staff engineering reading list",
                "Review technical strategy, writing effective design documents, mentoring across teams, and measuring reliability outcomes.",
                "Career",
                ["career", "leadership"],
                days_ago=14,
            ),
            note(
                "Old migration notes",
                "Legacy service migration completed. Keep this archived for historical context and rollback investigation.",
                "DevOps",
                ["migration", "archive"],
                archived=True,
                days_ago=45,
            ),
        ],
    },
    {
        "key": "student",
        "name": "Ananya Rao - Graduate Student",
        "email": "student@demo.memoryhive.app",
        "categories": [
            ("Research", "#7C3AED", "book-open", "Papers and thesis references"),
            ("Coursework", "#2563EB", "graduation-cap", "Classes and study material"),
            ("Campus", "#DB2777", "calendar", "University plans and opportunities"),
        ],
        "tags": {
            "paper": "#7C3AED",
            "machine-learning": "#2563EB",
            "thesis": "#DB2777",
            "study": "#0F766E",
        },
        "items": [
            link(
                "Attention Is All You Need",
                "https://arxiv.org/abs/1706.03762",
                "Research",
                ["paper", "machine-learning", "transformers"],
                favorite=True,
                days_ago=1,
            ),
            link(
                "Retrieval-Augmented Generation paper",
                "https://arxiv.org/abs/2005.11401",
                "Research",
                ["paper", "machine-learning", "rag"],
                favorite=True,
                days_ago=4,
            ),
            link(
                "Papers With Code",
                "https://paperswithcode.com/",
                "Research",
                ["paper", "datasets"],
                days_ago=6,
            ),
            link(
                "MIT Introduction to Algorithms",
                "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/",
                "Coursework",
                ["algorithms", "study"],
                days_ago=10,
            ),
            link(
                "Stanford CS229 materials",
                "https://cs229.stanford.edu/",
                "Coursework",
                ["machine-learning", "study"],
                favorite=True,
                days_ago=13,
            ),
            link(
                "Zotero research assistant",
                "https://www.zotero.org/",
                "Research",
                ["research-tools", "citations"],
                days_ago=17,
            ),
            link(
                "Kaggle datasets",
                "https://www.kaggle.com/datasets",
                "Coursework",
                ["datasets", "practice"],
                days_ago=21,
            ),
            note(
                "Thesis milestones",
                "September 18: finish evaluation dataset. September 25: send methodology draft. October 10: complete experiments. October 24: defense rehearsal.",
                "Research",
                ["thesis", "deadlines"],
                favorite=True,
                days_ago=2,
            ),
            note(
                "Embedding experiment",
                "Compare multilingual-e5-base, bge-base-en, and text-embedding baselines using Recall@10, MRR, indexing time, and query latency.",
                "Research",
                ["thesis", "machine-learning", "experiment"],
                days_ago=5,
            ),
            note(
                "Study group agenda",
                "Review dynamic programming proofs, transformer attention complexity, and the statistics problem set. Meet in Library Room 3B.",
                "Coursework",
                ["study", "algorithms"],
                days_ago=8,
            ),
            note(
                "Scholarship application",
                "Draft statement of purpose and request recommendation letters before the graduate research scholarship deadline.",
                "Campus",
                ["scholarship", "career"],
                favorite=True,
                days_ago=15,
            ),
            note(
                "Completed semester reading",
                "Archived reading checklist from the previous semester.",
                "Coursework",
                ["archive", "study"],
                archived=True,
                days_ago=70,
            ),
        ],
    },
    {
        "key": "commerce",
        "name": "Rohan Kapoor - E-Commerce Manager",
        "email": "commerce@demo.memoryhive.app",
        "categories": [
            (
                "Growth",
                "#DB2777",
                "trending-up",
                "Acquisition, conversion, and retention",
            ),
            ("Operations", "#0F766E", "package", "Inventory, fulfillment, and support"),
            (
                "Finance",
                "#CA8A04",
                "chart-no-axes-combined",
                "Revenue and unit economics",
            ),
        ],
        "tags": {
            "ecommerce": "#DB2777",
            "analytics": "#2563EB",
            "operations": "#0F766E",
            "finance": "#CA8A04",
        },
        "items": [
            link(
                "Shopify e-commerce trends",
                "https://www.shopify.com/blog/ecommerce-trends",
                "Growth",
                ["ecommerce", "trends"],
                favorite=True,
                days_ago=1,
            ),
            link(
                "Google Analytics e-commerce guide",
                "https://support.google.com/analytics/answer/12200568",
                "Growth",
                ["analytics", "conversion"],
                days_ago=4,
            ),
            link(
                "Meta Ads Library",
                "https://www.facebook.com/ads/library/",
                "Growth",
                ["ads", "creative"],
                favorite=True,
                days_ago=7,
            ),
            link(
                "Stripe subscriptions overview",
                "https://docs.stripe.com/billing/subscriptions/overview",
                "Finance",
                ["payments", "finance"],
                days_ago=9,
            ),
            link(
                "Google Merchant Center",
                "https://merchants.google.com/",
                "Operations",
                ["ecommerce", "catalog"],
                days_ago=12,
            ),
            link(
                "Amazon Seller Central",
                "https://sellercentral.amazon.com/",
                "Operations",
                ["marketplace", "operations"],
                days_ago=18,
            ),
            link(
                "Shiprocket resources",
                "https://www.shiprocket.in/blog/",
                "Operations",
                ["shipping", "operations"],
                days_ago=22,
            ),
            note(
                "Weekly commerce KPIs",
                "Revenue target: INR 12 lakh. Conversion rate target: 3.2%. CAC ceiling: INR 550. Return-to-origin below 8%. Repeat purchase rate above 24%.",
                "Finance",
                ["finance", "kpi", "analytics"],
                favorite=True,
                days_ago=2,
            ),
            note(
                "Festive campaign experiments",
                "Test free-shipping threshold, bundle pricing, creator video ads, abandoned-cart WhatsApp flow, and returning-customer landing pages.",
                "Growth",
                ["campaign", "experiments"],
                days_ago=5,
            ),
            note(
                "Warehouse action list",
                "Reconcile top 50 SKUs, investigate damaged inventory, update reorder points, and review same-day dispatch misses with the fulfillment partner.",
                "Operations",
                ["inventory", "operations"],
                favorite=True,
                days_ago=8,
            ),
            note(
                "Customer support themes",
                "Most common tickets: delivery ETA, exchange sizing, payment retry, coupon eligibility, and damaged packaging.",
                "Operations",
                ["support", "customer-experience"],
                days_ago=14,
            ),
            note(
                "Previous agency report",
                "Archived performance summary from the former advertising agency.",
                "Growth",
                ["archive", "ads"],
                archived=True,
                days_ago=60,
            ),
        ],
    },
    {
        "key": "home",
        "name": "Priya Sharma - Home and Lifestyle Curator",
        "email": "home@demo.memoryhive.app",
        "categories": [
            ("Recipes", "#DC2626", "cooking-pot", "Meals, snacks, and kitchen ideas"),
            ("Home Ideas", "#0F766E", "house", "Organization, decor, and gardening"),
            ("Family", "#7C3AED", "heart", "Family activities and routines"),
        ],
        "tags": {
            "instagram": "#DB2777",
            "video": "#DC2626",
            "recipe": "#CA8A04",
            "home": "#0F766E",
            "family": "#7C3AED",
        },
        "items": [
            link(
                "Instagram: creamy garlic pasta reel",
                "https://www.instagram.com/reel/C8kP2n9sLmQ/",
                "Recipes",
                ["instagram", "video", "recipe", "dinner"],
                source="instagram",
                favorite=True,
                days_ago=1,
            ),
            link(
                "Instagram: five lunchbox ideas",
                "https://www.instagram.com/reel/C9mB3xVs7tA/",
                "Recipes",
                ["instagram", "video", "recipe", "kids"],
                source="instagram",
                days_ago=2,
            ),
            link(
                "Instagram: no-bake chocolate dessert",
                "https://www.instagram.com/reel/C7tN4qLm8aR/",
                "Recipes",
                ["instagram", "video", "dessert"],
                source="instagram",
                favorite=True,
                days_ago=4,
            ),
            link(
                "Instagram: pantry organization",
                "https://www.instagram.com/reel/C6pR8vKs2dM/",
                "Home Ideas",
                ["instagram", "video", "home", "organization"],
                source="instagram",
                days_ago=5,
            ),
            link(
                "Instagram: balcony herb garden",
                "https://www.instagram.com/reel/C5hT9wQn3bL/",
                "Home Ideas",
                ["instagram", "video", "home", "plants"],
                source="instagram",
                favorite=True,
                days_ago=7,
            ),
            link(
                "Instagram: festive table decoration",
                "https://www.instagram.com/p/C4jV7xMp6sK/",
                "Home Ideas",
                ["instagram", "decor", "festival"],
                source="instagram",
                days_ago=9,
            ),
            link(
                "Instagram: kids craft activity",
                "https://www.instagram.com/reel/C3nW5yRt8pD/",
                "Family",
                ["instagram", "video", "family", "craft"],
                source="instagram",
                days_ago=11,
            ),
            link(
                "YouTube: weekly Indian meal prep",
                "https://www.youtube.com/watch?v=1N6hbRbyAeQ",
                "Recipes",
                ["youtube", "video", "recipe", "meal-prep"],
                source="youtube",
                favorite=True,
                days_ago=3,
            ),
            link(
                "YouTube: complete home cleaning routine",
                "https://www.youtube.com/watch?v=3M7c9Vqj1XQ",
                "Home Ideas",
                ["youtube", "video", "home", "cleaning"],
                source="youtube",
                days_ago=6,
            ),
            link(
                "YouTube: beginner yoga at home",
                "https://www.youtube.com/watch?v=v7AYKMP6rOE",
                "Family",
                ["youtube", "video", "wellness"],
                source="youtube",
                favorite=True,
                days_ago=8,
            ),
            link(
                "YouTube: indoor plants for beginners",
                "https://www.youtube.com/watch?v=LZhnCxG5c6s",
                "Home Ideas",
                ["youtube", "video", "plants"],
                source="youtube",
                days_ago=13,
            ),
            link(
                "Pinterest kitchen storage ideas",
                "https://www.pinterest.com/search/pins/?q=kitchen%20storage%20ideas",
                "Home Ideas",
                ["pinterest", "home", "organization"],
                source="pinterest",
                days_ago=15,
            ),
            link(
                "Pinterest birthday activity ideas",
                "https://www.pinterest.com/search/pins/?q=kids%20birthday%20activities",
                "Family",
                ["pinterest", "family", "party"],
                source="pinterest",
                days_ago=17,
            ),
            note(
                "Weekly grocery list",
                "Oats, milk, curd, paneer, spinach, tomatoes, onions, seasonal fruit, whole-wheat bread, lentils, rice, nuts, and school snacks.",
                "Recipes",
                ["grocery", "recipe"],
                favorite=True,
                days_ago=1,
            ),
            note(
                "Sunday home reset",
                "Change bed linen, water plants, plan five dinners, prepare school uniforms, refill pantry jars, and call parents.",
                "Home Ideas",
                ["home", "routine"],
                days_ago=4,
            ),
            note(
                "Rainy-day family activities",
                "Make paper lanterns, bake banana bread, build a reading tent, play carrom, and organize family photos.",
                "Family",
                ["family", "activities"],
                days_ago=10,
            ),
            note(
                "Old festival shopping list",
                "Archived shopping list retained as a reference for next year's decorations.",
                "Family",
                ["archive", "festival"],
                archived=True,
                days_ago=90,
            ),
        ],
    },
]


class ApiError(RuntimeError):
    def __init__(self, status: int, payload: Any):
        super().__init__(f"HTTP {status}: {payload}")
        self.status = status
        self.payload = payload


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        token: str | None = None,
        retries: int = 2,
    ) -> Any:
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(
            f"{self.base_url}{path}", data=data, headers=headers, method=method
        )
        try:
            with urlopen(request, timeout=30) as response:
                content = response.read()
                return json.loads(content) if content else None
        except HTTPError as error:
            body = error.read().decode(errors="replace")
            try:
                parsed: Any = json.loads(body)
            except json.JSONDecodeError:
                parsed = body
            if error.code == 429 and retries > 0:
                delay = min(int(error.headers.get("Retry-After", "2")), 65)
                print(f"  Rate limit reached; retrying in {delay}s...")
                time.sleep(delay)
                return self.request(method, path, payload, token, retries - 1)
            raise ApiError(error.code, parsed) from error


def deterministic_id(persona_key: str, title: str) -> str:
    return str(uuid.uuid5(SEED_NAMESPACE, f"{persona_key}:{title}"))


def login_or_register(api: ApiClient, persona: dict[str, Any], password: str) -> str:
    credentials = {"email": persona["email"], "password": password}
    try:
        api.request(
            "POST",
            "/api/v1/auth/register",
            {**credentials, "name": persona["name"]},
        )
        print(f"Created {persona['email']}")
    except ApiError as error:
        if error.status != 409:
            raise
        print(f"Using existing account {persona['email']}")
    tokens = api.request("POST", "/api/v1/auth/login", credentials)
    return str(tokens["access_token"])


def seed_categories(
    api: ApiClient, token: str, persona: dict[str, Any]
) -> dict[str, str]:
    existing = {
        category["name"]: category["id"]
        for category in api.request("GET", "/api/v1/categories", token=token)
    }
    for name, color, icon, description in persona["categories"]:
        if name not in existing:
            created = api.request(
                "POST",
                "/api/v1/categories",
                {
                    "name": name,
                    "color": color,
                    "icon": icon,
                    "description": description,
                },
                token,
            )
            existing[name] = created["id"]
    return existing


def seed_tags(api: ApiClient, token: str, persona: dict[str, Any]) -> None:
    existing = {tag["name"] for tag in api.request("GET", "/api/v1/tags", token=token)}
    for name, color in persona["tags"].items():
        if name not in existing:
            api.request("POST", "/api/v1/tags", {"name": name, "color": color}, token)


def seed_persona(
    api: ApiClient, persona: dict[str, Any], password: str, dry_run: bool
) -> tuple[int, int]:
    print(f"\n{persona['name']}")
    if dry_run:
        print(f"  Would seed {len(persona['items'])} items")
        return len(persona["items"]), 0

    token = login_or_register(api, persona, password)
    categories = seed_categories(api, token, persona)
    seed_tags(api, token, persona)
    created_count = 0
    existing_count = 0

    for item in persona["items"]:
        item_id = deterministic_id(persona["key"], item["title"])
        payload = {
            key: value
            for key, value in item.items()
            if key not in {"category", "favorite", "archived", "days_ago"}
            and value is not None
        }
        payload.update(
            {
                "id": item_id,
                "category_id": categories[item["category"]],
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(days=item["days_ago"])
                ).isoformat(),
                "metadata": {"seed": "memoryhive-demo-v1", "persona": persona["key"]},
            }
        )
        try:
            saved = api.request("POST", "/api/v1/items", payload, token)
            created_count += 1
        except ApiError as error:
            if error.status != 409:
                raise
            try:
                saved = api.request("GET", f"/api/v1/items/{item_id}", token=token)
                existing_count += 1
            except ApiError as lookup_error:
                if lookup_error.status != 404:
                    raise
                print(f"  Skipped duplicate URL: {item['title']}")
                continue

        desired_values = {
            "title": item["title"],
            "is_favorite": item["favorite"],
            "is_archived": item["archived"],
        }
        updates = {
            key: value
            for key, value in desired_values.items()
            if saved.get(key) != value
        }
        if updates:
            api.request("PATCH", f"/api/v1/items/{item_id}", updates, token)

    print(
        f"  Categories: {len(categories)} | Created: {created_count} | "
        f"Already present: {existing_count}"
    )
    return created_count, existing_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument(
        "--persona",
        choices=["all", *(persona["key"] for persona in PERSONAS)],
        default="all",
        help="Seed one persona or all personas (default: all)",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected = [
        persona
        for persona in PERSONAS
        if args.persona == "all" or persona["key"] == args.persona
    ]
    api = ApiClient(args.base_url)
    try:
        if not args.dry_run:
            health = api.request("GET", "/health/ready")
            if health.get("status") != "ready":
                raise RuntimeError(f"API is not ready: {health}")
        total_created = 0
        total_existing = 0
        for persona in selected:
            created, existing = seed_persona(api, persona, args.password, args.dry_run)
            total_created += created
            total_existing += existing
    except (ApiError, URLError, TimeoutError, RuntimeError) as error:
        print(f"\nSeeding failed: {error}", file=sys.stderr)
        return 1

    print("\nSeed complete")
    print(f"Created: {total_created} | Already present: {total_existing}")
    if not args.dry_run:
        print("\nDemo accounts")
        for persona in selected:
            print(f"  {persona['email']} / {args.password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
