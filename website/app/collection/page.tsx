'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { getUserCollectibles, Collectible, addCollectible, updateCollectible, createListing, createCollectibleListing, isCollectibleListed } from '@/lib/firebase';
import { useAuthStore, useCollectionStore } from '@/lib/store';

function getGradeClass(grade?: number): string {
  if (!grade) return '';
  if (grade >= 9.8) return 'grade-gem';
  if (grade >= 9.4) return 'grade-mint';
  if (grade >= 9.0) return 'grade-nm';
  if (grade >= 8.0) return 'grade-vf';
  if (grade >= 6.0) return 'grade-fine';
  return 'grade-low';
}

interface ItemActionsModalProps {
  item: Collectible;
  onClose: () => void;
  onRegrade: () => void;
  onListForSale: () => void;
  onViewAnalysis: () => void;
}

function ItemActionsModal({ item, onClose, onRegrade, onListForSale, onViewAnalysis }: ItemActionsModalProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="omega-card p-6 max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-xl font-bold text-white mb-4">{item.title}</h3>

        {/* Current Grade Display */}
        {item.grade && (
          <div className="flex items-center gap-4 mb-6 p-4 bg-slate-800/50 rounded-lg">
            <span className={`grade-badge text-lg ${getGradeClass(item.grade)}`}>
              {item.grade.toFixed(1)}
            </span>
            <div>
              <div className="text-sm text-slate-400">Current Grade</div>
              <div className="text-white font-semibold">
                {item.grade >= 9.8 ? 'Gem Mint' :
                 item.grade >= 9.4 ? 'Near Mint+' :
                 item.grade >= 9.0 ? 'Near Mint' :
                 item.grade >= 8.0 ? 'Very Fine' :
                 item.grade >= 6.0 ? 'Fine' : 'Good'}
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons - Matching Desktop Program */}
        <div className="space-y-3">
          <button
            onClick={onRegrade}
            className="w-full omega-button flex items-center justify-center gap-2"
          >
            <span>🔄</span>
            <span>Re-Grade with AI</span>
          </button>

          <button
            onClick={onViewAnalysis}
            className="w-full omega-button-secondary flex items-center justify-center gap-2"
          >
            <span>📊</span>
            <span>View Full Analysis</span>
          </button>

          <button
            onClick={() => {}}
            className="w-full omega-button-secondary flex items-center justify-center gap-2"
          >
            <span>🤖</span>
            <span>Get AI Commentary (BREE/RAISTLIN)</span>
          </button>

          <button
            onClick={() => {}}
            className="w-full omega-button-secondary flex items-center justify-center gap-2"
          >
            <span>💰</span>
            <span>Check Market Value</span>
          </button>

          <button
            onClick={() => {}}
            className="w-full omega-button-secondary flex items-center justify-center gap-2"
          >
            <span>🔗</span>
            <span>CGC Lookup</span>
          </button>

          <hr className="border-slate-700 my-4" />

          <button
            onClick={onListForSale}
            className="w-full bg-green-600 hover:bg-green-500 text-white px-6 py-3 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all"
          >
            <span>🏷️</span>
            <span>{item.forSale ? 'Update Listing' : 'List for Sale'}</span>
          </button>

          <button
            onClick={() => {}}
            className="w-full omega-button-secondary flex items-center justify-center gap-2"
          >
            <span>📤</span>
            <span>Export Report</span>
          </button>
        </div>

        <button
          onClick={onClose}
          className="mt-6 w-full text-slate-400 hover:text-white transition-colors"
        >
          Close
        </button>
      </motion.div>
    </motion.div>
  );
}

function RegradeModal({ item, onClose }: { item: Collectible; onClose: () => void }) {
  const [grading, setGrading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleRegrade = async () => {
    setGrading(true);
    // Simulate AI grading - in production this calls Firebase Function
    await new Promise(resolve => setTimeout(resolve, 3000));
    setResult({
      newGrade: 9.4,
      confidence: 94,
      models: ['Claude', 'Gemini', 'GPT-4'],
      factors: [
        { name: 'Cover Condition', score: 9.5, notes: 'Minor wear on corners' },
        { name: 'Spine Condition', score: 9.2, notes: 'Light stress marks' },
        { name: 'Page Quality', score: 9.6, notes: 'Off-white to white pages' },
        { name: 'Centering', score: 9.3, notes: 'Slightly off-center' },
      ]
    });
    setGrading(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="omega-card p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-xl font-bold text-white mb-4">
          🔄 AI Re-Grading: {item.title}
        </h3>

        {!result ? (
          <div className="text-center py-8">
            {grading ? (
              <>
                <div className="animate-spin w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full mx-auto mb-4" />
                <p className="text-slate-400">Analyzing with multi-model consensus...</p>
                <p className="text-sm text-slate-500 mt-2">Claude + Gemini + GPT-4</p>
              </>
            ) : (
              <>
                <p className="text-slate-400 mb-6">
                  Re-analyze this item using our AI consensus system?
                  This will use Claude, Gemini, and GPT-4 for accurate grading.
                </p>
                <button onClick={handleRegrade} className="omega-button">
                  Start AI Analysis
                </button>
              </>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {/* New Grade */}
            <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg">
              <div>
                <div className="text-sm text-slate-400">New Grade</div>
                <div className="text-2xl font-bold text-white">{result.newGrade.toFixed(1)}</div>
              </div>
              <span className={`grade-badge text-xl ${getGradeClass(result.newGrade)}`}>
                {result.newGrade.toFixed(1)}
              </span>
            </div>

            {/* Confidence */}
            <div className="p-4 bg-slate-800/50 rounded-lg">
              <div className="flex justify-between mb-2">
                <span className="text-slate-400">AI Confidence</span>
                <span className="text-green-400 font-semibold">{result.confidence}%</span>
              </div>
              <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-green-500 to-emerald-400"
                  style={{ width: `${result.confidence}%` }}
                />
              </div>
            </div>

            {/* Models Used */}
            <div className="flex gap-2">
              {result.models.map((model: string) => (
                <span key={model} className="px-3 py-1 bg-purple-500/20 text-purple-300 rounded-full text-sm">
                  {model}
                </span>
              ))}
            </div>

            {/* Grading Factors */}
            <div className="space-y-2">
              <h4 className="font-semibold text-white">Grading Factors</h4>
              {result.factors.map((factor: any) => (
                <div key={factor.name} className="p-3 bg-slate-800/30 rounded-lg">
                  <div className="flex justify-between mb-1">
                    <span className="text-slate-300">{factor.name}</span>
                    <span className="font-semibold text-cyan-400">{factor.score.toFixed(1)}</span>
                  </div>
                  <p className="text-sm text-slate-500">{factor.notes}</p>
                </div>
              ))}
            </div>

            <div className="flex gap-3 mt-6">
              <button className="flex-1 omega-button">
                Accept New Grade
              </button>
              <button onClick={onClose} className="flex-1 omega-button-secondary">
                Keep Original
              </button>
            </div>
          </div>
        )}

        <button
          onClick={onClose}
          className="mt-4 w-full text-slate-400 hover:text-white transition-colors text-sm"
        >
          Cancel
        </button>
      </motion.div>
    </motion.div>
  );
}

interface ListForSaleModalProps {
  item: Collectible;
  user: { uid: string; displayName?: string | null; photoURL?: string | null };
  onClose: () => void;
  onSuccess: () => void;
}

function ListForSaleModal({ item, user, onClose, onSuccess }: ListForSaleModalProps) {
  const [price, setPrice] = useState(item.estimatedValue?.toString() || '');
  const [acceptsOffers, setAcceptsOffers] = useState(true);
  const [minimumOffer, setMinimumOffer] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const askingPrice = parseFloat(price);
    if (isNaN(askingPrice) || askingPrice <= 0) {
      setError('Please enter a valid price');
      return;
    }

    if (!item.grade || item.grade <= 0) {
      setError('Only graded items can be listed. Please grade this item first.');
      return;
    }

    setLoading(true);
    try {
      const listingId = await createCollectibleListing(
        item,
        askingPrice,
        user,
        {
          acceptsOffers,
          minimumOffer: minimumOffer ? parseFloat(minimumOffer) : undefined,
        }
      );

      onSuccess();
      router.push(`/marketplace/${listingId}`);
    } catch (err: any) {
      setError(err.message || 'Failed to create listing');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="omega-card p-6 max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-xl font-bold text-white mb-4">
          List on Marketplace
        </h3>

        {/* Item Preview */}
        <div className="flex gap-4 mb-6 p-4 bg-slate-800/50 rounded-lg">
          {item.imageUrl ? (
            <img
              src={item.imageUrl}
              alt={item.title}
              className="w-20 h-24 object-cover rounded"
            />
          ) : (
            <div className="w-20 h-24 bg-slate-700 rounded flex items-center justify-center text-2xl">
              📦
            </div>
          )}
          <div className="flex-1">
            <h4 className="font-semibold text-white">{item.title}</h4>
            <p className="text-sm text-slate-400 capitalize">{item.type}</p>
            {item.grade && (
              <span className={`grade-badge mt-2 inline-block ${getGradeClass(item.grade)}`}>
                Grade: {item.grade.toFixed(1)}
              </span>
            )}
          </div>
        </div>

        {!item.grade || item.grade <= 0 ? (
          <div className="text-center py-4">
            <div className="text-4xl mb-2">⚠️</div>
            <p className="text-yellow-400 font-semibold mb-2">Grading Required</p>
            <p className="text-slate-400 text-sm mb-4">
              This item needs to be graded before it can be listed on the marketplace.
            </p>
            <button onClick={onClose} className="omega-button">
              Grade This Item First
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Price Input */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Asking Price ($)
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  className="w-full pl-8 pr-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                  placeholder="0.00"
                  required
                />
              </div>
              {item.estimatedValue && (
                <p className="text-xs text-slate-500 mt-1">
                  Estimated value: ${item.estimatedValue.toLocaleString()}
                </p>
              )}
            </div>

            {/* Accept Offers Toggle */}
            <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
              <div>
                <div className="text-white font-medium">Accept Offers</div>
                <div className="text-xs text-slate-400">Allow buyers to make offers</div>
              </div>
              <button
                type="button"
                onClick={() => setAcceptsOffers(!acceptsOffers)}
                className={`w-12 h-6 rounded-full transition-colors ${
                  acceptsOffers ? 'bg-purple-600' : 'bg-slate-600'
                }`}
              >
                <div
                  className={`w-5 h-5 bg-white rounded-full transition-transform ${
                    acceptsOffers ? 'translate-x-6' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>

            {/* Minimum Offer (if accepting offers) */}
            {acceptsOffers && (
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Minimum Offer (optional)
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={minimumOffer}
                    onChange={(e) => setMinimumOffer(e.target.value)}
                    className="w-full pl-8 pr-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                    placeholder="No minimum"
                  />
                </div>
              </div>
            )}

            {error && (
              <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
                {error}
              </div>
            )}

            {/* Platform Fee Notice */}
            <div className="p-3 bg-slate-800/50 rounded-lg text-sm text-slate-400">
              <span className="text-slate-300">Platform fee:</span> 5% on sale
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-green-600 hover:bg-green-500 disabled:bg-green-800 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-semibold transition-all flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Creating Listing...
                </>
              ) : (
                <>
                  <span>🏷️</span>
                  <span>List for ${price || '0'}</span>
                </>
              )}
            </button>
          </form>
        )}

        <button
          onClick={onClose}
          className="mt-4 w-full text-slate-400 hover:text-white transition-colors text-sm"
        >
          Cancel
        </button>
      </motion.div>
    </motion.div>
  );
}

function CollectibleCard({ item, onSelect }: { item: Collectible; onSelect: () => void }) {
  const typeIcons: Record<string, string> = {
    comic: '📚',
    card: '🎴',
    coin: '🪙',
    stamp: '📮',
    vinyl: '💿',
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="omega-card overflow-hidden group cursor-pointer"
      onClick={onSelect}
    >
      <div className="aspect-[3/4] relative bg-slate-800">
        {item.imageUrl ? (
          <img
            src={item.imageUrl}
            alt={item.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-5xl text-slate-600">
            {typeIcons[item.type] || '📦'}
          </div>
        )}
        {item.grade && (
          <span className={`grade-badge absolute top-3 right-3 ${getGradeClass(item.grade)}`}>
            {item.grade.toFixed(1)}
          </span>
        )}
        {item.forSale && (
          <div className="absolute top-3 left-3 bg-green-500 text-white text-xs px-2 py-1 rounded-full">
            For Sale
          </div>
        )}

        {/* Hover Overlay with Quick Actions */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-4">
          <div className="space-y-2">
            <button className="w-full bg-purple-600/90 hover:bg-purple-500 text-white text-sm py-2 rounded-lg transition-colors">
              🔄 Re-Grade
            </button>
            <button className="w-full bg-slate-700/90 hover:bg-slate-600 text-white text-sm py-2 rounded-lg transition-colors">
              📊 Analysis
            </button>
          </div>
        </div>
      </div>
      <div className="p-4">
        <h3 className="font-semibold text-white mb-1 truncate">{item.title}</h3>
        <p className="text-sm text-slate-400 capitalize mb-2">{item.type}</p>
        {item.estimatedValue && (
          <p className="text-green-400 font-semibold">
            ${item.estimatedValue.toLocaleString()}
          </p>
        )}
      </div>
    </motion.div>
  );
}

export default function CollectionPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuthStore();
  const { items, loading, setItems, setLoading } = useCollectionStore();
  const [filter, setFilter] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<Collectible | null>(null);
  const [showRegrade, setShowRegrade] = useState(false);
  const [showListForSale, setShowListForSale] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/');
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    const loadCollection = async () => {
      if (!user) return;
      setLoading(true);
      try {
        const result = await getUserCollectibles(user.uid);
        setItems(result.items);
      } catch (error) {
        console.error('Error loading collection:', error);
      } finally {
        setLoading(false);
      }
    };
    if (user) {
      loadCollection();
    }
  }, [user, setItems, setLoading]);

  if (authLoading) {
    return (
      <div className="container mx-auto px-4 py-20 text-center">
        <div className="animate-spin w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full mx-auto" />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const filteredItems = filter
    ? items.filter(item => item.type === filter)
    : items;

  const stats = {
    total: items.length,
    totalValue: items.reduce((sum, item) => sum + (item.estimatedValue || 0), 0),
    avgGrade: items.filter(i => i.grade).reduce((sum, item) => sum + (item.grade || 0), 0) / items.filter(i => i.grade).length || 0,
    forSale: items.filter(item => item.forSale).length,
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">My Collection</h1>
          <p className="text-slate-400">
            Manage, grade, and showcase your collectibles
          </p>
        </div>
        <div className="flex gap-3">
          <button className="omega-button-secondary">
            📤 Export All
          </button>
          <button className="omega-button">
            + Add Item
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="omega-card p-4 text-center">
          <div className="text-3xl font-bold text-white">{stats.total}</div>
          <div className="text-sm text-slate-400">Total Items</div>
        </div>
        <div className="omega-card p-4 text-center">
          <div className="text-3xl font-bold text-green-400">
            ${stats.totalValue.toLocaleString()}
          </div>
          <div className="text-sm text-slate-400">Total Value</div>
        </div>
        <div className="omega-card p-4 text-center">
          <div className="text-3xl font-bold text-cyan-400">
            {stats.avgGrade.toFixed(1)}
          </div>
          <div className="text-sm text-slate-400">Avg Grade</div>
        </div>
        <div className="omega-card p-4 text-center">
          <div className="text-3xl font-bold text-purple-400">{stats.forSale}</div>
          <div className="text-sm text-slate-400">For Sale</div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-2 mb-6">
        {[
          { value: null, label: 'All', icon: '🎯' },
          { value: 'comic', label: 'Comics', icon: '📚' },
          { value: 'card', label: 'Cards', icon: '🎴' },
          { value: 'coin', label: 'Coins', icon: '🪙' },
          { value: 'stamp', label: 'Stamps', icon: '📮' },
          { value: 'vinyl', label: 'Vinyl', icon: '💿' },
        ].map((tab) => (
          <button
            key={tab.value || 'all'}
            onClick={() => setFilter(tab.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              filter === tab.value
                ? 'bg-purple-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            <span className="mr-2">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Collection Grid */}
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="omega-card animate-pulse">
              <div className="aspect-[3/4] bg-slate-700" />
              <div className="p-4 space-y-2">
                <div className="h-4 bg-slate-700 rounded w-3/4" />
                <div className="h-3 bg-slate-700 rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      ) : filteredItems.length > 0 ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
          {filteredItems.map((item) => (
            <CollectibleCard
              key={item.id}
              item={item}
              onSelect={() => setSelectedItem(item)}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-20">
          <div className="text-6xl mb-4">📦</div>
          <h3 className="text-xl font-semibold text-white mb-2">No items yet</h3>
          <p className="text-slate-400 mb-6">
            Start adding collectibles to your collection
          </p>
          <button className="omega-button">
            + Add Your First Item
          </button>
        </div>
      )}

      {/* Item Actions Modal */}
      <AnimatePresence>
        {selectedItem && !showRegrade && !showListForSale && (
          <ItemActionsModal
            item={selectedItem}
            onClose={() => setSelectedItem(null)}
            onRegrade={() => setShowRegrade(true)}
            onListForSale={() => setShowListForSale(true)}
            onViewAnalysis={() => {}}
          />
        )}
        {selectedItem && showRegrade && (
          <RegradeModal
            item={selectedItem}
            onClose={() => {
              setShowRegrade(false);
              setSelectedItem(null);
            }}
          />
        )}
        {selectedItem && showListForSale && user && (
          <ListForSaleModal
            item={selectedItem}
            user={user}
            onClose={() => {
              setShowListForSale(false);
              setSelectedItem(null);
            }}
            onSuccess={() => {
              setShowListForSale(false);
              setSelectedItem(null);
              // Refresh collection to show updated status
              if (user) {
                getUserCollectibles(user.uid).then(result => setItems(result.items));
              }
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
