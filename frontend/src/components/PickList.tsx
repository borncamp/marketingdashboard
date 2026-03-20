import { useState, useMemo } from 'react';
import { ordersApi } from '../services/api';

interface PickItem {
  product_title: string;
  variant_title: string | null;
  total_quantity: number;
}

type SortKey = 'product_title' | 'total_quantity';
type SortDir = 'asc' | 'desc';

const parseOrderNumbers = (input: string): number[] => {
  return input
    .split(/[\s,]+/)
    .map((s) => s.replace(/^#/, '').trim())
    .filter((s) => /^\d+$/.test(s))
    .map(Number)
    .filter((n, i, arr) => arr.indexOf(n) === i); // dedupe
};

export default function PickList() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<PickItem[]>([]);
  const [found, setFound] = useState<number[]>([]);
  const [submitted, setSubmitted] = useState<number[]>([]);
  const [sortKey, setSortKey] = useState<SortKey>('product_title');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [copied, setCopied] = useState(false);

  const parsed = useMemo(() => parseOrderNumbers(input), [input]);
  const missing = submitted.filter((n) => !found.includes(n));

  const handleGenerate = async () => {
    if (parsed.length === 0) return;
    setLoading(true);
    setError(null);
    setCopied(false);
    try {
      const result = await ordersApi.getPickList(parsed);
      setItems(result.items);
      setFound(result.found);
      setSubmitted(parsed);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate pick list');
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortKey(key); setSortDir(key === 'product_title' ? 'asc' : 'desc'); }
  };

  const sorted = useMemo(() => {
    return [...items].sort((a, b) => {
      if (sortKey === 'product_title') {
        const cmp = `${a.product_title} ${a.variant_title ?? ''}`.localeCompare(
          `${b.product_title} ${b.variant_title ?? ''}`
        );
        return sortDir === 'asc' ? cmp : -cmp;
      }
      const diff = a.total_quantity - b.total_quantity;
      return sortDir === 'asc' ? diff : -diff;
    });
  }, [items, sortKey, sortDir]);

  const totalUnits = items.reduce((s, i) => s + i.total_quantity, 0);

  const handleCopy = () => {
    const text = sorted
      .map((r) => `${r.total_quantity}x ${r.product_title}${r.variant_title ? ` (${r.variant_title})` : ''}`)
      .join('\n');
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const SortIndicator = ({ col }: { col: SortKey }) =>
    sortKey === col ? (
      <span className="ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>
    ) : (
      <span className="ml-1 text-gray-300">↕</span>
    );

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Input section */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Order Numbers
          <span className="ml-2 text-gray-400 font-normal">(comma or space separated, # prefix optional)</span>
        </label>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleGenerate(); }}
          placeholder="123, 124, 125  or  #123 #124 #125"
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
        />
        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-gray-500">
            {parsed.length > 0 ? `${parsed.length} order${parsed.length !== 1 ? 's' : ''} entered` : 'No valid order numbers yet'}
          </span>
          <button
            onClick={handleGenerate}
            disabled={parsed.length === 0 || loading}
            className="px-5 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Loading…' : 'Generate Pick List'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      {/* Results */}
      {!loading && items.length > 0 && (
        <>
          {/* Summary bar */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <span className="text-sm font-medium text-gray-700">
                Found{' '}
                <span className="font-bold text-gray-900">{found.length}</span> of{' '}
                <span className="font-bold text-gray-900">{submitted.length}</span> orders
              </span>
              {missing.length > 0 && (
                <div className="flex items-center space-x-1">
                  <span className="text-xs text-amber-700 bg-amber-100 border border-amber-200 rounded px-2 py-0.5">
                    Not found: {missing.map((n) => `#${n}`).join(', ')}
                  </span>
                </div>
              )}
              <span className="text-sm text-gray-500">
                — <span className="font-semibold">{sorted.length}</span> SKUs,{' '}
                <span className="font-semibold">{totalUnits}</span> total units
              </span>
            </div>
            <button
              onClick={handleCopy}
              className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <span>{copied ? '✓ Copied' : '📋 Copy List'}</span>
            </button>
          </div>

          {/* Pick list table */}
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-800 select-none"
                    onClick={() => handleSort('product_title')}
                  >
                    Product <SortIndicator col="product_title" />
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Variant
                  </th>
                  <th
                    className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-800 select-none"
                    onClick={() => handleSort('total_quantity')}
                  >
                    Qty <SortIndicator col="total_quantity" />
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sorted.map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-6 py-3 text-sm font-medium text-gray-900">{row.product_title}</td>
                    <td className="px-6 py-3 text-sm text-gray-500">{row.variant_title || '—'}</td>
                    <td className="px-6 py-3 text-sm text-right font-semibold text-blue-700">
                      {row.total_quantity}
                    </td>
                  </tr>
                ))}
                <tr className="bg-gray-50 font-semibold">
                  <td className="px-6 py-3 text-sm text-gray-900">Total</td>
                  <td className="px-6 py-3"></td>
                  <td className="px-6 py-3 text-sm text-right font-bold text-blue-800">{totalUnits}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}

      {!loading && submitted.length > 0 && items.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <p className="text-yellow-800">No items found for the entered order numbers.</p>
        </div>
      )}
    </div>
  );
}
