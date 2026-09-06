import type { Category, Item, ManagedTag } from '../types/api';

const ownerId = '01a4dc43-39a8-4f09-b2f1-71a0a8b0fbde';

export const fixtureCategories: Category[] = [
  {
    id: 'c32aa516-ad8f-43ab-b20f-04aec8a9a952',
    name: 'Research',
    color: '#0f766e',
    icon: 'flask-conical',
    description: 'References and papers',
    item_count: 3,
    created_at: '2026-08-02T09:15:00Z',
    updated_at: '2026-09-03T15:12:00Z',
  },
  {
    id: '220f207d-6738-4fb6-9181-13e1c846c887',
    name: 'Ideas',
    color: '#ea580c',
    icon: 'lightbulb',
    description: 'Notes worth returning to',
    item_count: 2,
    created_at: '2026-08-10T08:30:00Z',
    updated_at: '2026-09-01T12:10:00Z',
  },
  {
    id: '1981b994-355c-459f-947f-9537d4d09135',
    name: 'Design',
    color: '#ca8a04',
    icon: 'palette',
    description: 'Interfaces and systems',
    item_count: 1,
    created_at: '2026-08-20T10:00:00Z',
    updated_at: '2026-08-28T10:00:00Z',
  },
];

export const fixtureTags: ManagedTag[] = [
  { id: 'tag-systems', name: 'systems', color: '#0f766e', usage_count: 4 },
  { id: 'tag-product', name: 'product', color: '#2563eb', usage_count: 3 },
  { id: 'tag-research', name: 'research', color: '#7c3aed', usage_count: 3 },
  { id: 'tag-habits', name: 'habits', color: '#ea580c', usage_count: 2 },
  { id: 'tag-design', name: 'design', color: '#ca8a04', usage_count: 2 },
];

const itemDefaults: Pick<
  Item,
  | 'user_id'
  | 'description'
  | 'notes'
  | 'author'
  | 'published_at'
  | 'favicon_url'
  | 'extracted_text'
  | 'language'
  | 'processing_error'
  | 'analysis_status'
  | 'analysis_error'
  | 'analysis_version'
  | 'analysis_requested_at'
  | 'analysis_started_at'
  | 'analysis_completed_at'
  | 'assets'
  | 'is_archived'
  | 'read_count'
  | 'last_visited_at'
  | 'revision'
  | 'deleted_at'
> = {
  user_id: ownerId,
  description: null,
  notes: null,
  author: null,
  published_at: null,
  favicon_url: null,
  extracted_text: null,
  language: 'en',
  processing_error: null,
  analysis_status: 'analyzed',
  analysis_error: null,
  analysis_version: 1,
  analysis_requested_at: '2026-09-01T00:00:00Z',
  analysis_started_at: '2026-09-01T00:01:00Z',
  analysis_completed_at: '2026-09-01T00:02:00Z',
  assets: [],
  is_archived: false,
  read_count: 0,
  last_visited_at: null,
  revision: 1,
  deleted_at: null,
};

export const fixtureItems: Item[] = [
  {
    ...itemDefaults,
    id: '0d74711b-70cf-4f45-935a-43c8bb08d83b',
    type: 'screenshot',
    url: null,
    raw_text: null,
    title: 'Building durable habits',
    description: 'Weekly system for routines, focus work, and deliberate practice.',
    notes: 'Adapt the minimum viable routine for the next planning cycle.',
    source: 'screenshot',
    source_domain: null,
    extracted_text: 'Weekly progress morning routine exercise read focus work make it obvious easy satisfying',
    summary: 'A visual habit system built around consistency and low-friction routines.',
    metadata: { preview_url: '/fixtures/habits-capture.png' },
    processing_status: 'ready',
    category_id: fixtureCategories[1].id,
    tags: [fixtureTags[0], fixtureTags[3]],
    is_favorite: true,
    created_at: '2026-09-03T16:20:00Z',
    updated_at: '2026-09-03T16:22:00Z',
  },
  {
    ...itemDefaults,
    id: '2fde1c9c-e002-43bf-b773-73f44a3f96a7',
    type: 'link',
    url: 'https://www.nngroup.com/articles/recognition-and-recall/',
    raw_text: null,
    title: 'Recognition rather than recall',
    description: 'Why interfaces should minimize the information people must remember.',
    source: 'article',
    source_domain: 'nngroup.com',
    author: 'Nielsen Norman Group',
    published_at: '2024-02-17T00:00:00Z',
    summary: 'Make actions and choices visible so users can recognize options instead of recalling them.',
    metadata: null,
    processing_status: 'ready',
    category_id: fixtureCategories[2].id,
    tags: [fixtureTags[1], fixtureTags[4]],
    is_favorite: true,
    read_count: 4,
    created_at: '2026-09-03T10:45:00Z',
    updated_at: '2026-09-03T10:47:00Z',
  },
  {
    ...itemDefaults,
    id: '5ce76e50-1bba-4c3e-a6fe-e1e294de68a0',
    type: 'text',
    url: null,
    raw_text: 'A useful knowledge system should make capture nearly invisible and retrieval deliberate.',
    title: 'Capture should disappear',
    source: 'manual',
    source_domain: null,
    summary: null,
    metadata: null,
    processing_status: 'ready',
    category_id: fixtureCategories[1].id,
    tags: [fixtureTags[0], fixtureTags[1]],
    is_favorite: false,
    created_at: '2026-09-02T14:05:00Z',
    updated_at: '2026-09-02T14:05:00Z',
  },
  {
    ...itemDefaults,
    id: 'd63b31cc-4ad8-4032-b681-033d03b3df65',
    type: 'link',
    url: 'https://martinfowler.com/articles/patterns-of-distributed-systems/',
    raw_text: null,
    title: 'Patterns of distributed systems',
    description: 'A catalog of patterns for reliable distributed applications.',
    source: 'article',
    source_domain: 'martinfowler.com',
    author: 'Unmesh Joshi',
    summary: null,
    metadata: null,
    processing_status: 'processing',
    category_id: fixtureCategories[0].id,
    tags: [fixtureTags[0], fixtureTags[2]],
    is_favorite: false,
    created_at: '2026-09-01T08:30:00Z',
    updated_at: '2026-09-01T08:30:00Z',
  },
  {
    ...itemDefaults,
    id: '1be599c8-0039-47f5-b1ec-08cc283b5e7c',
    type: 'text',
    url: null,
    raw_text: 'Search quality is part indexing and part language: saved context makes future queries much easier.',
    title: 'Context improves retrieval',
    source: 'manual',
    source_domain: null,
    summary: null,
    metadata: null,
    processing_status: 'ready',
    category_id: fixtureCategories[0].id,
    tags: [fixtureTags[2]],
    is_favorite: false,
    is_archived: true,
    created_at: '2026-08-28T11:10:00Z',
    updated_at: '2026-09-02T09:00:00Z',
  },
];
