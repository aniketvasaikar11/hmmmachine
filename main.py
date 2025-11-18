import React, { useState, useCallback } from 'react';
import { TrendingUp, BarChart3, Activity } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, ComposedChart } from 'recharts';

// Types
type Regime = 'Bull' | 'Bear';

interface ChartDataPoint {
  date: string;
  price: number;
  regime: Regime;
  allocation: number;
  strategyEquity: number;
  buyAndHoldEquity: number;
}

interface SinglePerformanceMetrics {
  cumulativeReturn: number;
  annualizedReturn: number;
  volatility: number;
  sharpeRatio: number;
  maxDrawdown: number;
}

interface PerformanceMetrics {
  strategy: SinglePerformanceMetrics & {
    turnover: number;
    tradeCount: number;
  };
  buyAndHold: SinglePerformanceMetrics;
}

interface BacktestResult {
  metrics: PerformanceMetrics;
  chartData: ChartDataPoint[];
  startPrice: number;
  endPrice: number;
}

// Yahoo Finance Service using CORS proxy
const fetchYahooFinanceData = async (ticker: string, startDate: Date, endDate: Date): Promise<{ dates: string[], prices: number[] }> => {
  const period1 = Math.floor(startDate.getTime() / 1000);
  const period2 = Math.floor(endDate.getTime() / 1000);
  
  // Use CORS proxy to access Yahoo Finance
  const yahooUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${ticker}?period1=${period1}&period2=${period2}&interval=1d`;
  const proxyUrl = `https://api.allorigins.win/raw?url=${encodeURIComponent(yahooUrl)}`;
  
  try {
    const response = await fetch(proxyUrl);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch data for ${ticker}. Please verify the ticker symbol is correct.`);
    }
    
    const data = await response.json();
    
    if (!data.chart?.result?.[0]) {
      throw new Error(`No data available for ticker ${ticker}. Please check if the ticker is valid.`);
    }
    
    const result = data.chart.result[0];
    const timestamps = result.timestamp;
    const quotes = result.indicators.quote[0];
    const closes = quotes.close;
    
    if (!timestamps || !closes || timestamps.length === 0) {
      throw new Error('Insufficient data returned from Yahoo Finance');
    }
    
    const dates: string[] = [];
    const prices: number[] = [];
    
    for (let i = 0; i < timestamps.length; i++) {
      const date = new Date(timestamps[i] * 1000).toISOString().split('T')[0];
      const close = closes[i];
      
      if (close !== null && !isNaN(close)) {
        dates.push(date);
        prices.push(close);
      }
    }
    
    if (dates.length === 0) {
      throw new Error('No valid price data found');
    }
    
    return { dates, prices };
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(`Error fetching Yahoo Finance data: Unknown error`);
  }
};

// HSMM Regime Detection (simplified implementation)
const detectRegimes = (returns: number[], qValue: number): Regime[] => {
  const regimes: Regime[] = [];
  const windowSize = Math.max(20, qValue * 5);
  
  for (let i = 0; i < returns.length; i++) {
    const start = Math.max(0, i - windowSize);
    const window = returns.slice(start, i + 1);
    
    if (window.length < 5) {
      regimes.push('Bull');
      continue;
    }
    
    const mean = window.reduce((a, b) => a + b, 0) / window.length;
    const variance = window.reduce((sum, r) => sum + Math.pow(r - mean, 2), 0) / window.length;
    const volatility = Math.sqrt(variance * 252);
    
    // Use momentum and volatility for regime detection
    const recentReturns = window.slice(-10);
    const momentum = recentReturns.reduce((a, b) => a + b, 0);
    
    // Bear market: negative momentum or high volatility
    if (momentum < -0.02 || volatility > 0.30) {
      regimes.push('Bear');
    } else {
      regimes.push('Bull');
    }
  }
  
  return regimes;
};

// Backtest Service
const runBacktest = async (ticker: string, qValue: number): Promise<BacktestResult> => {
  // Fetch 2 years of data
  const endDate = new Date();
  const startDate = new Date();
  startDate.setFullYear(startDate.getFullYear() - 2);
  
  const { dates, prices } = await fetchYahooFinanceData(ticker, startDate, endDate);
  
  if (prices.length < 50) {
    throw new Error('Insufficient historical data (need at least 50 days)');
  }
  
  // Calculate returns
  const returns: number[] = [];
  for (let i = 1; i < prices.length; i++) {
    returns.push((prices[i] - prices[i - 1]) / prices[i - 1]);
  }
  
  // Detect regimes
  const regimes = detectRegimes(returns, qValue);
  
  // Run backtest
  let strategyEquity = 100;
  let buyAndHoldEquity = 100;
  const strategyEquities: number[] = [strategyEquity];
  const buyAndHoldEquities: number[] = [buyAndHoldEquity];
  const allocations: number[] = [1.0];
  
  let prevAllocation = 1.0;
  let tradeCount = 0;
  let totalTurnover = 0;
  
  for (let i = 0; i < returns.length; i++) {
    const regime = regimes[i];
    const allocation = regime === 'Bull' ? 1.0 : 0.0;
    
    if (Math.abs(allocation - prevAllocation) > 0.01) {
      tradeCount++;
      totalTurnover += Math.abs(allocation - prevAllocation);
    }
    
    strategyEquity *= (1 + returns[i] * allocation);
    buyAndHoldEquity *= (1 + returns[i]);
    
    strategyEquities.push(strategyEquity);
    buyAndHoldEquities.push(buyAndHoldEquity);
    allocations.push(allocation);
    prevAllocation = allocation;
  }
  
  // Calculate metrics
  const calculateMetrics = (equities: number[]): SinglePerformanceMetrics => {
    const totalReturn = (equities[equities.length - 1] - 100) / 100;
    const years = equities.length / 252;
    const annualizedReturn = Math.pow(1 + totalReturn, 1 / years) - 1;
    
    const dailyReturns: number[] = [];
    for (let i = 1; i < equities.length; i++) {
      dailyReturns.push((equities[i] - equities[i - 1]) / equities[i - 1]);
    }
    
    const avgReturn = dailyReturns.reduce((a, b) => a + b, 0) / dailyReturns.length;
    const variance = dailyReturns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / dailyReturns.length;
    const volatility = Math.sqrt(variance * 252);
    
    const sharpeRatio = volatility > 0 ? (annualizedReturn - 0.02) / volatility : 0;
    
    let maxDrawdown = 0;
    let peak = equities[0];
    for (const equity of equities) {
      if (equity > peak) peak = equity;
      const drawdown = (peak - equity) / peak;
      if (drawdown > maxDrawdown) maxDrawdown = drawdown;
    }
    
    return {
      cumulativeReturn: totalReturn,
      annualizedReturn,
      volatility,
      sharpeRatio,
      maxDrawdown
    };
  };
  
  const strategyMetrics = calculateMetrics(strategyEquities);
  const buyAndHoldMetrics = calculateMetrics(buyAndHoldEquities);
  
  // Build chart data
  const chartData: ChartDataPoint[] = dates.map((date, i) => ({
    date,
    price: prices[i],
    regime: i === 0 ? 'Bull' : regimes[i - 1],
    allocation: allocations[i],
    strategyEquity: strategyEquities[i],
    buyAndHoldEquity: buyAndHoldEquities[i]
  }));
  
  return {
    metrics: {
      strategy: {
        ...strategyMetrics,
        turnover: totalTurnover / (returns.length / 252),
        tradeCount
      },
      buyAndHold: buyAndHoldMetrics
    },
    chartData,
    startPrice: prices[0],
    endPrice: prices[prices.length - 1]
  };
};

// Components
const Header: React.FC = () => (
  <header className="bg-gray-800 shadow-lg border-b border-gray-700">
    <div className="container mx-auto px-4 py-6">
      <h1 className="text-3xl font-bold text-cyan-500 flex items-center gap-2">
        <Activity className="w-8 h-8" />
        HSMM Regime-Based Asset Allocation
      </h1>
      <p className="text-gray-400 mt-2">Backtest with Real Yahoo Finance Data</p>
    </div>
  </header>
);

const ControlPanel: React.FC<{
  ticker: string;
  setTicker: (v: string) => void;
  qValue: number;
  setQValue: (v: number) => void;
  onRunBacktest: () => void;
  isLoading: boolean;
}> = ({ ticker, setTicker, qValue, setQValue, onRunBacktest, isLoading }) => (
  <div className="bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-700">
    <h2 className="text-xl font-semibold mb-4 text-gray-200">Backtest Configuration</h2>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div>
        <label className="block text-sm font-medium text-gray-400 mb-2">Ticker Symbol</label>
        <input
          type="text"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 focus:ring-2 focus:ring-cyan-500 focus:outline-none"
          placeholder="e.g., NVDA"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-400 mb-2">Q Value (Regime Duration)</label>
        <input
          type="number"
          value={qValue}
          onChange={(e) => setQValue(Number(e.target.value))}
          min="1"
          max="10"
          className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 focus:ring-2 focus:ring-cyan-500 focus:outline-none"
        />
      </div>
      <div className="flex items-end">
        <button
          onClick={onRunBacktest}
          disabled={isLoading}
          className="w-full px-6 py-2 bg-cyan-600 hover:bg-cyan-700 disabled:bg-gray-600 text-white font-semibold rounded-lg transition-colors"
        >
          {isLoading ? 'Running...' : 'Run Backtest'}
        </button>
      </div>
    </div>
  </div>
);

const Loader: React.FC = () => (
  <div className="flex flex-col items-center justify-center py-16">
    <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-cyan-500"></div>
    <p className="mt-4 text-gray-400">Fetching data from Yahoo Finance and running backtest...</p>
  </div>
);

const MetricCard: React.FC<{ title: string; value: string; subtitle?: string }> = ({ title, value, subtitle }) => (
  <div className="bg-gray-700 p-4 rounded-lg">
    <h4 className="text-sm font-medium text-gray-400">{title}</h4>
    <p className="text-2xl font-bold text-gray-200 mt-1">{value}</p>
    {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
  </div>
);

const ResultsDashboard: React.FC<{ result: BacktestResult }> = ({ result }) => {
  const { metrics, chartData } = result;
  
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-700">
          <h3 className="text-xl font-semibold mb-4 text-cyan-500 flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Strategy Performance
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <MetricCard title="Cumulative Return" value={`${(metrics.strategy.cumulativeReturn * 100).toFixed(2)}%`} />
            <MetricCard title="Annualized Return" value={`${(metrics.strategy.annualizedReturn * 100).toFixed(2)}%`} />
            <MetricCard title="Volatility" value={`${(metrics.strategy.volatility * 100).toFixed(2)}%`} />
            <MetricCard title="Sharpe Ratio" value={metrics.strategy.sharpeRatio.toFixed(3)} />
            <MetricCard title="Max Drawdown" value={`${(metrics.strategy.maxDrawdown * 100).toFixed(2)}%`} />
            <MetricCard title="Trade Count" value={metrics.strategy.tradeCount.toString()} />
          </div>
        </div>
        
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-700">
          <h3 className="text-xl font-semibold mb-4 text-gray-400 flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Buy & Hold Performance
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <MetricCard title="Cumulative Return" value={`${(metrics.buyAndHold.cumulativeReturn * 100).toFixed(2)}%`} />
            <MetricCard title="Annualized Return" value={`${(metrics.buyAndHold.annualizedReturn * 100).toFixed(2)}%`} />
            <MetricCard title="Volatility" value={`${(metrics.buyAndHold.volatility * 100).toFixed(2)}%`} />
            <MetricCard title="Sharpe Ratio" value={metrics.buyAndHold.sharpeRatio.toFixed(3)} />
            <MetricCard title="Max Drawdown" value={`${(metrics.buyAndHold.maxDrawdown * 100).toFixed(2)}%`} />
            <MetricCard title="Annual Turnover" value={`${(metrics.strategy.turnover * 100).toFixed(1)}%`} />
          </div>
        </div>
      </div>
      
      <div className="bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-700">
        <h3 className="text-xl font-semibold mb-4 text-gray-200">Equity Curves</h3>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="date" stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
            <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
            <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }} />
            <Legend />
            <Line type="monotone" dataKey="strategyEquity" stroke="#06b6d4" strokeWidth={2} dot={false} name="Strategy" />
            <Line type="monotone" dataKey="buyAndHoldEquity" stroke="#f59e0b" strokeWidth={2} dot={false} name="Buy & Hold" />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      <div className="bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-700">
        <h3 className="text-xl font-semibold mb-4 text-gray-200">Price & Regime Detection</h3>
        <ResponsiveContainer width="100%" height={400}>
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="date" stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
            <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
            <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }} />
            <Legend />
            <Area 
              type="monotone" 
              dataKey={(d) => d.regime === 'Bull' ? d.price : null} 
              fill="#10b981" 
              fillOpacity={0.3}
              stroke="none"
              name="Bull Market"
            />
            <Area 
              type="monotone" 
              dataKey={(d) => d.regime === 'Bear' ? d.price : null} 
              fill="#ef4444" 
              fillOpacity={0.3}
              stroke="none"
              name="Bear Market"
            />
            <Line type="monotone" dataKey="price" stroke="#06b6d4" strokeWidth={2} dot={false} name="Price" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// Main App
const App: React.FC = () => {
  const [ticker, setTicker] = useState<string>('NVDA');
  const [qValue, setQValue] = useState<number>(3);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);

  const handleRunBacktest = useCallback(async () => {
    if (!ticker) {
      setError('Please enter a ticker symbol.');
      return;
    }
    setIsLoading(true);
    setError(null);
    setBacktestResult(null);

    try {
      const result = await runBacktest(ticker.toUpperCase(), qValue);
      setBacktestResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred.');
    } finally {
      setIsLoading(false);
    }
  }, [ticker, qValue]);

  return (
    <div className="min-h-screen bg-gray-900 text-gray-200 font-sans">
      <Header />
      <main className="container mx-auto p-4 md:p-6 lg:p-8">
        <ControlPanel
          ticker={ticker}
          setTicker={setTicker}
          qValue={qValue}
          setQValue={setQValue}
          onRunBacktest={handleRunBacktest}
          isLoading={isLoading}
        />

        {error && (
          <div className="mt-6 bg-red-900/50 border border-red-700 text-red-300 px-4 py-3 rounded-lg text-center" role="alert">
            <strong className="font-bold">Error: </strong>
            <span className="block sm:inline">{error}</span>
          </div>
        )}

        {isLoading && <Loader />}

        {backtestResult && !isLoading && (
          <div className="mt-8">
            <ResultsDashboard result={backtestResult} />
          </div>
        )}
        
        {!isLoading && !backtestResult && !error && (
          <div className="mt-8 text-center text-gray-500 bg-gray-800 p-12 rounded-lg border-2 border-dashed border-gray-700">
            <h2 className="text-2xl font-semibold mb-2">Welcome to the HSMM Backtester</h2>
            <p>This app fetches real historical data from Yahoo Finance (past 2 years).</p>
            <p className="text-sm mt-2">Try any valid ticker symbol like <strong className="text-gray-400">NVDA</strong>, <strong className="text-gray-400">SPY</strong>, <strong className="text-gray-400">AAPL</strong>, etc.</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
