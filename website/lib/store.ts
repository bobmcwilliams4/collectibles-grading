import { create } from 'zustand';
import { User } from 'firebase/auth';
import { Collectible, MarketplaceListing, PaginatedResult } from './firebase';
import { DocumentSnapshot } from 'firebase/firestore';

// ============================================================================
// AUTH STORE
// ============================================================================

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: true,
  error: null,
  setUser: (user) => set({ user, loading: false, error: null }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error, loading: false }),
  clearError: () => set({ error: null }),
}));

// ============================================================================
// COLLECTION STORE WITH OPTIMISTIC UPDATES
// ============================================================================

interface CollectionState {
  items: Collectible[];
  loading: boolean;
  error: string | null;
  lastDoc: DocumentSnapshot | null;
  hasMore: boolean;
  // Actions
  setItems: (items: Collectible[]) => void;
  addItem: (item: Collectible) => void;
  updateItem: (id: string, updates: Partial<Collectible>) => void;
  removeItem: (id: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setPagination: (lastDoc: DocumentSnapshot | null, hasMore: boolean) => void;
  // Optimistic update helpers
  optimisticAdd: (item: Collectible) => { rollback: () => void };
  optimisticUpdate: (id: string, updates: Partial<Collectible>) => { rollback: () => void };
  optimisticRemove: (id: string) => { rollback: () => void };
  // Clear
  clear: () => void;
}

export const useCollectionStore = create<CollectionState>((set, get) => ({
  items: [],
  loading: false,
  error: null,
  lastDoc: null,
  hasMore: true,

  setItems: (items) => set({ items, error: null }),

  addItem: (item) => set((state) => ({
    items: [item, ...state.items],
    error: null
  })),

  updateItem: (id, updates) => set((state) => ({
    items: state.items.map((item) =>
      item.id === id ? { ...item, ...updates } : item
    ),
    error: null
  })),

  removeItem: (id) => set((state) => ({
    items: state.items.filter((item) => item.id !== id),
    error: null
  })),

  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error, loading: false }),
  setPagination: (lastDoc, hasMore) => set({ lastDoc, hasMore }),

  // Optimistic add - immediately adds item and returns rollback function
  optimisticAdd: (item) => {
    const previousItems = get().items;
    set({ items: [item, ...previousItems] });

    return {
      rollback: () => set({ items: previousItems })
    };
  },

  // Optimistic update - immediately updates and returns rollback
  optimisticUpdate: (id, updates) => {
    const previousItems = get().items;
    set({
      items: previousItems.map((item) =>
        item.id === id ? { ...item, ...updates } : item
      )
    });

    return {
      rollback: () => set({ items: previousItems })
    };
  },

  // Optimistic remove - immediately removes and returns rollback
  optimisticRemove: (id) => {
    const previousItems = get().items;
    set({ items: previousItems.filter((item) => item.id !== id) });

    return {
      rollback: () => set({ items: previousItems })
    };
  },

  clear: () => set({
    items: [],
    loading: false,
    error: null,
    lastDoc: null,
    hasMore: true
  }),
}));

// ============================================================================
// MARKETPLACE STORE WITH REAL-TIME SUPPORT
// ============================================================================

type MarketplaceSortOption = 'newest' | 'price_low' | 'price_high' | 'grade_high';

interface MarketplaceState {
  listings: MarketplaceListing[];
  filter: string | null;
  categoryFilter: 'all' | 'collectibles' | 'digital_goods';
  typeFilter: string | null;
  sortBy: MarketplaceSortOption;
  loading: boolean;
  error: string | null;
  lastDoc: DocumentSnapshot | null;
  hasMore: boolean;
  searchQuery: string;
  // Actions
  setListings: (listings: MarketplaceListing[]) => void;
  appendListings: (listings: MarketplaceListing[]) => void;
  setFilter: (filter: string | null) => void;
  setCategoryFilter: (category: 'all' | 'collectibles' | 'digital_goods') => void;
  setTypeFilter: (type: string | null) => void;
  setSortBy: (sortBy: MarketplaceSortOption) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setPagination: (lastDoc: DocumentSnapshot | null, hasMore: boolean) => void;
  setSearchQuery: (query: string) => void;
  // Real-time update handlers
  onListingAdded: (listing: MarketplaceListing) => void;
  onListingUpdated: (id: string, updates: Partial<MarketplaceListing>) => void;
  onListingRemoved: (id: string) => void;
  // Optimistic updates
  optimisticCreate: (listing: MarketplaceListing) => { rollback: () => void };
  // Helpers
  getFilteredListings: () => MarketplaceListing[];
  clear: () => void;
}

export const useMarketplaceStore = create<MarketplaceState>((set, get) => ({
  listings: [],
  filter: null,
  categoryFilter: 'all',
  typeFilter: null,
  sortBy: 'newest',
  loading: false,
  error: null,
  lastDoc: null,
  hasMore: true,
  searchQuery: '',

  setListings: (listings) => set({ listings, error: null }),

  appendListings: (newListings) => set((state) => ({
    listings: [...state.listings, ...newListings],
    error: null
  })),

  setFilter: (filter) => set({ filter }),
  setCategoryFilter: (categoryFilter) => set({ categoryFilter, typeFilter: null }),
  setTypeFilter: (typeFilter) => set({ typeFilter }),
  setSortBy: (sortBy) => set({ sortBy }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error, loading: false }),
  setPagination: (lastDoc, hasMore) => set({ lastDoc, hasMore }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),

  // Real-time handlers
  onListingAdded: (listing) => set((state) => ({
    listings: [listing, ...state.listings.filter(l => l.id !== listing.id)]
  })),

  onListingUpdated: (id, updates) => set((state) => ({
    listings: state.listings.map((listing) =>
      listing.id === id ? { ...listing, ...updates } : listing
    )
  })),

  onListingRemoved: (id) => set((state) => ({
    listings: state.listings.filter((listing) => listing.id !== id)
  })),

  // Optimistic create
  optimisticCreate: (listing) => {
    const previousListings = get().listings;
    set({ listings: [listing, ...previousListings] });

    return {
      rollback: () => set({ listings: previousListings })
    };
  },

  // Get filtered and sorted listings
  getFilteredListings: () => {
    const { listings, categoryFilter, typeFilter, sortBy, searchQuery } = get();

    let filtered = listings;

    // Apply category filter
    if (categoryFilter !== 'all') {
      filtered = filtered.filter(l => l.category === categoryFilter);
    }

    // Apply type filter
    if (typeFilter) {
      filtered = filtered.filter(l => l.type === typeFilter);
    }

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(l =>
        l.title.toLowerCase().includes(query) ||
        l.sellerName.toLowerCase().includes(query) ||
        l.description?.toLowerCase().includes(query) ||
        l.tags?.some(tag => tag.toLowerCase().includes(query))
      );
    }

    // Apply sorting
    switch (sortBy) {
      case 'price_low':
        filtered = [...filtered].sort((a, b) => a.askingPrice - b.askingPrice);
        break;
      case 'price_high':
        filtered = [...filtered].sort((a, b) => b.askingPrice - a.askingPrice);
        break;
      case 'grade_high':
        filtered = [...filtered].sort((a, b) => (b.grade || 0) - (a.grade || 0));
        break;
      case 'newest':
      default:
        // Already sorted by createdAt desc from Firestore
        break;
    }

    return filtered;
  },

  clear: () => set({
    listings: [],
    filter: null,
    categoryFilter: 'all',
    typeFilter: null,
    sortBy: 'newest',
    loading: false,
    error: null,
    lastDoc: null,
    hasMore: true,
    searchQuery: ''
  }),
}));

// ============================================================================
// UI STATE STORE
// ============================================================================

interface UIState {
  // Modals
  showCreateListingModal: boolean;
  showItemActionsModal: boolean;
  showRegradeModal: boolean;
  showListForSaleModal: boolean;
  // Selected items
  selectedCollectible: Collectible | null;
  selectedListing: MarketplaceListing | null;
  // Toast notifications
  toasts: Array<{
    id: string;
    message: string;
    type: 'success' | 'error' | 'info' | 'warning';
    duration?: number;
  }>;
  // Actions
  openCreateListingModal: () => void;
  closeCreateListingModal: () => void;
  openItemActionsModal: (collectible: Collectible) => void;
  closeItemActionsModal: () => void;
  openRegradeModal: (collectible: Collectible) => void;
  closeRegradeModal: () => void;
  openListForSaleModal: (collectible: Collectible) => void;
  closeListForSaleModal: () => void;
  selectListing: (listing: MarketplaceListing | null) => void;
  // Toast management
  addToast: (message: string, type: 'success' | 'error' | 'info' | 'warning', duration?: number) => void;
  removeToast: (id: string) => void;
  clearToasts: () => void;
}

export const useUIStore = create<UIState>((set, get) => ({
  showCreateListingModal: false,
  showItemActionsModal: false,
  showRegradeModal: false,
  showListForSaleModal: false,
  selectedCollectible: null,
  selectedListing: null,
  toasts: [],

  openCreateListingModal: () => set({ showCreateListingModal: true }),
  closeCreateListingModal: () => set({ showCreateListingModal: false }),

  openItemActionsModal: (collectible) => set({
    showItemActionsModal: true,
    selectedCollectible: collectible
  }),
  closeItemActionsModal: () => set({
    showItemActionsModal: false,
    selectedCollectible: null
  }),

  openRegradeModal: (collectible) => set({
    showRegradeModal: true,
    selectedCollectible: collectible
  }),
  closeRegradeModal: () => set({
    showRegradeModal: false
  }),

  openListForSaleModal: (collectible) => set({
    showListForSaleModal: true,
    selectedCollectible: collectible
  }),
  closeListForSaleModal: () => set({
    showListForSaleModal: false
  }),

  selectListing: (listing) => set({ selectedListing: listing }),

  addToast: (message, type, duration = 5000) => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    set((state) => ({
      toasts: [...state.toasts, { id, message, type, duration }]
    }));

    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => {
        get().removeToast(id);
      }, duration);
    }
  },

  removeToast: (id) => set((state) => ({
    toasts: state.toasts.filter(t => t.id !== id)
  })),

  clearToasts: () => set({ toasts: [] }),
}));

// ============================================================================
// INFINITE SCROLL HOOK HELPER
// ============================================================================

export interface InfiniteScrollState<T> {
  items: T[];
  loading: boolean;
  error: string | null;
  hasMore: boolean;
  loadMore: () => Promise<void>;
  refresh: () => Promise<void>;
}

// Export a helper for creating infinite scroll behavior
export function createInfiniteScroll<T>(
  fetchFn: (lastDoc?: DocumentSnapshot) => Promise<PaginatedResult<T>>,
  onError: (error: Error) => void
): {
  items: T[];
  loading: boolean;
  hasMore: boolean;
  lastDoc: DocumentSnapshot | null;
  loadInitial: () => Promise<void>;
  loadMore: () => Promise<void>;
  refresh: () => Promise<void>;
  setItems: (items: T[]) => void;
} {
  let items: T[] = [];
  let loading = false;
  let hasMore = true;
  let lastDoc: DocumentSnapshot | null = null;

  const loadInitial = async () => {
    loading = true;
    try {
      const result = await fetchFn();
      items = result.items;
      lastDoc = result.lastDoc;
      hasMore = result.hasMore;
    } catch (error) {
      onError(error as Error);
    } finally {
      loading = false;
    }
  };

  const loadMore = async () => {
    if (loading || !hasMore) return;

    loading = true;
    try {
      const result = await fetchFn(lastDoc || undefined);
      items = [...items, ...result.items];
      lastDoc = result.lastDoc;
      hasMore = result.hasMore;
    } catch (error) {
      onError(error as Error);
    } finally {
      loading = false;
    }
  };

  const refresh = async () => {
    items = [];
    lastDoc = null;
    hasMore = true;
    await loadInitial();
  };

  const setItems = (newItems: T[]) => {
    items = newItems;
  };

  return {
    get items() { return items; },
    get loading() { return loading; },
    get hasMore() { return hasMore; },
    get lastDoc() { return lastDoc; },
    loadInitial,
    loadMore,
    refresh,
    setItems,
  };
}
