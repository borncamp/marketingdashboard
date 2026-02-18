import { useState, useEffect, useMemo } from 'react';
import { campaignApi, ordersApi } from '../services/api';

interface MonthlyData {
  month: string;
  revenue: number;
  shipping_revenue: number;
  shipping_cost: number;
  order_count: number;
  ad_spend: number;
  cogs: number;
}

interface ProjectionRow {
  month: string;
  multiplier: number;
  projected_revenue: number;
  projected_ad_spend: number;
  projected_cogs: number;
  projected_shipping_cost: number;
  projected_expenses: number;
  projected_profit: number;
  isCurrentMonth: boolean;
}

const formatCurrency = (value: number) =>
  `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const formatMonth = (month: string) => {
  const [year, m] = month.split('-');
  const date = new Date(parseInt(year), parseInt(m) - 1);
  return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
};

// Hard cutoff: Nov 15 of the prior year
const getCutoffDate = () => {
  const now = new Date();
  return `${now.getFullYear() - 1}-11-15`;
};

// Current month as YYYY-MM
const getCurrentMonth = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
};

// Days elapsed in the current month (including today)
const getDaysElapsedInMonth = () => {
  return new Date().getDate();
};

// Total days in the current month
const getDaysInCurrentMonth = () => {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
};

export default function ProfitTracker() {
  const [period, setPeriod] = useState<number>(365);
  const [allData, setAllData] = useState<MonthlyData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Projection state
  const [baseMonthIndex, setBaseMonthIndex] = useState<number>(-1);
  const [projectionMonths, setProjectionMonths] = useState<ProjectionRow[]>([]);

  const cutoffDate = getCutoffDate();
  const currentMonth = getCurrentMonth();

  // Load all data once from cutoff — period only filters what's displayed
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [shopifyData, spendData] = await Promise.all([
        ordersApi.getMonthlySummary(24, cutoffDate),
        campaignApi.getMonthlySpend(24, cutoffDate),
      ]);

      // Build a spend lookup
      const spendByMonth: Record<string, number> = {};
      for (const item of spendData.months) {
        spendByMonth[item.month] = item.spend;
      }

      // Merge into unified monthly data
      const merged: MonthlyData[] = shopifyData.months.map((m: any) => ({
        month: m.month,
        revenue: m.revenue || 0,
        shipping_revenue: m.shipping_revenue || 0,
        shipping_cost: m.shipping_cost || 0,
        order_count: m.order_count || 0,
        ad_spend: spendByMonth[m.month] || 0,
        cogs: m.cogs || 0,
      }));

      // Also add months that only have spend data
      for (const item of spendData.months) {
        if (!merged.find((m) => m.month === item.month)) {
          merged.push({
            month: item.month,
            revenue: 0,
            shipping_revenue: 0,
            shipping_cost: 0,
            order_count: 0,
            ad_spend: item.spend,
            cogs: 0,
          });
        }
      }

      merged.sort((a, b) => a.month.localeCompare(b.month));
      setAllData(merged);

      // Default base month to the most recent COMPLETE month
      const completeMonths = merged.filter((m) => m.month !== currentMonth);
      if (completeMonths.length > 0) {
        const lastCompleteIdx = merged.findIndex(
          (m) => m.month === completeMonths[completeMonths.length - 1].month
        );
        setBaseMonthIndex(lastCompleteIdx);
      } else if (merged.length > 0) {
        setBaseMonthIndex(0);
      }

      initProjections(merged);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const initProjections = (data: MonthlyData[]) => {
    if (data.length === 0) {
      setProjectionMonths([]);
      return;
    }

    // Find the last complete month
    const completeMonths = data.filter((m) => m.month !== currentMonth);
    const lastComplete = completeMonths[completeMonths.length - 1];
    const currentMonthData = data.find((m) => m.month === currentMonth);

    // Start projections from the current month (if partial) or next month
    const startFromMonth = currentMonth;
    const [startYear, startM] = startFromMonth.split('-').map(Number);

    const rows: ProjectionRow[] = [];

    // Current month: extrapolate from days elapsed
    if (currentMonthData) {
      const daysElapsed = getDaysElapsedInMonth();
      const daysInMonth = getDaysInCurrentMonth();
      const extrapolationMultiplier = daysInMonth / daysElapsed;
      const currentActualRevenue = currentMonthData.revenue + currentMonthData.shipping_revenue;
      const extrapolatedRevenue = currentActualRevenue * extrapolationMultiplier;

      // Express as multiplier of base month
      let multiplier = 1.0;
      if (lastComplete) {
        const baseRev = lastComplete.revenue + lastComplete.shipping_revenue;
        if (baseRev > 0) {
          multiplier = parseFloat((extrapolatedRevenue / baseRev).toFixed(2));
        }
      }

      rows.push({
        month: currentMonth,
        multiplier,
        projected_revenue: 0,
        projected_ad_spend: 0,
        projected_cogs: 0,
        projected_shipping_cost: 0,
        projected_expenses: 0,
        projected_profit: 0,
        isCurrentMonth: true,
      });
    }

    // 5 more future months after the current month with preset multipliers
    const presetMultipliers = [2, 3, 6, 1, 0];
    for (let i = 1; i <= 5; i++) {
      const date = new Date(startYear, startM - 1 + i);
      const futureMonth = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      const multiplier = presetMultipliers[i - 1];

      rows.push({ month: futureMonth, multiplier, projected_revenue: 0, projected_ad_spend: 0, projected_cogs: 0, projected_shipping_cost: 0, projected_expenses: 0, projected_profit: 0, isCurrentMonth: false });
    }

    setProjectionMonths(rows);
  };

  // Filter data by period for display (summary cards + table)
  const filteredData = useMemo(() => {
    const now = new Date();
    const cutoff = new Date(now);
    cutoff.setDate(cutoff.getDate() - period);
    const cutoffMonth = `${cutoff.getFullYear()}-${String(cutoff.getMonth() + 1).padStart(2, '0')}`;
    return allData.filter((m) => m.month >= cutoffMonth);
  }, [allData, period]);

  // Compute totals for the summary cards from filtered data
  const totals = useMemo(() => {
    const productRevenue = filteredData.reduce((s, m) => s + m.revenue, 0);
    const shippingCollected = filteredData.reduce((s, m) => s + m.shipping_revenue, 0);
    const totalRevenue = productRevenue + shippingCollected;
    const totalAdSpend = filteredData.reduce((s, m) => s + m.ad_spend, 0);
    const totalShippingCost = filteredData.reduce((s, m) => s + m.shipping_cost, 0);
    const totalCogs = filteredData.reduce((s, m) => s + m.cogs, 0);
    const totalExpenses = totalAdSpend + totalShippingCost + totalCogs;
    const netProfit = totalRevenue - totalExpenses;
    const profitMargin = totalRevenue > 0 ? (netProfit / totalRevenue) * 100 : 0;
    return { productRevenue, shippingCollected, totalRevenue, totalAdSpend, totalShippingCost, totalCogs, totalExpenses, netProfit, profitMargin };
  }, [filteredData]);

  // Compute projected values from ALL data (base month uses allData index)
  const projectedRows = useMemo(() => {
    if (baseMonthIndex < 0 || baseMonthIndex >= allData.length) return projectionMonths;
    const base = allData[baseMonthIndex];
    const baseRevenue = base.revenue + base.shipping_revenue;
    const baseAdSpend = base.ad_spend;
    const baseCogs = base.cogs;
    const baseShippingCost = base.shipping_cost;
    return projectionMonths.map((row) => {
      const projected_revenue = baseRevenue * row.multiplier;
      const projected_ad_spend = baseAdSpend * row.multiplier;
      const projected_cogs = baseCogs * row.multiplier;
      const projected_shipping_cost = baseShippingCost * row.multiplier;
      const projected_expenses = projected_ad_spend + projected_cogs + projected_shipping_cost;
      const projected_profit = projected_revenue - projected_expenses;
      return { ...row, projected_revenue, projected_ad_spend, projected_cogs, projected_shipping_cost, projected_expenses, projected_profit };
    });
  }, [projectionMonths, baseMonthIndex, allData]);

  const totalProjectedRevenue = projectedRows.reduce((s, r) => s + r.projected_revenue, 0);
  const totalProjectedExpenses = projectedRows.reduce((s, r) => s + r.projected_expenses, 0);
  const totalProjectedProfit = projectedRows.reduce((s, r) => s + r.projected_profit, 0);

  const updateMultiplier = (index: number, value: number) => {
    setProjectionMonths((prev) =>
      prev.map((row, i) => (i === index ? { ...row, multiplier: value } : row))
    );
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading profit data...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-800 mb-2">Error Loading Data</h3>
          <p className="text-red-700">{error}</p>
        </div>
      </div>
    );
  }

  // Current month info for the table annotation
  const daysElapsed = getDaysElapsedInMonth();
  const daysInMonth = getDaysInCurrentMonth();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header + Period Toggle */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Profit Tracker</h2>
          <p className="text-gray-600 mt-1">
            Revenue, expenses, and profit projections (since Nov 15, {new Date().getFullYear() - 1})
          </p>
        </div>
        <div className="flex space-x-2">
          {[30, 90, 180, 365].map((days) => (
            <button
              key={days}
              onClick={() => setPeriod(days)}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                period === days
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {days === 365 ? '1y' : `${days}d`}
            </button>
          ))}
        </div>
      </div>

      {/* Section 1: Summary Cards */}
      <div className="space-y-3 mb-8">
        {/* Row 1: Revenue breakdown */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <SummaryCard icon="💵" label="Product Revenue" value={formatCurrency(totals.productRevenue)} color="green" />
          <SummaryCard icon="🚢" label="Shipping Collected" value={formatCurrency(totals.shippingCollected)} color="teal" />
          <SummaryCard icon="💰" label="Total Revenue" value={formatCurrency(totals.totalRevenue)} color="emerald" />
          <SummaryCard
            icon="📊"
            label="Profit Margin"
            value={`${totals.profitMargin.toFixed(1)}%`}
            color={totals.profitMargin >= 20 ? 'emerald' : totals.profitMargin >= 0 ? 'amber' : 'red'}
          />
        </div>
        {/* Row 2: Expenses & profit */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <SummaryCard icon="📣" label="Ad Spend" value={formatCurrency(totals.totalAdSpend)} color="yellow" />
          <SummaryCard icon="🏭" label="COGS" value={formatCurrency(totals.totalCogs)} color="amber" />
          <SummaryCard icon="📦" label="Shipping Cost" value={formatCurrency(totals.totalShippingCost)} color="orange" />
          <SummaryCard icon="💸" label="Total Expenses" value={formatCurrency(totals.totalExpenses)} color="red" />
          <SummaryCard
            icon="💎"
            label="Net Profit"
            value={formatCurrency(totals.netProfit)}
            color={totals.netProfit >= 0 ? 'emerald' : 'red'}
          />
        </div>
      </div>

      {/* Section 2: Monthly Breakdown Table */}
      <div className="mb-12">
        <h3 className="text-xl font-bold text-gray-900 mb-4">Monthly Breakdown</h3>
        {filteredData.length === 0 ? (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
            <p className="text-yellow-800">No data available for this period.</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Month</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Revenue</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Shipping Collected</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ad Spend</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">COGS</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Shipping Cost</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Orders</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Profit</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredData.map((row) => {
                  const isPartial = row.month === currentMonth;
                  const totalRev = row.revenue + row.shipping_revenue;
                  const totalExp = row.ad_spend + row.shipping_cost + row.cogs;
                  const profit = totalRev - totalExp;
                  return (
                    <tr key={row.month} className={`hover:bg-gray-50 ${isPartial ? 'bg-amber-50/50' : ''}`}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {formatMonth(row.month)}
                        {isPartial && (
                          <span className="ml-2 text-xs text-amber-600 font-normal">
                            (partial — {daysElapsed}/{daysInMonth} days)
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">{formatCurrency(row.revenue)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-600">{formatCurrency(row.shipping_revenue)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-yellow-700">{formatCurrency(row.ad_spend)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-amber-600">{formatCurrency(row.cogs)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-orange-600">{formatCurrency(row.shipping_cost)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-600">{row.order_count}</td>
                      <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-semibold ${profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatCurrency(profit)}
                      </td>
                    </tr>
                  );
                })}
                {/* Totals row */}
                <tr className="bg-gray-50 font-semibold">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">Total</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                    {formatCurrency(totals.productRevenue)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-600">
                    {formatCurrency(totals.shippingCollected)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-yellow-700">
                    {formatCurrency(totals.totalAdSpend)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-amber-600">
                    {formatCurrency(totals.totalCogs)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-orange-600">
                    {formatCurrency(totals.totalShippingCost)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-600">
                    {filteredData.reduce((s, m) => s + m.order_count, 0)}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-bold ${totals.netProfit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatCurrency(totals.netProfit)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Section 3: Revenue Projection Tool */}
      <div>
        <h3 className="text-xl font-bold text-gray-900 mb-4">Revenue Projection</h3>
        <p className="text-gray-600 mb-4">
          Set a base month and adjust multipliers to project future revenue. The current month is auto-extrapolated from {daysElapsed} days of actual data.
        </p>

        {allData.length === 0 ? (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
            <p className="text-yellow-800">Need historical data to project revenue.</p>
          </div>
        ) : (
          <>
            {/* Base month selector — only complete months */}
            <div className="flex items-center space-x-4 mb-6">
              <label className="text-sm font-medium text-gray-700">Base Month:</label>
              <select
                value={baseMonthIndex}
                onChange={(e) => setBaseMonthIndex(parseInt(e.target.value))}
                className="px-3 py-2 border rounded-lg"
              >
                {allData
                  .filter((m) => m.month !== currentMonth)
                  .map((m) => {
                    const idx = allData.findIndex((d) => d.month === m.month);
                    return (
                      <option key={m.month} value={idx}>
                        {formatMonth(m.month)} — {formatCurrency(m.revenue + m.shipping_revenue)} revenue
                      </option>
                    );
                  })}
              </select>
              {baseMonthIndex >= 0 && baseMonthIndex < allData.length && (
                <span className="text-sm text-gray-500">
                  Base revenue: {formatCurrency(allData[baseMonthIndex].revenue + allData[baseMonthIndex].shipping_revenue)}
                </span>
              )}
            </div>

            {/* Projection table */}
            <div className="bg-white rounded-lg shadow-md overflow-hidden mb-4">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Month</th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Multiplier</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Revenue</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ad Spend</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">COGS</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Shipping</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Expenses</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Profit</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {projectedRows.map((row, index) => (
                    <tr key={row.month} className={`hover:bg-gray-50 ${row.isCurrentMonth ? 'bg-amber-50/50' : ''}`}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {formatMonth(row.month)}
                        {row.isCurrentMonth && (
                          <span className="ml-2 text-xs text-amber-600 font-normal">
                            (extrapolated from {daysElapsed} days)
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <div className="flex items-center justify-center space-x-2">
                          <input
                            type="number"
                            step="0.1"
                            min="0"
                            value={row.multiplier}
                            onChange={(e) => updateMultiplier(index, parseFloat(e.target.value) || 0)}
                            className="w-24 px-3 py-1 border rounded-lg text-center text-sm"
                          />
                          <span className="text-xs text-gray-500">x</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-blue-700">
                        {formatCurrency(row.projected_revenue)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-yellow-700">
                        {formatCurrency(row.projected_ad_spend)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-amber-600">
                        {formatCurrency(row.projected_cogs)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-orange-600">
                        {formatCurrency(row.projected_shipping_cost)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-red-600">
                        {formatCurrency(row.projected_expenses)}
                      </td>
                      <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-semibold ${row.projected_profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatCurrency(row.projected_profit)}
                      </td>
                    </tr>
                  ))}
                  {/* Total projected row */}
                  <tr className="bg-blue-50 font-semibold">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">Total Projected</td>
                    <td className="px-6 py-4"></td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-bold text-blue-800">
                      {formatCurrency(totalProjectedRevenue)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-yellow-700">
                      {formatCurrency(projectedRows.reduce((s, r) => s + r.projected_ad_spend, 0))}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-amber-600">
                      {formatCurrency(projectedRows.reduce((s, r) => s + r.projected_cogs, 0))}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-orange-600">
                      {formatCurrency(projectedRows.reduce((s, r) => s + r.projected_shipping_cost, 0))}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-bold text-red-700">
                      {formatCurrency(totalProjectedExpenses)}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-bold ${totalProjectedProfit >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                      {formatCurrency(totalProjectedProfit)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function SummaryCard({ icon, label, value, color }: { icon: string; label: string; value: string; color: string }) {
  const colorMap: Record<string, { bg: string; text: string; border: string }> = {
    green: { bg: 'bg-green-50', text: 'text-green-600', border: 'border-green-200' },
    yellow: { bg: 'bg-yellow-50', text: 'text-yellow-600', border: 'border-yellow-200' },
    orange: { bg: 'bg-orange-50', text: 'text-orange-600', border: 'border-orange-200' },
    red: { bg: 'bg-red-50', text: 'text-red-600', border: 'border-red-200' },
    emerald: { bg: 'bg-emerald-50', text: 'text-emerald-600', border: 'border-emerald-200' },
    teal: { bg: 'bg-teal-50', text: 'text-teal-600', border: 'border-teal-200' },
    amber: { bg: 'bg-amber-50', text: 'text-amber-600', border: 'border-amber-200' },
    blue: { bg: 'bg-blue-50', text: 'text-blue-600', border: 'border-blue-200' },
  };
  const c = colorMap[color] || colorMap.blue;

  return (
    <div className={`${c.bg} border ${c.border} rounded-lg p-6 shadow-sm`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-2xl">{icon}</span>
      </div>
      <div className={`text-2xl font-bold ${c.text} mb-1`}>{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}
