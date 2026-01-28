'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { getMarketplaceListings, MarketplaceListing, CollectibleType, DigitalGoodType, MarketplaceCategory, getListableCollectibles, createCollectibleListing, Collectible } from '@/lib/firebase';
import { useMarketplaceStore, useAuthStore } from '@/lib/store';

// Category tabs - Row 1: Main categories, Row 2: Sub-categories
const categoryTabs: { value: MarketplaceCategory | 'all' | 'services'; label: string; icon: string }[] = [
  { value: 'all', label: 'All Items', icon: '🛒' },
  { value: 'collectibles', label: 'Collectibles', icon: '🎯' },
  { value: 'digital_goods', label: 'Digital Goods', icon: '💾' },
  { value: 'services', label: 'Services', icon: '🎙️' },
];

// Collectible type filters
const collectibleFilters: { value: CollectibleType | 'all'; label: string; icon: string }[] = [
  { value: 'all', label: 'All', icon: '📦' },
  { value: 'comic', label: 'Comics', icon: '📚' },
  { value: 'card', label: 'Cards', icon: '🎴' },
  { value: 'coin', label: 'Coins', icon: '🪙' },
  { value: 'stamp', label: 'Stamps', icon: '📮' },
  { value: 'vinyl', label: 'Vinyl', icon: '💿' },
];

// Digital goods type filters
const digitalFilters: { value: DigitalGoodType | 'all'; label: string; icon: string }[] = [
  { value: 'all', label: 'All', icon: '📦' },
  { value: 'voice_clone', label: 'Voice Clones', icon: '🎙️' },
  { value: 'image', label: 'Images', icon: '🖼️' },
  { value: 'video', label: 'Videos', icon: '🎬' },
  { value: 'audio', label: 'Audio', icon: '🎵' },
  { value: 'artwork', label: 'AI Artwork', icon: '🎨' },
  { value: '3d_model', label: '3D Models', icon: '🧊' },
];

function getGradeClass(grade?: number): string {
  if (!grade) return '';
  if (grade >= 9.8) return 'grade-gem';
  if (grade >= 9.4) return 'grade-mint';
  if (grade >= 9.0) return 'grade-nm';
  if (grade >= 8.0) return 'grade-vf';
  if (grade >= 6.0) return 'grade-fine';
  return 'grade-low';
}

function getTypeIcon(type: string): string {
  const allFilters = [...collectibleFilters, ...digitalFilters];
  return allFilters.find(f => f.value === type)?.icon || '📦';
}

function ListingCard({ listing, onClick }: { listing: MarketplaceListing; onClick: () => void }) {
  const isDigital = listing.category === 'digital_goods';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="omega-card overflow-hidden group cursor-pointer"
      onClick={onClick}
    >
      <div className="aspect-[3/4] relative bg-slate-800">
        {listing.imageUrl ? (
          <img
            src={listing.imageUrl}
            alt={listing.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-6xl text-slate-600">
            {getTypeIcon(listing.type)}
          </div>
        )}

        {/* Digital/Physical Badge */}
        <span className={`absolute top-3 left-3 px-2 py-1 rounded-full text-xs font-medium ${
          isDigital ? 'bg-cyan-500/80 text-white' : 'bg-amber-500/80 text-white'
        }`}>
          {isDigital ? 'Digital' : 'Physical'}
        </span>

        {/* Grade Badge (for collectibles) */}
        {listing.grade && (
          <span className={`grade-badge absolute top-3 right-3 ${getGradeClass(listing.grade)}`}>
            {listing.grade.toFixed(1)}
          </span>
        )}

        {/* License Badge (for digital goods) */}
        {listing.license && (
          <span className={`absolute top-3 right-3 px-2 py-1 rounded-full text-xs font-medium ${
            listing.license === 'exclusive' ? 'bg-purple-500/80 text-white' :
            listing.license === 'commercial' ? 'bg-green-500/80 text-white' :
            'bg-slate-500/80 text-white'
          }`}>
            {listing.license}
          </span>
        )}

        {/* Preview overlay for digital goods */}
        {isDigital && listing.previewUrl && (
          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <button className="px-4 py-2 bg-purple-600 rounded-lg text-white text-sm font-medium">
              Preview
            </button>
          </div>
        )}

        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>

      <div className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-lg">{getTypeIcon(listing.type)}</span>
          <span className="text-xs text-slate-500 capitalize">{listing.type.replace('_', ' ')}</span>
        </div>
        <h3 className="font-semibold text-white mb-1 truncate">{listing.title}</h3>
        <div className="flex items-center gap-2 mb-2">
          {listing.sellerAvatar && (
            <img src={listing.sellerAvatar} alt="" className="w-5 h-5 rounded-full" />
          )}
          <p className="text-sm text-slate-400">by {listing.sellerName}</p>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-lg font-bold text-green-400">
            ${listing.askingPrice.toLocaleString()}
          </span>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            {listing.views !== undefined && <span>👁️ {listing.views}</span>}
            {listing.favorites !== undefined && <span>❤️ {listing.favorites}</span>}
          </div>
        </div>
        {listing.tags && listing.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {listing.tags.slice(0, 3).map(tag => (
              <span key={tag} className="px-2 py-0.5 bg-slate-700/50 rounded text-xs text-slate-400">
                #{tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

function CreateListingModal({ onClose, onSuccess }: { onClose: () => void; onSuccess?: () => void }) {
  const router = useRouter();
  const { user } = useAuthStore();
  const [category, setCategory] = useState<MarketplaceCategory>('collectibles');
  const [listableItems, setListableItems] = useState<Collectible[]>([]);
  const [loadingItems, setLoadingItems] = useState(false);
  const [selectedItem, setSelectedItem] = useState<Collectible | null>(null);
  const [price, setPrice] = useState('');
  const [acceptsOffers, setAcceptsOffers] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  // Load listable collectibles when category is collectibles
  useEffect(() => {
    if (category === 'collectibles' && user) {
      setLoadingItems(true);
      getListableCollectibles(user.uid)
        .then(setListableItems)
        .catch(console.error)
        .finally(() => setLoadingItems(false));
    }
  }, [category, user]);

  const handleCreateListing = async () => {
    if (!selectedItem || !user) return;

    const askingPrice = parseFloat(price);
    if (isNaN(askingPrice) || askingPrice <= 0) {
      setError('Please enter a valid price');
      return;
    }

    setCreating(true);
    setError('');
    try {
      const listingId = await createCollectibleListing(
        selectedItem,
        askingPrice,
        user,
        { acceptsOffers }
      );
      onSuccess?.();
      onClose();
      router.push(`/marketplace/${listingId}`);
    } catch (err: any) {
      setError(err.message || 'Failed to create listing');
    } finally {
      setCreating(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="omega-card p-6 max-w-lg w-full max-h-[80vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white">Create Listing</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white">✕</button>
        </div>

        {/* Category Selection */}
        <div className="mb-6">
          <label className="block text-sm text-slate-400 mb-2">What are you selling?</label>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => { setCategory('collectibles'); setSelectedItem(null); }}
              className={`p-4 rounded-lg border transition-all ${
                category === 'collectibles'
                  ? 'border-purple-500 bg-purple-500/20'
                  : 'border-slate-600 bg-slate-800/50 hover:border-slate-500'
              }`}
            >
              <span className="text-2xl mb-2 block">🎯</span>
              <span className="text-white font-medium">Collectible</span>
              <p className="text-xs text-slate-400 mt-1">Comics, Cards, Coins, etc.</p>
            </button>
            <button
              onClick={() => { setCategory('digital_goods'); setSelectedItem(null); }}
              className={`p-4 rounded-lg border transition-all ${
                category === 'digital_goods'
                  ? 'border-cyan-500 bg-cyan-500/20'
                  : 'border-slate-600 bg-slate-800/50 hover:border-slate-500'
              }`}
            >
              <span className="text-2xl mb-2 block">💾</span>
              <span className="text-white font-medium">Digital Good</span>
              <p className="text-xs text-slate-400 mt-1">Voice Clones, Images, Videos</p>
            </button>
          </div>
        </div>

        {category === 'collectibles' ? (
          <div className="space-y-4">
            {!user ? (
              <div className="text-center py-6">
                <p className="text-slate-400 mb-4">Sign in to list your collectibles</p>
                <button onClick={onClose} className="omega-button-secondary">Sign In</button>
              </div>
            ) : loadingItems ? (
              <div className="text-center py-6">
                <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full mx-auto mb-2" />
                <p className="text-slate-400 text-sm">Loading your collection...</p>
              </div>
            ) : listableItems.length === 0 ? (
              <div className="text-center py-6">
                <div className="text-4xl mb-2">📦</div>
                <p className="text-slate-400 mb-2">No graded collectibles available to list</p>
                <p className="text-xs text-slate-500 mb-4">Items must be graded before listing</p>
                <a href="/collection" className="omega-button-secondary inline-block">Go to Collection</a>
              </div>
            ) : selectedItem ? (
              /* Pricing form for selected item */
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg">
                  {selectedItem.imageUrl ? (
                    <img src={selectedItem.imageUrl} alt="" className="w-16 h-20 object-cover rounded" />
                  ) : (
                    <div className="w-16 h-20 bg-slate-700 rounded flex items-center justify-center text-xl">📦</div>
                  )}
                  <div className="flex-1">
                    <h4 className="text-white font-medium">{selectedItem.title}</h4>
                    <p className="text-sm text-slate-400 capitalize">{selectedItem.type}</p>
                    {selectedItem.grade && (
                      <span className={`inline-block mt-1 px-2 py-0.5 rounded text-xs ${getGradeClass(selectedItem.grade)}`}>
                        Grade: {selectedItem.grade.toFixed(1)}
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => setSelectedItem(null)}
                    className="text-slate-400 hover:text-white"
                  >
                    ✕
                  </button>
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-2">Asking Price ($)</label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={price}
                      onChange={(e) => setPrice(e.target.value)}
                      className="omega-input pl-8"
                      placeholder="0.00"
                    />
                  </div>
                  {selectedItem.estimatedValue && (
                    <p className="text-xs text-slate-500 mt-1">
                      Estimated: ${selectedItem.estimatedValue.toLocaleString()}
                    </p>
                  )}
                </div>

                <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                  <div>
                    <div className="text-white text-sm">Accept Offers</div>
                    <div className="text-xs text-slate-500">Allow buyers to negotiate</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setAcceptsOffers(!acceptsOffers)}
                    className={`w-10 h-5 rounded-full transition-colors ${acceptsOffers ? 'bg-purple-600' : 'bg-slate-600'}`}
                  >
                    <div className={`w-4 h-4 bg-white rounded-full transition-transform ${acceptsOffers ? 'translate-x-5' : 'translate-x-0.5'}`} />
                  </button>
                </div>

                <div className="p-3 bg-slate-800/50 rounded-lg text-sm text-slate-400">
                  <span className="text-slate-300">Platform fee:</span> 5% on sale
                </div>

                {error && (
                  <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
                    {error}
                  </div>
                )}

                <button
                  onClick={handleCreateListing}
                  disabled={creating || !price}
                  className="omega-button w-full disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {creating ? (
                    <span className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Creating...
                    </span>
                  ) : (
                    `List for $${price || '0'}`
                  )}
                </button>
              </div>
            ) : (
              /* Collection picker */
              <div>
                <label className="block text-sm text-slate-400 mb-3">Select from your collection:</label>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {listableItems.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => {
                        setSelectedItem(item);
                        setPrice(item.estimatedValue?.toString() || '');
                      }}
                      className="w-full flex items-center gap-3 p-3 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg transition-colors text-left"
                    >
                      {item.imageUrl ? (
                        <img src={item.imageUrl} alt="" className="w-12 h-16 object-cover rounded" />
                      ) : (
                        <div className="w-12 h-16 bg-slate-700 rounded flex items-center justify-center">📦</div>
                      )}
                      <div className="flex-1 min-w-0">
                        <h4 className="text-white font-medium truncate">{item.title}</h4>
                        <p className="text-sm text-slate-400 capitalize">{item.type}</p>
                      </div>
                      {item.grade && (
                        <span className={`px-2 py-1 rounded text-xs ${getGradeClass(item.grade)}`}>
                          {item.grade.toFixed(1)}
                        </span>
                      )}
                      {item.estimatedValue && (
                        <span className="text-green-400 text-sm font-medium">
                          ${item.estimatedValue.toLocaleString()}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-2">Type</label>
              <select className="omega-input">
                {digitalFilters.filter(f => f.value !== 'all').map(f => (
                  <option key={f.value} value={f.value}>{f.icon} {f.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-2">Title</label>
              <input type="text" className="omega-input" placeholder="Enter title..." />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-2">Description</label>
              <textarea className="omega-input h-24" placeholder="Describe your digital good..." />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-2">Upload File</label>
              <div className="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center hover:border-purple-500 transition-colors cursor-pointer">
                <span className="text-3xl mb-2 block">📤</span>
                <p className="text-slate-400">Drop file here or click to upload</p>
                <p className="text-xs text-slate-500 mt-1">Max 500MB</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Price ($)</label>
                <input type="number" className="omega-input" placeholder="0.00" />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-2">License</label>
                <select className="omega-input">
                  <option value="personal">Personal Use</option>
                  <option value="commercial">Commercial Use</option>
                  <option value="exclusive">Exclusive Rights</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-2">Tags (comma separated)</label>
              <input type="text" className="omega-input" placeholder="ai, voice, custom..." />
            </div>
            <button className="omega-button w-full">Create Listing</button>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}

export default function MarketplacePage() {
  const router = useRouter();
  const { listings, filter, loading, setListings, setFilter, setLoading } = useMarketplaceStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<MarketplaceCategory | 'all' | 'services'>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    const loadListings = async () => {
      setLoading(true);
      try {
        const category = categoryFilter === 'all' || categoryFilter === 'services' ? undefined : categoryFilter;
        const type = typeFilter === 'all' ? undefined : typeFilter;
        const result = await getMarketplaceListings(category, type as any);
        setListings(result.items);
      } catch (error) {
        console.error('Error loading marketplace:', error);
      } finally {
        setLoading(false);
      }
    };
    loadListings();
  }, [categoryFilter, typeFilter, setListings, setLoading]);

  const filteredListings = listings.filter(listing =>
    listing.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    listing.sellerName.toLowerCase().includes(searchQuery.toLowerCase()) ||
    listing.tags?.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const currentTypeFilters = categoryFilter === 'digital_goods'
    ? digitalFilters
    : categoryFilter === 'collectibles'
      ? collectibleFilters
      : [...collectibleFilters.slice(0, 1), ...collectibleFilters.slice(1), ...digitalFilters.slice(1)];

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">Marketplace</h1>
          <p className="text-slate-400">
            Buy and sell collectibles & digital goods from verified creators
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="omega-button"
        >
          + Create Listing
        </button>
      </div>

      {/* Category Tabs - Two Rows */}
      <div className="space-y-3 mb-6">
        {/* Row 1: Main Categories */}
        <div className="flex flex-wrap gap-2">
          {categoryTabs.map((tab) => (
            <button
              key={tab.value}
              onClick={() => {
                if (tab.value === 'services') {
                  router.push('/services');
                } else {
                  setCategoryFilter(tab.value);
                  setTypeFilter('all');
                }
              }}
              className={`px-6 py-3 rounded-lg text-sm font-medium transition-all ${
                categoryFilter === tab.value
                  ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-900/50'
                  : tab.value === 'services'
                    ? 'bg-gradient-to-r from-cyan-800 to-teal-800 text-cyan-300 hover:from-cyan-700 hover:to-teal-700'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
              {tab.value === 'services' && (
                <span className="ml-2 px-1.5 py-0.5 bg-cyan-500/30 rounded text-[10px] uppercase">New</span>
              )}
            </button>
          ))}
        </div>

        {/* Row 2: Type Filters (shown below main categories) */}
        <div className="flex flex-wrap gap-2">
          {(categoryFilter === 'all' ? collectibleFilters :
            categoryFilter === 'collectibles' ? collectibleFilters :
            categoryFilter === 'services' ? [] : digitalFilters
          ).map((type) => (
            <button
              key={type.value}
              onClick={() => setTypeFilter(type.value)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                typeFilter === type.value
                  ? 'bg-purple-600/50 text-white border border-purple-500/50'
                  : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50 border border-transparent'
              }`}
            >
              <span className="mr-1">{type.icon}</span>
              {type.label}
            </button>
          ))}
        </div>
      </div>

      {/* Search Bar */}
      <div className="mb-8">
        <input
          type="text"
          placeholder="Search listings, sellers, or tags..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="omega-input w-full max-w-md"
        />
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="omega-card p-4 text-center">
          <div className="text-2xl font-bold text-white">{filteredListings.length}</div>
          <div className="text-xs text-slate-400">Active Listings</div>
        </div>
        <div className="omega-card p-4 text-center">
          <div className="text-2xl font-bold text-green-400">
            ${filteredListings.reduce((sum, l) => sum + l.askingPrice, 0).toLocaleString()}
          </div>
          <div className="text-xs text-slate-400">Total Value</div>
        </div>
        <div className="omega-card p-4 text-center">
          <div className="text-2xl font-bold text-purple-400">
            {filteredListings.filter(l => l.category === 'collectibles').length}
          </div>
          <div className="text-xs text-slate-400">Collectibles</div>
        </div>
        <div className="omega-card p-4 text-center">
          <div className="text-2xl font-bold text-cyan-400">
            {filteredListings.filter(l => l.category === 'digital_goods').length}
          </div>
          <div className="text-xs text-slate-400">Digital Goods</div>
        </div>
      </div>

      {/* Listings Grid */}
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="omega-card animate-pulse">
              <div className="aspect-[3/4] bg-slate-700" />
              <div className="p-4 space-y-2">
                <div className="h-4 bg-slate-700 rounded w-3/4" />
                <div className="h-3 bg-slate-700 rounded w-1/2" />
                <div className="h-5 bg-slate-700 rounded w-1/3" />
              </div>
            </div>
          ))}
        </div>
      ) : filteredListings.length > 0 ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
          {filteredListings.map((listing, index) => (
            <motion.div
              key={listing.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <ListingCard
                listing={listing}
                onClick={() => router.push(`/marketplace/${listing.id}`)}
              />
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="text-center py-20">
          <div className="text-6xl mb-4">
            {categoryFilter === 'digital_goods' ? '💾' : categoryFilter === 'collectibles' ? '📦' : '🏪'}
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">No listings found</h3>
          <p className="text-slate-400 mb-6">
            {categoryFilter === 'digital_goods'
              ? 'No digital goods are currently for sale.'
              : categoryFilter === 'collectibles'
                ? 'No collectibles are currently for sale.'
                : 'The marketplace is empty.'}
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="omega-button"
          >
            Be the first to list!
          </button>
        </div>
      )}

      {/* Create Listing Modal */}
      <AnimatePresence>
        {showCreateModal && (
          <CreateListingModal
            onClose={() => setShowCreateModal(false)}
            onSuccess={() => {
              // Refresh listings after creating new one
              const category = categoryFilter === 'all' || categoryFilter === 'services' ? undefined : categoryFilter;
              const type = typeFilter === 'all' ? undefined : typeFilter;
              getMarketplaceListings(category, type as any).then(result => setListings(result.items));
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
