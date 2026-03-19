import { useState, useEffect, useMemo } from 'react';
import { ordersApi } from '../services/api';

interface ProductSalesRow {
  product_title: string;
  total_quantity: number;
  gross_revenue: number;
}

type SortKey = 'total_quantity' | 'gross_revenue';
type SortDir = 'asc' | 'desc';
type Tab = 'plants' | 'other';

const formatCurrency = (value: number) =>
  `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const isPlug = (title: string) => title.includes('2" Plug');

const getDefaultStartDate = () => {
  const lastYear = new Date().getFullYear() - 1;
  return `${lastYear}-11-01`;
};

export default function SalesReport() {
  const [startDate, setStartDate] = useState(getDefaultStartDate());
  const [products, setProducts] = useState<ProductSalesRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('gross_revenue');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [tab, setTab] = useState<Tab>('other');
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadData();
  }, [startDate]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await ordersApi.getProductSales(startDate);
      setProducts(data.products);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sales data');
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const plugs = useMemo(() => products.filter((p) => isPlug(p.product_title)), [products]);
  const other = useMemo(() => products.filter((p) => !isPlug(p.product_title)), [products]);

  const tabRows = tab === 'plants' ? plugs : other;

  const sorted = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = q ? tabRows.filter((r) => r.product_title.toLowerCase().includes(q)) : tabRows;
    return [...filtered].sort((a, b) => {
      const diff = a[sortKey] - b[sortKey];
      return sortDir === 'desc' ? -diff : diff;
    });
  }, [tabRows, sortKey, sortDir, search]);

  const tabQty = sorted.reduce((s, p) => s + p.total_quantity, 0);
  const tabRevenue = sorted.reduce((s, p) => s + p.gross_revenue, 0);
  const totalQty = products.reduce((s, p) => s + p.total_quantity, 0);
  const totalRevenue = products.reduce((s, p) => s + p.gross_revenue, 0);

  const SortIndicator = ({ col }: { col: SortKey }) =>
    sortKey === col ? (
      <span className="ml-1">{sortDir === 'desc' ? '↓' : '↑'}</span>
    ) : (
      <span className="ml-1 text-gray-300">↕</span>
    );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Sales Report</h2>
          <p className="text-gray-600 mt-1">Product-level sales by quantity and revenue</p>
        </div>
        <div className="flex items-center space-x-3">
          <input
            type="text"
            placeholder="Search products…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm w-52 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <label className="text-sm font-medium text-gray-700">Since:</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Summary chips — always show all-product totals */}
      {!loading && !error && (
        <div className="flex space-x-4 mb-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
            <div className="text-xs text-blue-500 uppercase font-medium">Total Products</div>
            <div className="text-xl font-bold text-blue-700">{products.length}</div>
          </div>
          <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3">
            <div className="text-xs text-green-500 uppercase font-medium">Total Units Sold</div>
            <div className="text-xl font-bold text-green-700">{totalQty.toLocaleString()}</div>
          </div>
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3">
            <div className="text-xs text-emerald-500 uppercase font-medium">Total Gross Revenue</div>
            <div className="text-xl font-bold text-emerald-700">{formatCurrency(totalRevenue)}</div>
          </div>
        </div>
      )}

      {/* States */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-3 text-gray-500 text-sm">Loading sales data…</p>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {!loading && !error && products.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <p className="text-yellow-800">No sales data found since {startDate}.</p>
        </div>
      )}

      {/* Tabs + Table */}
      {!loading && !error && products.length > 0 && (
        <>
          {/* Tab bar */}
          <div className="flex space-x-1 mb-4 border-b border-gray-200">
            <button
              onClick={() => setTab('other')}
              className={`px-5 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                tab === 'other'
                  ? 'bg-white border border-b-white border-gray-200 text-gray-900 -mb-px'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Trees & Shrubs
              <span className="ml-2 text-xs text-gray-400">({other.length})</span>
            </button>
            <button
              onClick={() => setTab('plants')}
              className={`px-5 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                tab === 'plants'
                  ? 'bg-white border border-b-white border-gray-200 text-gray-900 -mb-px'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              2" Plugs
              <span className="ml-2 text-xs text-gray-400">({plugs.length})</span>
            </button>
          </div>

          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Product
                  </th>
                  <th
                    className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-800 select-none"
                    onClick={() => handleSort('total_quantity')}
                  >
                    Qty Sold <SortIndicator col="total_quantity" />
                  </th>
                  <th
                    className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-800 select-none"
                    onClick={() => handleSort('gross_revenue')}
                  >
                    Gross Revenue <SortIndicator col="gross_revenue" />
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sorted.map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{row.product_title}</td>
                    <td className="px-6 py-4 text-sm text-right text-gray-700">{row.total_quantity.toLocaleString()}</td>
                    <td className="px-6 py-4 text-sm text-right font-medium text-green-700">
                      {formatCurrency(row.gross_revenue)}
                    </td>
                  </tr>
                ))}
                {/* Tab totals row */}
                <tr className="bg-gray-50 font-semibold">
                  <td className="px-6 py-4 text-sm text-gray-900">Subtotal</td>
                  <td className="px-6 py-4 text-sm text-right text-gray-700">{tabQty.toLocaleString()}</td>
                  <td className="px-6 py-4 text-sm text-right font-bold text-green-700">
                    {formatCurrency(tabRevenue)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
