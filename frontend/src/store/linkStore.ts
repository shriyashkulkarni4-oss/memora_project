import { create } from 'zustand';
import { Link, Category, Tag, LinkStats, LinkSource, LinkStatus, CreateLinkDto, UpdateLinkDto } from '../types';

// Sample data
const sampleTags: Tag[] = [
  { id: 'tag-1', name: 'javascript', color: '#f7df1e', usageCount: 3 },
  { id: 'tag-2', name: 'python', color: '#3776ab', usageCount: 2 },
  { id: 'tag-3', name: 'react', color: '#61dafb', usageCount: 4 },
  { id: 'tag-4', name: 'ai', color: '#9b59b6', usageCount: 5 },
  { id: 'tag-5', name: 'startup', color: '#27ae60', usageCount: 2 },
  { id: 'tag-6', name: 'tutorial', color: '#f39c12', usageCount: 3 },
  { id: 'tag-7', name: 'must-read', color: '#e74c3c', usageCount: 4 },
];

const sampleCategories: Category[] = [
  { id: 'cat-1', name: 'Tech & Development', color: '#3b82f6', icon: 'Code', description: 'Programming and tech news', linkCount: 2, createdAt: new Date(), updatedAt: new Date() },
  { id: 'cat-2', name: 'AI & Machine Learning', color: '#8b5cf6', icon: 'Brain', description: 'AI tools and research', linkCount: 2, createdAt: new Date(), updatedAt: new Date() },
  { id: 'cat-3', name: 'Business & Startups', color: '#10b981', icon: 'Briefcase', description: 'Business insights', linkCount: 1, createdAt: new Date(), updatedAt: new Date() },
  { id: 'cat-4', name: 'Design & UX', color: '#f43f5e', icon: 'Palette', description: 'Design inspiration', linkCount: 0, createdAt: new Date(), updatedAt: new Date() },
  { id: 'cat-5', name: 'Learning', color: '#f59e0b', icon: 'BookOpen', description: 'Tutorials and courses', linkCount: 1, createdAt: new Date(), updatedAt: new Date() },
];

const sampleLinks: Link[] = [
  {
    id: 'link-1',
    userId: 'user-1',
    url: 'https://react.dev/learn',
    title: 'React Documentation - Quick Start',
    description: 'The official React documentation with interactive examples',
    source: LinkSource.ARTICLE,
    status: LinkStatus.PROCESSED,
    categoryId: 'cat-1',
    tags: [sampleTags[2], sampleTags[5]],
    aiSummary: {
      summary: 'Comprehensive guide to getting started with React, covering components, JSX, and hooks.',
      keyPoints: ['Component-based architecture', 'Declarative UI patterns', 'React hooks for state'],
      topics: ['React', 'Frontend', 'JavaScript'],
      suggestedCategories: ['Tech & Development'],
      suggestedTags: ['react', 'tutorial'],
      processedAt: new Date()
    },
    isFavorite: true,
    isArchived: false,
    readCount: 8,
    lastVisitedAt: new Date(),
    createdAt: new Date('2024-01-15'),
    updatedAt: new Date('2024-01-15')
  },
  {
    id: 'link-2',
    userId: 'user-1',
    url: 'https://openai.com/blog/chatgpt',
    title: 'Introducing ChatGPT - OpenAI',
    description: 'OpenAI announces ChatGPT, a conversational AI model',
    source: LinkSource.NEWS,
    status: LinkStatus.PROCESSED,
    categoryId: 'cat-2',
    tags: [sampleTags[3], sampleTags[6]],
    aiSummary: {
      summary: 'OpenAI introduces ChatGPT, a large language model fine-tuned for conversational interactions.',
      keyPoints: ['Built on GPT architecture', 'RLHF training', 'Free research preview'],
      topics: ['AI', 'ChatGPT', 'LLM'],
      suggestedCategories: ['AI & Machine Learning'],
      suggestedTags: ['ai', 'must-read'],
      processedAt: new Date()
    },
    isFavorite: true,
    isArchived: false,
    readCount: 15,
    createdAt: new Date('2024-01-10'),
    updatedAt: new Date('2024-01-10')
  },
  {
    id: 'link-3',
    userId: 'user-1',
    url: 'https://github.com/features/copilot',
    title: 'GitHub Copilot - AI Pair Programmer',
    description: 'AI-powered code completion and suggestions',
    source: LinkSource.GITHUB,
    status: LinkStatus.PROCESSED,
    categoryId: 'cat-2',
    tags: [sampleTags[3], sampleTags[0]],
    isFavorite: false,
    isArchived: false,
    readCount: 5,
    createdAt: new Date('2024-01-20'),
    updatedAt: new Date('2024-01-20')
  },
  {
    id: 'link-4',
    userId: 'user-1',
    url: 'https://www.ycombinator.com/library',
    title: 'YC Startup Library',
    description: 'Essential resources for startup founders',
    source: LinkSource.ARTICLE,
    status: LinkStatus.PENDING,
    categoryId: 'cat-3',
    tags: [sampleTags[4]],
    isFavorite: false,
    isArchived: false,
    readCount: 2,
    createdAt: new Date('2024-01-25'),
    updatedAt: new Date('2024-01-25')
  },
  {
    id: 'link-5',
    userId: 'user-1',
    url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    title: 'Advanced TypeScript Patterns',
    description: 'Deep dive into TypeScript generics and utility types',
    source: LinkSource.YOUTUBE,
    status: LinkStatus.PROCESSED,
    categoryId: 'cat-5',
    tags: [sampleTags[0], sampleTags[5]],
    isFavorite: false,
    isArchived: false,
    readCount: 3,
    createdAt: new Date('2024-01-28'),
    updatedAt: new Date('2024-01-28')
  }
];

interface LinkStore {
  // State
  links: Link[];
  categories: Category[];
  tags: Tag[];
  isLoading: boolean;
  error: string | null;

  // Actions
  addLink: (dto: CreateLinkDto) => Link;
  updateLink: (id: string, dto: UpdateLinkDto) => void;
  deleteLink: (id: string) => void;
  toggleFavorite: (id: string) => void;
  toggleArchive: (id: string) => void;

  addCategory: (category: Omit<Category, 'id' | 'linkCount' | 'createdAt' | 'updatedAt'>) => Category;
  updateCategory: (id: string, updates: Partial<Category>) => void;
  deleteCategory: (id: string) => void;

  addTag: (name: string, color?: string) => Tag;
  deleteTag: (id: string) => void;

  // Selectors
  getStats: () => LinkStats;
  getFilteredLinks: (filter: { search?: string; categoryId?: string; source?: LinkSource; showArchived?: boolean }) => Link[];
  getFavorites: () => Link[];
  getArchived: () => Link[];
  getRecentLinks: (count?: number) => Link[];
}

const generateId = (prefix: string) => `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

const getRandomColor = () => {
  const colors = ['#3b82f6', '#8b5cf6', '#10b981', '#f43f5e', '#f59e0b', '#06b6d4', '#ec4899'];
  return colors[Math.floor(Math.random() * colors.length)];
};

export const useLinkStore = create<LinkStore>((set, get) => ({
  links: sampleLinks,
  categories: sampleCategories,
  tags: sampleTags,
  isLoading: false,
  error: null,

  addLink: (dto) => {
    const { tags, categories } = get();
    const linkTags = dto.tags?.map(tagName => {
      const existing = tags.find(t => t.name.toLowerCase() === tagName.toLowerCase());
      if (existing) return existing;
      const newTag: Tag = { id: generateId('tag'), name: tagName.toLowerCase(), color: getRandomColor(), usageCount: 1 };
      set(state => ({ tags: [...state.tags, newTag] }));
      return newTag;
    }) || [];

    const newLink: Link = {
      id: generateId('link'),
      userId: 'user-1',
      url: dto.url || '',
      title: dto.title || 'Untitled',
      description: dto.description,
      source: dto.source,
      status: LinkStatus.PENDING,
      categoryId: dto.categoryId,
      category: categories.find(c => c.id === dto.categoryId),
      tags: linkTags,
      isFavorite: false,
      isArchived: false,
      readCount: 0,
      notes: dto.notes,
      createdAt: new Date(),
      updatedAt: new Date()
    };

    set(state => ({ links: [newLink, ...state.links] }));
    return newLink;
  },

  updateLink: (id, dto) => {
    set(state => ({
      links: state.links.map(link =>
        link.id === id
          ? { ...link, ...dto, updatedAt: new Date() }
          : link
      )
    }));
  },

  deleteLink: (id) => {
    set(state => ({
      links: state.links.filter(link => link.id !== id)
    }));
  },

  toggleFavorite: (id) => {
    set(state => ({
      links: state.links.map(link =>
        link.id === id
          ? { ...link, isFavorite: !link.isFavorite, updatedAt: new Date() }
          : link
      )
    }));
  },

  toggleArchive: (id) => {
    set(state => ({
      links: state.links.map(link =>
        link.id === id
          ? { ...link, isArchived: !link.isArchived, updatedAt: new Date() }
          : link
      )
    }));
  },

  addCategory: (category) => {
    const newCategory: Category = {
      ...category,
      id: generateId('cat'),
      linkCount: 0,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    set(state => ({ categories: [...state.categories, newCategory] }));
    return newCategory;
  },

  updateCategory: (id, updates) => {
    set(state => ({
      categories: state.categories.map(cat =>
        cat.id === id
          ? { ...cat, ...updates, updatedAt: new Date() }
          : cat
      )
    }));
  },

  deleteCategory: (id) => {
    set(state => ({
      categories: state.categories.filter(cat => cat.id !== id),
      links: state.links.map(link =>
        link.categoryId === id
          ? { ...link, categoryId: undefined, category: undefined }
          : link
      )
    }));
  },

  addTag: (name, color) => {
    const { tags } = get();
    const existing = tags.find(t => t.name.toLowerCase() === name.toLowerCase());
    if (existing) return existing;

    const newTag: Tag = {
      id: generateId('tag'),
      name: name.toLowerCase().trim(),
      color: color || getRandomColor(),
      usageCount: 0
    };
    set(state => ({ tags: [...state.tags, newTag] }));
    return newTag;
  },

  deleteTag: (id) => {
    set(state => ({
      tags: state.tags.filter(tag => tag.id !== id),
      links: state.links.map(link => ({
        ...link,
        tags: link.tags.filter(t => t.id !== id)
      }))
    }));
  },

  getStats: () => {
    const { links, categories, tags } = get();
    const activeLinks = links.filter(l => !l.isArchived);

    return {
      totalLinks: links.length,
      favoriteLinks: links.filter(l => l.isFavorite).length,
      archivedLinks: links.filter(l => l.isArchived).length,
      pendingProcessing: links.filter(l => l.status === LinkStatus.PENDING).length,
      categoryCounts: categories.map(cat => ({
        categoryId: cat.id,
        categoryName: cat.name,
        count: activeLinks.filter(l => l.categoryId === cat.id).length
      })),
      sourceCounts: Object.values(LinkSource)
        .map(source => ({
          source,
          count: activeLinks.filter(l => l.source === source).length
        }))
        .filter(s => s.count > 0),
      recentLinks: [...links].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()).slice(0, 5),
      topTags: [...tags].sort((a, b) => b.usageCount - a.usageCount).slice(0, 10)
    };
  },

  getFilteredLinks: (filter) => {
    const { links } = get();
    let result = [...links];

    if (!filter.showArchived) {
      result = result.filter(l => !l.isArchived);
    }

    if (filter.search) {
      const search = filter.search.toLowerCase();
      result = result.filter(l =>
        l.title.toLowerCase().includes(search) ||
        l.description?.toLowerCase().includes(search) ||
        l.url.toLowerCase().includes(search) ||
        l.tags.some(t => t.name.includes(search))
      );
    }

    if (filter.categoryId) {
      result = result.filter(l => l.categoryId === filter.categoryId);
    }

    if (filter.source) {
      result = result.filter(l => l.source === filter.source);
    }

    return result.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  },

  getFavorites: () => {
    const { links } = get();
    return links.filter(l => l.isFavorite && !l.isArchived);
  },

  getArchived: () => {
    const { links } = get();
    return links.filter(l => l.isArchived);
  },

  getRecentLinks: (count = 5) => {
    const { links } = get();
    return [...links]
      .filter(l => !l.isArchived)
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, count);
  }
}));
