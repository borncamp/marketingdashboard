import { useState } from 'react';

interface ROASCalculatorProps {
  totalSpend: number;
}

export default function ROASCalculator({ totalSpend }: ROASCalculatorProps) {
  const [revenue, setRevenue] = useState<string>('');

  const revenueNum = parseFloat(revenue) || 0;
  const roas = totalSpend > 0 ? revenueNum / totalSpend : 0;

  const handleRevenueChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    // Allow only numbers and decimal point
    if (value === '' || /^\d*\.?\d*$/.test(value)) {
      setRevenue(value);
    }
  };

  const getROASColor = () => {
    if (roas >= 4) return 'text-green-600';
    if (roas >= 2) return 'text-blue-600';
    if (roas >= 1) return 'text-amber-600';
    return 'text-red-600';
  };

  return (
    <div className="flex items-center space-x-3">
      <div className="text-sm text-gray-600">
        Revenue:
      </div>
      <div className="relative">
        <span className="absolute left-2 top-1/2 transform -translate-y-1/2 text-gray-500 text-sm">
          $
        </span>
        <input
          type="text"
          value={revenue}
          onChange={handleRevenueChange}
          placeholder="0.00"
          className="w-32 pl-6 pr-2 py-1 border border-gray-300 rounded text-sm focus:border-blue-400 focus:outline-none"
        />
      </div>
      {revenue && roas > 0 && (
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-600">=</span>
          <span className={`text-lg font-bold ${getROASColor()}`}>
            {roas.toFixed(2)}x
          </span>
          <span className="text-xs text-gray-500">ROAS</span>
        </div>
      )}
    </div>
  );
}
