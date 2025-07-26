import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import time

# Configure the Streamlit page
st.set_page_config(
    page_title="Tech Stock Monitor VSCode",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stock symbols and company names (alphabetized)
STOCKS = {
    "AAPL": "Apple Inc.",
    "AMD": "Advanced Micro Devices Inc.",
    "AMZN": "Amazon.com Inc.",
    "AVGO": "Broadcom Inc.",
    "CDNS": "Cadence Design Systems Inc.",
    "GOOGL": "Alphabet Inc. (Class A)",
    "INTU": "Intuit Inc.",
    "LCID": "Lucid Group Inc.",
    "META": "Meta Platforms Inc.",
    "MSFT": "Microsoft Corporation",
    "NFLX": "Netflix Inc.",
    "NVDA": "NVIDIA Corporation",
    "QCOM": "Qualcomm Inc.",
    "RIVN": "Rivian Automotive Inc.",
    "SNOW": "Snowflake Inc.",
    "SNPS": "Synopsys Inc.",
    "TSLA": "Tesla Inc.",
    "TSM": "Taiwan Semiconductor Manufacturing Co. Ltd."
}

def fetch_stock_data(symbol):
    """
    Fetch real-time stock data for a given symbol using yfinance
    Returns a dictionary with key metrics or None if error occurs
    """
    try:
        ticker = yf.Ticker(symbol)

        # Get current info
        info = ticker.info

        # Get historical data for the last 2 days to calculate daily change
        hist_recent = ticker.history(period="2d", interval="1d")

        if hist_recent.empty or len(hist_recent) < 1:
            return None

        # Get the most recent data
        current_data = hist_recent.iloc[-1]
        current_price = current_data['Close']

        # Calculate daily change
        if len(hist_recent) >= 2:
            previous_close = hist_recent.iloc[-2]['Close']
            daily_change = current_price - previous_close
            percentage_change = (daily_change / previous_close) * 100
        else:
            # Fallback to info data if available
            previous_close = info.get('previousClose', current_price)
            daily_change = current_price - previous_close
            percentage_change = (daily_change / previous_close) * 100 if previous_close != 0 else 0

        # Get historical data for moving averages
        hist_long = ticker.history(period="250d")  # Get extra days to ensure we have enough data

        # Calculate 50-day moving average
        ma_50d = None
        if len(hist_long) >= 50:
            ma_50d = hist_long['Close'].tail(50).mean()

        # Calculate 200-day moving average
        ma_200d = None
        if len(hist_long) >= 200:
            ma_200d = hist_long['Close'].tail(200).mean()

        # Get P/E ratio (TTM)
        pe_ratio = info.get('trailingPE', 'N/A')

        # Compile stock data
        stock_data = {
            'symbol': symbol,
            'current_price': current_price,
            'pe_ratio': pe_ratio,  # P/E Ratio (TTM)
            'open_price': current_data['Open'],
            'high_price': current_data['High'],
            'low_price': current_data['Low'],
            'volume': current_data['Volume'],
            'daily_change': daily_change,
            'percentage_change': percentage_change,
            'market_cap': info.get('marketCap', 'N/A'),
            'previous_close': previous_close,
            'ma_50d': ma_50d,  # 50-day moving average
            'ma_200d': ma_200d,  # 200-day moving average
            'timestamp': datetime.now()
        }

        return stock_data

    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {str(e)}")
        return None

def format_currency(value):
    """Format currency values with appropriate suffixes"""
    if pd.isna(value) or value == 'N/A':
        return 'N/A'

    if isinstance(value, str):
        return value

    if value >= 1e12:
        return f"${value/1e12:.2f}T"
    elif value >= 1e9:
        return f"${value/1e9:.2f}B"
    elif value >= 1e6:
        return f"${value/1e6:.2f}M"
    else:
        return f"${value:,.2f}"

def format_volume(volume):
    """Format volume with appropriate suffixes"""
    if pd.isna(volume) or volume == 'N/A':
        return 'N/A'

    if volume >= 1e9:
        return f"{volume/1e9:.2f}B"
    elif volume >= 1e6:
        return f"{volume/1e6:.2f}M"
    elif volume >= 1e3:
        return f"{volume/1e3:.2f}K"
    else:
        return f"{volume:,.0f}"

def display_stock_card(stock_data, company_name):
    """Display individual stock data in a card format"""
    if stock_data is None:
        st.error(f"Failed to load data for {company_name}")
        return

    # Determine color based on daily change
    change_color = "green" if stock_data['daily_change'] >= 0 else "red"
    change_symbol = "+" if stock_data['daily_change'] >= 0 else ""

    # Create card layout
    with st.container():
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

        with col1:
            st.subheader(f"{stock_data['symbol']} - {company_name}")
            st.metric(
                label="Current Price",
                value=f"${stock_data['current_price']:.2f}",
                delta=f"{change_symbol}{stock_data['daily_change']:.2f} ({change_symbol}{stock_data['percentage_change']:.2f}%)"
            )

        with col2:
            st.metric("Volume", format_volume(stock_data['volume']))
            st.metric("Market Cap", format_currency(stock_data['market_cap']))

        with col3:
            st.metric("Open", f"${stock_data['open_price']:.2f}")
            st.metric("High", f"${stock_data['high_price']:.2f}")

        with col4:
            st.metric("Low", f"${stock_data['low_price']:.2f}")

            # Display 50-day moving average if available
            ma_50d_value = "N/A"
            if stock_data['ma_50d'] is not None:
                ma_50d_value = f"${stock_data['ma_50d']:.2f}"
            st.metric("50-Day MA", ma_50d_value)

            # Display 200-day moving average if available
            ma_200d_value = "N/A"
            if stock_data['ma_200d'] is not None:
                ma_200d_value = f"${stock_data['ma_200d']:.2f}"
            st.metric("200-Day MA", ma_200d_value)

    st.divider()

def create_summary_table(all_stock_data):
    """Create a summary table of all tech stocks"""
    summary_data = []

    for symbol, stock_data in all_stock_data.items():
        if stock_data is not None:
            # Format P/E ratio
            pe_ratio_value = "N/A"
            if stock_data['pe_ratio'] != 'N/A' and stock_data['pe_ratio'] is not None:
                pe_ratio_value = f"{stock_data['pe_ratio']:.2f}"

            # Format 50-day moving average
            ma_50d_value = "N/A"
            if stock_data['ma_50d'] is not None:
                ma_50d_value = f"${stock_data['ma_50d']:.2f}"

            # Format 200-day moving average
            ma_200d_value = "N/A"
            if stock_data['ma_200d'] is not None:
                ma_200d_value = f"${stock_data['ma_200d']:.2f}"

            # Format percentage change with color
            percentage_change = stock_data['percentage_change']
            is_positive = percentage_change >= 0
            change_symbol = "+" if is_positive else ""

            summary_data.append({
                'Symbol': symbol,
                'Company': STOCKS[symbol],
                'Current Price': f"${stock_data['current_price']:.2f}",
                'P/E (TTM)': pe_ratio_value,
                'Daily Change': f"{stock_data['daily_change']:+.2f}",
                'Change %': f"{change_symbol}{percentage_change:.2f}%",
                '200-Day MA': ma_200d_value,  # Swapped position with 50-Day MA
                '50-Day MA': ma_50d_value,    # Swapped position with 200-Day MA
                'Volume': format_volume(stock_data['volume']),
                'Market Cap': format_currency(stock_data['market_cap'])
            })

    if summary_data:
        # Create a DataFrame with raw values for proper sorting
        raw_data = []

        for symbol, stock_data in all_stock_data.items():
            if stock_data is not None:
                # Get raw numerical values for sorting
                pe_ratio_raw = stock_data['pe_ratio']
                if pe_ratio_raw == 'N/A' or pe_ratio_raw is None:
                    pe_ratio_raw = float('nan')

                ma_50d_raw = stock_data['ma_50d'] if stock_data['ma_50d'] is not None else float('nan')
                ma_200d_raw = stock_data['ma_200d'] if stock_data['ma_200d'] is not None else float('nan')

                # Format for display
                pe_ratio_display = "N/A"
                if stock_data['pe_ratio'] != 'N/A' and stock_data['pe_ratio'] is not None:
                    pe_ratio_display = f"{stock_data['pe_ratio']:.2f}"

                ma_50d_display = "N/A"
                if stock_data['ma_50d'] is not None:
                    ma_50d_display = f"${stock_data['ma_50d']:.2f}"

                ma_200d_display = "N/A"
                if stock_data['ma_200d'] is not None:
                    ma_200d_display = f"${stock_data['ma_200d']:.2f}"

                # Format percentage change
                percentage_change = stock_data['percentage_change']
                is_positive = percentage_change >= 0
                change_symbol = "+" if is_positive else ""
                percentage_display = f"{change_symbol}{percentage_change:.2f}%"

                # Add to raw data for DataFrame
                raw_data.append({
                    'Symbol': symbol,
                    'Company': STOCKS[symbol],
                    'Current Price': stock_data['current_price'],
                    'Current Price Display': f"${stock_data['current_price']:.2f}",
                    'P/E (TTM)': pe_ratio_raw,
                    'P/E (TTM) Display': pe_ratio_display,
                    'Daily Change': stock_data['daily_change'],
                    'Daily Change Display': f"{stock_data['daily_change']:+.2f}",
                    'Change %': percentage_change,
                    'Change % Display': percentage_display,
                    '200-Day MA': ma_200d_raw,
                    '200-Day MA Display': ma_200d_display,
                    '50-Day MA': ma_50d_raw,
                    '50-Day MA Display': ma_50d_display,
                    'Volume': stock_data['volume'],
                    'Volume Display': format_volume(stock_data['volume']),
                    'Market Cap': stock_data['market_cap'] if stock_data['market_cap'] != 'N/A' else float('nan'),
                    'Market Cap Display': format_currency(stock_data['market_cap'])
                })

        # Create DataFrame with both raw and display values
        df_raw = pd.DataFrame(raw_data)

        # Create a display DataFrame with only the columns we want to show
        display_df = pd.DataFrame({
            'Symbol': df_raw['Symbol'],
            'Company': df_raw['Company'],
            'Current Price': df_raw['Current Price Display'],
            'P/E (TTM)': df_raw['P/E (TTM) Display'],
            'Daily Change': df_raw['Daily Change Display'],
            'Change %': df_raw['Change % Display'],
            '200-Day MA': df_raw['200-Day MA Display'],
            '50-Day MA': df_raw['50-Day MA Display'],
            'Volume': df_raw['Volume Display'],
            'Market Cap': df_raw['Market Cap Display']
        })

        # Apply color styling to the Change % column
        def color_change_percent(val):
            if '+' in val:
                return 'color: green'
            elif '-' in val:
                return 'color: red'
            return ''

        # Apply the styling
        styled_df = display_df.style.applymap(color_change_percent, subset=['Change %'])

        # Make the table as big as the screen allows and enable sorting
        st.dataframe(
            data=df_raw,  # Use the raw data for sorting
            column_order=[
                'Symbol', 'Company', 'Current Price', 'P/E (TTM)',
                'Daily Change', 'Change %', '200-Day MA', '50-Day MA',
                'Volume', 'Market Cap'
            ],
            column_config={
                # Configure columns with appropriate types for sorting
                "Symbol": st.column_config.TextColumn("Symbol"),
                "Company": st.column_config.TextColumn("Company"),
                "Current Price": st.column_config.NumberColumn(
                    "Current Price",
                    format="$%.2f",
                    help="Current stock price"
                ),
                "P/E (TTM)": st.column_config.NumberColumn(
                    "P/E (TTM)",
                    format="%.2f",
                    help="Price to Earnings ratio (trailing 12 months)"
                ),
                "Daily Change": st.column_config.NumberColumn(
                    "Daily Change",
                    format="%+.2f",
                    help="Change in price from previous day"
                ),
                "Change %": st.column_config.NumberColumn(
                    "Change %",
                    format="%+.2f%%",
                    help="Percentage change from previous day"
                ),
                "200-Day MA": st.column_config.NumberColumn(
                    "200-Day MA",
                    format="$%.2f",
                    help="200-Day Moving Average"
                ),
                "50-Day MA": st.column_config.NumberColumn(
                    "50-Day MA",
                    format="$%.2f",
                    help="50-Day Moving Average"
                ),
                "Volume": st.column_config.NumberColumn(
                    "Volume",
                    format="%d",
                    help="Trading volume"
                ),
                "Market Cap": st.column_config.NumberColumn(
                    "Market Cap",
                    format="$%d",
                    help="Market Capitalization"
                )
            },
            use_container_width=True,
            hide_index=True,
            height=800
        )
    else:
        st.error("No stock data available to display in summary table")

def main():
    """Main application function"""
    st.title("📈 Tech Stock Monitor")
    st.markdown("Real-time stock prices and trading metrics for leading tech companies")

    # Sidebar controls
    st.sidebar.title("Controls")

    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30 seconds)", value=False)

    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.rerun()

    # Display last update time
    last_update = st.sidebar.empty()

    # Main content area
    with st.spinner("Fetching stock data..."):
        # Fetch data for all stocks
        all_stock_data = {}

        for symbol in STOCKS.keys():
            stock_data = fetch_stock_data(symbol)
            all_stock_data[symbol] = stock_data

    # Update timestamp
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    last_update.text(f"Last updated: {current_time}")

    # Create tabs for different views
    tab1, tab2 = st.tabs(["📊 Summary Table", "📋 Detailed Cards"])

    with tab1:
        st.subheader("Tech Stocks Summary")
        create_summary_table(all_stock_data)

    with tab2:
        st.subheader("Detailed Stock Information")
        for symbol, company_name in STOCKS.items():
            display_stock_card(all_stock_data[symbol], company_name)

    # Auto-refresh functionality
    if auto_refresh:
        time.sleep(30)
        st.rerun()

    # Footer information
    st.markdown("---")
    st.markdown("**Note:** Stock prices are fetched from Yahoo Finance and may have a slight delay. This application is for informational purposes only and should not be used as the sole basis for investment decisions.")

if __name__ == "__main__":
    main()
