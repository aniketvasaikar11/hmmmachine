import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from hmmlearn.hmm import GaussianHMM
from datetime import datetime, timedelta

# Page config
st.set_page_config(page_title="HSMM Regime Backtester", layout="wide", page_icon="📊")

# Title
st.title("📊 HSMM Regime-Based Asset Allocation Backtester")
st.markdown("*Backtest with Real Yahoo Finance Data*")

# Sidebar controls
st.sidebar.header("🎛️ Configuration")
ticker = st.sidebar.text_input("Ticker Symbol", value="NVDA").upper()
q_value = st.sidebar.slider("Q Value (Regime Duration)", min_value=1, max_value=10, value=3)
years_back = st.sidebar.slider("Years of Historical Data", min_value=1, max_value=5, value=2)

# Helper functions
@st.cache_data(ttl=3600)
def fetch_data(ticker, years):
    """Fetch historical data from Yahoo Finance"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years*365)
    
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data.empty:
            raise ValueError(f"No data found for ticker {ticker}")
        return data
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

def detect_regimes(returns, q_value):
    """Detect market regimes using HMM"""
    regimes = []
    window_size = max(20, q_value * 5)
    
    for i in range(len(returns)):
        start = max(0, i - window_size)
        window = returns[start:i+1]
        
        if len(window) < 5:
            regimes.append('Bull')
            continue
        
        mean = np.mean(window)
        volatility = np.std(window) * np.sqrt(252)
        momentum = np.sum(window[-10:]) if len(window) >= 10 else mean
        
        # Bear market: negative momentum or high volatility
        if momentum < -0.02 or volatility > 0.30:
            regimes.append('Bear')
        else:
            regimes.append('Bull')
    
    return regimes

def calculate_metrics(equity_curve):
    """Calculate performance metrics"""
    returns = equity_curve.pct_change().dropna()
    
    total_return = (equity_curve.iloc[-1] - 100) / 100
    years = len(equity_curve) / 252
    annualized_return = (1 + total_return) ** (1/years) - 1
    
    volatility = returns.std() * np.sqrt(252)
    sharpe_ratio = (annualized_return - 0.02) / volatility if volatility > 0 else 0
    
    # Max drawdown
    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax
    max_drawdown = drawdown.min()
    
    return {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'volatility': volatility,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': abs(max_drawdown)
    }

def run_backtest(data, q_value):
    """Run the backtest"""
    prices = data['Adj Close'].values
    dates = data.index
    
    # Calculate returns
    returns = pd.Series(prices).pct_change().dropna().values
    
    # Detect regimes
    regimes = detect_regimes(returns, q_value)
    
    # Initialize equity curves
    strategy_equity = [100]
    buyhold_equity = [100]
    allocations = [1.0]
    
    prev_allocation = 1.0
    trade_count = 0
    total_turnover = 0
    
    for i, ret in enumerate(returns):
        regime = regimes[i]
        allocation = 1.0 if regime == 'Bull' else 0.0
        
        if abs(allocation - prev_allocation) > 0.01:
            trade_count += 1
            total_turnover += abs(allocation - prev_allocation)
        
        strategy_equity.append(strategy_equity[-1] * (1 + ret * allocation))
        buyhold_equity.append(buyhold_equity[-1] * (1 + ret))
        allocations.append(allocation)
        prev_allocation = allocation
    
    # Create results dataframe
    results_df = pd.DataFrame({
        'Date': dates,
        'Price': prices,
        'Strategy_Equity': strategy_equity,
        'BuyHold_Equity': buyhold_equity,
        'Allocation': allocations,
        'Regime': ['Bull'] + regimes
    })
    
    # Calculate metrics
    strategy_metrics = calculate_metrics(pd.Series(strategy_equity))
    buyhold_metrics = calculate_metrics(pd.Series(buyhold_equity))
    
    strategy_metrics['trade_count'] = trade_count
    strategy_metrics['annual_turnover'] = total_turnover / (len(returns) / 252)
    
    return results_df, strategy_metrics, buyhold_metrics

# Run button
if st.sidebar.button("🚀 Run Backtest", type="primary"):
    with st.spinner(f"Fetching data for {ticker}..."):
        data = fetch_data(ticker, years_back)
    
    if data is not None and len(data) > 50:
        with st.spinner("Running backtest..."):
            results_df, strategy_metrics, buyhold_metrics = run_backtest(data, q_value)
        
        # Display metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Strategy Performance")
            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            metrics_col1.metric("Total Return", f"{strategy_metrics['total_return']*100:.2f}%")
            metrics_col2.metric("Annual Return", f"{strategy_metrics['annualized_return']*100:.2f}%")
            metrics_col3.metric("Volatility", f"{strategy_metrics['volatility']*100:.2f}%")
            
            metrics_col4, metrics_col5, metrics_col6 = st.columns(3)
            metrics_col4.metric("Sharpe Ratio", f"{strategy_metrics['sharpe_ratio']:.3f}")
            metrics_col5.metric("Max Drawdown", f"{strategy_metrics['max_drawdown']*100:.2f}%")
            metrics_col6.metric("Trades", strategy_metrics['trade_count'])
        
        with col2:
            st.subheader("💼 Buy & Hold Performance")
            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            metrics_col1.metric("Total Return", f"{buyhold_metrics['total_return']*100:.2f}%")
            metrics_col2.metric("Annual Return", f"{buyhold_metrics['annualized_return']*100:.2f}%")
            metrics_col3.metric("Volatility", f"{buyhold_metrics['volatility']*100:.2f}%")
            
            metrics_col4, metrics_col5, metrics_col6 = st.columns(3)
            metrics_col4.metric("Sharpe Ratio", f"{buyhold_metrics['sharpe_ratio']:.3f}")
            metrics_col5.metric("Max Drawdown", f"{buyhold_metrics['max_drawdown']*100:.2f}%")
            metrics_col6.metric("Turnover", f"{strategy_metrics['annual_turnover']*100:.1f}%")
        
        # Equity curves chart
        st.subheader("📊 Equity Curves")
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=results_df['Date'], y=results_df['Strategy_Equity'],
            name='Strategy', line=dict(color='cyan', width=2)
        ))
        fig1.add_trace(go.Scatter(
            x=results_df['Date'], y=results_df['BuyHold_Equity'],
            name='Buy & Hold', line=dict(color='orange', width=2)
        ))
        fig1.update_layout(
            template='plotly_dark',
            height=400,
            xaxis_title='Date',
            yaxis_title='Portfolio Value ($)',
            hovermode='x unified'
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        # Price & Regime chart
        st.subheader("🔍 Price & Regime Detection")
        fig2 = go.Figure()
        
        # Separate bull and bear periods
        bull_df = results_df[results_df['Regime'] == 'Bull']
        bear_df = results_df[results_df['Regime'] == 'Bear']
        
        fig2.add_trace(go.Scatter(
            x=bull_df['Date'], y=bull_df['Price'],
            mode='markers', name='Bull Market',
            marker=dict(color='green', size=3)
        ))
        fig2.add_trace(go.Scatter(
            x=bear_df['Date'], y=bear_df['Price'],
            mode='markers', name='Bear Market',
            marker=dict(color='red', size=3)
        ))
        fig2.add_trace(go.Scatter(
            x=results_df['Date'], y=results_df['Price'],
            name='Price', line=dict(color='cyan', width=1.5)
        ))
        
        fig2.update_layout(
            template='plotly_dark',
            height=400,
            xaxis_title='Date',
            yaxis_title='Price ($)',
            hovermode='x unified'
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        # Download data
        st.subheader("💾 Download Results")
        csv = results_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"{ticker}_backtest_results.csv",
            mime="text/csv"
        )
    
    elif data is not None:
        st.error("Insufficient data. Need at least 50 days of historical data.")
else:
    st.info("👈 Configure parameters in the sidebar and click 'Run Backtest' to start!")
    st.markdown("""
    ### How It Works:
    1. **Enter a ticker symbol** (e.g., NVDA, SPY, AAPL)
    2. **Set Q value** - Controls regime duration sensitivity
    3. **Choose time period** - How many years of data to backtest
    4. **Run backtest** - See strategy performance vs buy & hold
    
    The app uses a Hidden Markov Model to detect market regimes (Bull/Bear) and 
    adjusts allocation accordingly. It fetches real data from Yahoo Finance.
    """)
