import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import random  # For generating mock data
import time

# Configure the Streamlit page
st.set_page_config(
    page_title="Tech Stock Monitor VSCode",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Stock symbols and company names (alphabetized)
STOCKS = {
    "AAPL": "Apple Inc.",
    "AMD": "Advanced Micro Devices Inc.",
    "AMZN": "Amazon.com Inc.",
    "ASML": "ASML Holding N.V.",
    "AVGO": "Broadcom Inc.",
    "BLK": "BlackRock Inc.",
    "BTC-USD": "Bitcoin USD",  # Using BTC-USD instead of BTC=F for better compatibility
    "CDNS": "Cadence Design Systems Inc.",
    "CRM": "Salesforce Inc.",
    "CRSP": "CRISPR Therapeutics AG",
    "CRWD": "CrowdStrike Holdings Inc.",
    "GLD": "SPDR Gold Shares",
    "GOOGL": "Alphabet Inc. (Class A)",
    "INTU": "Intuit Inc.",
    "LCID": "Lucid Group Inc.",
    "META": "Meta Platforms Inc.",
    "MSFT": "Microsoft Corporation",
    "NFLX": "Netflix Inc.",
    "NTLA": "Intellia Therapeutics Inc.",
    "NVDA": "NVIDIA Corporation",
    "QCOM": "Qualcomm Inc.",
    "QQQ": "Invesco QQQ Trust",
    "RIVN": "Rivian Automotive Inc.",
    "SHOP": "Shopify Inc.",
    "SLV": "iShares Silver Trust",  # Using SLV instead of SLVR
    "SNOW": "Snowflake Inc.",
    "SNPS": "Synopsys Inc.",
    "SPY": "SPDR S&P 500 ETF Trust",
    "TSLA": "Tesla Inc.",
    "TSM": "Taiwan Semiconductor Manufacturing Co. Ltd.",
    "^VIX": "CBOE Volatility Index",  # Using ^VIX for the volatility index
}


def fetch_stock_data(symbol):
    """
    Fetch real-time stock data for a given symbol using yfinance
    Returns a dictionary with key metrics or None if error occurs
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Get current info
        # Get historical data for the last 2 days to calculate daily change
        hist_recent = ticker.history(period="2d", interval="1d")

        if hist_recent.empty or len(hist_recent) < 1:
            return None

        # Get the most recent data
        current_data = hist_recent.iloc[-1]
        current_price = current_data["Close"]

        # Calculate daily change
        if len(hist_recent) >= 2:
            previous_close = hist_recent.iloc[-2]["Close"]
            daily_change = current_price - previous_close
            percentage_change = (daily_change / previous_close) * 100
        else:
            # Fallback to info data if available
            previous_close = info.get("previousClose", current_price)
            daily_change = current_price - previous_close
            percentage_change = (
                (daily_change / previous_close) * 100 if previous_close != 0 else 0
            )

        # Get historical data for moving averages (get extra days to check for recent golden cross)
        hist_long = ticker.history(
            period="250d"
        )  # Get extra days to ensure we have enough data

        # Calculate 50-day moving average
        ma_50d = None
        if len(hist_long) >= 50:
            ma_50d = hist_long["Close"].tail(50).mean()

        # Calculate 200-day moving average
        ma_200d = None
        if len(hist_long) >= 200:
            ma_200d = hist_long["Close"].tail(200).mean()

        # Check if Golden Cross occurred in the past 30 days
        golden_cross = False
        if len(hist_long) >= 200:
            # Calculate 50-day and 200-day MAs for the past 60 days
            # (we need 30 days + some buffer to detect the crossover)
            ma_50d_series = hist_long["Close"].rolling(window=50).mean().tail(60)
            ma_200d_series = hist_long["Close"].rolling(window=200).mean().tail(60)

            # Check if there was a crossover in the past 30 days
            # (50-day MA crossing above 200-day MA)
            for i in range(1, min(31, len(ma_50d_series))):
                if (ma_50d_series.iloc[-i] > ma_200d_series.iloc[-i] and
                    ma_50d_series.iloc[-i-1] <= ma_200d_series.iloc[-i-1]):
                    golden_cross = True
                    break

        # Get financial metrics
        pe_ratio = info.get("trailingPE", info.get("forwardPE", "N/A"))
        eps = info.get("trailingEPS", info.get("forwardEPS", info.get("epsTrailingTwelveMonths", "N/A")))
        peg_ratio = info.get("pegRatio", info.get("fiveYearAvgDividendYield", "N/A"))
        pb_ratio = info.get("priceToBook", "N/A")
        short_percent_float = info.get("shortPercentOfFloat", "N/A")  # <-- Added

        # Debug info - print what we're getting from Yahoo Finance
        # print(f"Debug for {symbol}: EPS={eps}, PEG={peg_ratio}")

        # Compile stock data
        stock_data = {
            "symbol": symbol,
            "current_price": current_price,
            "pe_ratio": pe_ratio,  # P/E Ratio (TTM)
            "eps": eps,  # Earnings Per Share (TTM)
            "peg_ratio": peg_ratio,  # PEG Ratio
            "pb_ratio": pb_ratio,  # P/B Ratio
            "short_percent_float": short_percent_float,  # <-- Added
            "open_price": current_data["Open"],
            "high_price": current_data["High"],
            "low_price": current_data["Low"],
            "volume": current_data["Volume"],
            "daily_change": daily_change,
            "percentage_change": percentage_change,
            "market_cap": info.get("marketCap", "N/A"),
            "previous_close": previous_close,
            "ma_50d": ma_50d,  # 50-day moving average
            "ma_200d": ma_200d,  # 200-day moving average
            "golden_cross": golden_cross,  # Golden Cross indicator
            "timestamp": datetime.now(),
        }

        return stock_data

    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {str(e)}")
        return None


def format_currency(value):
    """Format currency values in billions"""
    if pd.isna(value) or value == "N/A":
        return "N/A"

    if isinstance(value, str):
        return value

    # Always show market cap in billions for large values
    if value >= 1e9:
        return f"${value/1e9:.2f}B"
    elif value >= 1e6:
        return f"${value/1e6:.2f}M"
    else:
        return f"${value:,.2f}"


def format_volume(volume):
    """Format volume in millions"""
    if pd.isna(volume) or volume == "N/A":
        return "N/A"

    # Always show volume in millions for large values
    if volume >= 1e6:
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
    change_color = "green" if stock_data["daily_change"] >= 0 else "red"
    change_symbol = "+" if stock_data["daily_change"] >= 0 else ""

    # Create card layout
    with st.container():
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

        with col1:
            st.subheader(f"{stock_data['symbol']} - {company_name}")
            st.metric(
                label="Current Price",
                value=f"${stock_data['current_price']:.2f}",
                delta=f"{change_symbol}{stock_data['daily_change']:.2f} ({change_symbol}{stock_data['percentage_change']:.2f}%)",
            )

        with col2:
            st.metric("Volume", format_volume(stock_data["volume"]))
            st.metric("Market Cap", format_currency(stock_data["market_cap"]))

        with col3:
            st.metric("Open", f"${stock_data['open_price']:.2f}")
            st.metric("High", f"${stock_data['high_price']:.2f}")

        with col4:
            st.metric("Low", f"${stock_data['low_price']:.2f}")

            # Display 50-day moving average if available
            ma_50d_value = "N/A"
            if stock_data["ma_50d"] is not None:
                ma_50d_value = f"${stock_data['ma_50d']:.2f}"
            st.metric("50-Day MA", ma_50d_value)

            # Display 200-day moving average if available
            ma_200d_value = "N/A"
            if stock_data["ma_200d"] is not None:
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
            if stock_data["pe_ratio"] != "N/A" and stock_data["pe_ratio"] is not None:
                pe_ratio_value = f"{stock_data['pe_ratio']:.2f}"

            # Format 50-day moving average
            ma_50d_value = "N/A"
            if stock_data["ma_50d"] is not None:
                ma_50d_value = f"${stock_data['ma_50d']:.2f}"

            # Format 200-day moving average
            ma_200d_value = "N/A"
            if stock_data["ma_200d"] is not None:
                ma_200d_value = f"${stock_data['ma_200d']:.2f}"

            # Format percentage change with color
            percentage_change = stock_data["percentage_change"]
            is_positive = percentage_change >= 0
            change_symbol = "+" if is_positive else ""

            short_percent_float_raw = stock_data.get("short_percent_float", "N/A")
            if short_percent_float_raw == "N/A" or short_percent_float_raw is None:
                short_percent_float_display = "N/A"
            else:
                short_percent_float_display = f"{short_percent_float_raw*100:.2f}%"

            summary_data.append(
                {
                    "Symbol": symbol,
                    "Company": STOCKS[symbol],
                    "Current Price": f"${stock_data['current_price']:.2f}",
                    "P/E (TTM)": pe_ratio_value,
                    "Daily Change": f"{stock_data['daily_change']:+.2f} ({change_symbol}{percentage_change:.2f}%)",
                    "200-Day MA": ma_200d_value,  # Swapped position with 50-Day MA
                    "50-Day MA": ma_50d_value,  # Swapped position with 200-Day MA
                    "Volume": format_volume(stock_data["volume"]),
                    "Market Cap": format_currency(stock_data["market_cap"]),
                    "Short % Float": short_percent_float_display,  # <-- Added
                }
            )
    if summary_data:
        raw_data = []
        for symbol, stock_data in all_stock_data.items():
            if stock_data is not None:
                # Get raw numerical values for sorting
                pe_ratio_raw = stock_data["pe_ratio"]
                if pe_ratio_raw == "N/A" or pe_ratio_raw is None:
                    pe_ratio_raw = float("nan")

                ma_50d_raw = (
                    stock_data["ma_50d"]
                    if stock_data["ma_50d"] is not None
                    else float("nan")
                )
                ma_200d_raw = (
                    stock_data["ma_200d"]
                    if stock_data["ma_200d"] is not None
                    else float("nan")
                )

                # Format for display
                pe_ratio_display = "N/A"
                if (
                    stock_data["pe_ratio"] != "N/A"
                    and stock_data["pe_ratio"] is not None
                ):
                    pe_ratio_display = f"{stock_data['pe_ratio']:.2f}"

                ma_50d_display = "N/A"
                if stock_data["ma_50d"] is not None:
                    ma_50d_display = f"${stock_data['ma_50d']:.2f}"

                ma_200d_display = "N/A"
                if stock_data["ma_200d"] is not None:
                    ma_200d_display = f"${stock_data['ma_200d']:.2f}"

                # Format percentage change
                percentage_change = stock_data["percentage_change"]
                is_positive = percentage_change >= 0
                change_symbol = "+" if is_positive else ""

                # Add to raw data for DataFrame
                # Format Golden Cross indicator
                golden_cross = stock_data["golden_cross"]
                golden_cross_display = "✓" if golden_cross else "✗"

                # Format EPS, PEG ratio, and P/B ratio
                eps_raw = stock_data["eps"]
                if eps_raw == "N/A" or eps_raw is None:
                    eps_raw = float("nan")
                    eps_display = "N/A"
                else:
                    eps_display = f"{eps_raw:.2f}"

                peg_ratio_raw = stock_data["peg_ratio"]
                if peg_ratio_raw == "N/A" or peg_ratio_raw is None:
                    peg_ratio_raw = float("nan")
                    peg_ratio_display = "N/A"
                else:
                    peg_ratio_display = f"{peg_ratio_raw:.2f}"

                pb_ratio_raw = stock_data["pb_ratio"]
                if pb_ratio_raw == "N/A" or pb_ratio_raw is None:
                    pb_ratio_raw = float("nan")
                    pb_ratio_display = "N/A"
                else:
                    pb_ratio_display = f"{pb_ratio_raw:.2f}"

                short_percent_float_raw = stock_data.get("short_percent_float", "N/A")
                if short_percent_float_raw == "N/A" or short_percent_float_raw is None:
                    short_percent_float_val = float("nan")
                    short_percent_float_display = "N/A"
                else:
                    short_percent_float_val = short_percent_float_raw * 100
                    short_percent_float_display = f"{short_percent_float_val:.2f}%"

                raw_data.append(
                    {
                        "Symbol": symbol,
                        "Company": STOCKS[symbol],
                        "Current Price": stock_data["current_price"],
                        "Current Price Display": f"${stock_data['current_price']:.2f}",
                        "P/E (TTM)": pe_ratio_raw,
                        "P/E (TTM) Display": pe_ratio_display,
                        "EPS (TTM)": eps_raw,
                        "EPS (TTM) Display": eps_display,
                        "PEG Ratio": peg_ratio_raw,
                        "PEG Ratio Display": peg_ratio_display,
                        "P/B Ratio": pb_ratio_raw,
                        "P/B Ratio Display": pb_ratio_display,
                        "Daily Change": percentage_change,  # Store percentage change for sorting
                        "Daily Change Display": f"{change_symbol}{percentage_change:.2f}%",  # Percentage only display
                        "Golden Cross": golden_cross,  # Boolean for sorting
                        "Golden Cross Display": golden_cross_display,  # Display value
                        "200-Day MA": ma_200d_raw,
                        "200-Day MA Display": ma_200d_display,
                        "50-Day MA": ma_50d_raw,
                        "50-Day MA Display": ma_50d_display,
                        "Short % Float": short_percent_float_val,  # For sorting
                        "Short % Float Display": short_percent_float_display,
                        # Convert volume to millions for sorting and display
                        "Volume": (
                            stock_data["volume"] / 1e6
                            if stock_data["volume"] != "N/A"
                            else float("nan")
                        ),
                        "Volume Display": format_volume(stock_data["volume"]),
                        # Convert market cap to billions for sorting and display
                        "Market Cap": (
                            stock_data["market_cap"] / 1e9
                            if stock_data["market_cap"] != "N/A"
                            else float("nan")
                        ),
                        "Market Cap Display": format_currency(stock_data["market_cap"]),
                    }
                )

        # Create DataFrame with both raw and display values
        df_raw = pd.DataFrame(raw_data)

        # Add a colored display for Golden Cross with symbols
        df_raw["Golden Cross Colored"] = df_raw["Golden Cross"].apply(
            lambda x: '<span style="color: green; font-weight: bold;">✓</span>' if x else '<span style="color: red; font-weight: bold;">✗</span>'
        )

        # Create a display DataFrame with clickable symbols and other columns
        display_df = pd.DataFrame(
            {
                "Symbol": [f'<a href="#" onclick="parent.postMessage({{cmd: \'streamlit:setComponentValue\', componentValue: \'{symbol}\', componentKey: \'stock_click\'}}, \'*\'); return false;" style="text-decoration: none; color: #1E88E5; font-weight: bold;">{symbol}</a>' for symbol in df_raw["Symbol"]],
                "Company": df_raw["Company"],
                "Current Price": df_raw["Current Price Display"],
                "Daily Change": df_raw["Daily Change Display"],
                "P/E (TTM)": df_raw["P/E (TTM) Display"],
                "EPS (TTM)": df_raw["EPS (TTM) Display"],
                "PEG Ratio": df_raw["PEG Ratio Display"],
                "P/B Ratio": df_raw["P/B Ratio Display"],
                "Short % Float": df_raw["Short % Float Display"],
                "Golden Cross": df_raw["Golden Cross Colored"],  # <-- Use colored HTML
                "200-Day MA": df_raw["200-Day MA Display"],
                "50-Day MA": df_raw["50-Day MA Display"],
                "Volume": df_raw["Volume Display"],
                "Market Cap": df_raw["Market Cap Display"],
            }
        )

        # Show summary table with HTML coloring for Golden Cross
        st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.error("No stock data available to display in summary table")


def main():
    """Main application function"""
    # Initialize session state for navigation
    if 'viewing_stock' not in st.session_state:
        st.session_state.viewing_stock = None

    if 'selected_tab' not in st.session_state:
        st.session_state.selected_tab = 0

    # Custom styled title - SparkVibe with trumpet logo
    st.markdown("""
    <h1 style="text-align: center; font-family: 'Times New Roman', serif; font-size: 32px; color: #1E3A8A; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);">
        🎺 SparkVibe <span style="font-size: 24px; color: #4B5563;">Finance</span>
    </h1>
    """, unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-style: italic; color: #4B5563;'>Real-time stock prices and trading metrics for leading tech companies</p>", unsafe_allow_html=True)

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
    tab1, tab2, tab3 = st.tabs(["📊 Summary Table", "📋 Detailed Cards", "🔍 Golden Cross"])

    # If a stock is selected for viewing, show its details
    if st.session_state.viewing_stock:
        selected_symbol = st.session_state.viewing_stock
        if selected_symbol in all_stock_data and all_stock_data[selected_symbol] is not None:
            st.subheader(f"Detailed View: {selected_symbol} - {STOCKS[selected_symbol]}")
            display_stock_card(all_stock_data[selected_symbol], STOCKS[selected_symbol])

            # Get historical data for chart
            ticker = yf.Ticker(selected_symbol)
            hist = ticker.history(period="250d")

            if not hist.empty and len(hist) >= 50:
                # Calculate moving averages
                hist['MA50'] = hist['Close'].rolling(window=50).mean()
                hist['MA200'] = hist['Close'].rolling(window=200).mean()

                # Create chart
                st.subheader(f"Price History and Moving Averages")
                chart_data = pd.DataFrame({
                    'Date': hist.index,
                    'Price': hist['Close'],
                    '50-Day MA': hist['MA50'],
                    '200-Day MA': hist['MA200']
                })

                st.line_chart(chart_data.set_index('Date')[['Price', '50-Day MA', '200-Day MA']])

            # Add a button to go back to the main view
            if st.button("← Back to Summary"):
                st.session_state.viewing_stock = None
                st.rerun()

            # Early return to not show the tabs
            return

    # Add a component to capture clicks on stock symbols
    stock_click = st.text_input("stock_click", "", key="stock_click", label_visibility="collapsed")
    if stock_click and stock_click in STOCKS:
        st.session_state.viewing_stock = stock_click
        st.rerun()

    # Add JavaScript to handle clicks on stock symbols
    st.markdown("""
    <script>
    // Function to handle clicks on stock symbols
    document.addEventListener('DOMContentLoaded', function() {
        // Add click event listeners to all stock symbol links
        document.querySelectorAll('a.stock-link').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const symbol = this.getAttribute('data-symbol');
                window.parent.postMessage({
                    cmd: 'streamlit:setComponentValue',
                    componentValue: symbol,
                    componentKey: 'stock_click'
                }, '*');
            });
        });
    });
    </script>
    """, unsafe_allow_html=True)

    with tab1:
        st.subheader("Tech Stocks Summary")
        create_summary_table(all_stock_data)

    with tab2:
        st.subheader("Detailed Stock Information")

        # Add a selectbox to jump to a specific stock
        selected_stock = st.selectbox(
            "Jump to stock:",
            options=list(STOCKS.keys()),
            format_func=lambda x: f"{x} - {STOCKS[x]}"
        )

        if selected_stock:
            st.markdown(f"### {selected_stock} - {STOCKS[selected_stock]}")
            display_stock_card(all_stock_data[selected_stock], STOCKS[selected_stock])
            st.markdown("---")

        # Display all other stocks
        for symbol, company_name in STOCKS.items():
            if symbol != selected_stock:  # Skip the already displayed selected stock
                display_stock_card(all_stock_data[symbol], company_name)

    with tab3:
        st.subheader("Golden Cross Stocks")
        # Filter stocks with golden cross and remove any None values
        golden_cross_stocks = {symbol: data for symbol, data in all_stock_data.items()
                              if data is not None and data.get("golden_cross", False)}

        if golden_cross_stocks:
            st.success(f"Found {len(golden_cross_stocks)} stocks with a golden cross in the past 30 days")

            # Create a table with stock information - using markdown to avoid st.table's non-interactive nature
            st.markdown("### Golden Cross Stocks")

            # Create a DataFrame for display with clickable symbols
            golden_cross_data = []
            for symbol, data in golden_cross_stocks.items():
                # Format daily change with color
                daily_change = data['percentage_change']
                change_color = "green" if daily_change >= 0 else "red"
                change_symbol = "+" if daily_change >= 0 else ""
                formatted_change = f'<span style="color: {change_color};">{change_symbol}{daily_change:.2f}%</span>'

                golden_cross_data.append({
                    "Symbol": f'<a href="#" onclick="parent.postMessage({{cmd: \'streamlit:setComponentValue\', componentValue: \'{symbol}\', componentKey: \'stock_click\'}}, \'*\'); return false;" style="text-decoration: none; color: #1E88E5; font-weight: bold;">{symbol}</a>',
                    "Company": STOCKS[symbol],
                    "Current Price": f"${data['current_price']:.2f}",
                    "Daily Change": formatted_change,
                    "Golden Cross": '<span style="color: green; font-weight: bold;">✓</span>'
                })

            golden_cross_df = pd.DataFrame(golden_cross_data)

            # Display the table with clickable symbols
            st.markdown(golden_cross_df.to_html(escape=False, index=False), unsafe_allow_html=True)

            # Display charts for all golden cross stocks
            st.markdown("### Golden Cross Charts")

            # Show charts for each stock with golden cross
            for symbol, stock_data in golden_cross_stocks.items():
                st.subheader(f"📊 {symbol} - {STOCKS[symbol]}")

                # Fetch historical data for the past 250 days
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="250d")

                if not hist.empty and len(hist) >= 200:
                    # Calculate moving averages
                    hist['MA50'] = hist['Close'].rolling(window=50).mean()
                    hist['MA200'] = hist['Close'].rolling(window=200).mean()

                    # Create a DataFrame for the chart
                    chart_data = pd.DataFrame({
                        'Date': hist.index,
                        'Price': hist['Close'],
                        '50-Day MA': hist['MA50'],
                        '200-Day MA': hist['MA200']
                    })

                    # Find the crossover point(s)
                    crossover_points = []
                    for i in range(1, len(hist)):
                        if (hist['MA50'].iloc[i] > hist['MA200'].iloc[i] and
                            hist['MA50'].iloc[i-1] <= hist['MA200'].iloc[i-1]):
                            crossover_points.append(i)

                    # Create the chart
                    chart = st.line_chart(
                        chart_data.set_index('Date')[['Price', '50-Day MA', '200-Day MA']]
                    )

                    # Add annotation about the crossover
                    if crossover_points:
                        latest_crossover = crossover_points[-1]
                        crossover_date = hist.index[latest_crossover].strftime('%Y-%m-%d')
                        crossover_price = hist['Close'].iloc[latest_crossover]
                        st.caption(f"⭐ Golden Cross occurred on {crossover_date} at price ${crossover_price:.2f}")

                st.markdown("---")  # Add a separator between charts

            # Add explanation
            st.markdown("### About Golden Cross")
            st.write("A golden cross occurs when the 50-day moving average crosses above the 200-day moving average. "
                     "This is often considered a bullish signal by technical analysts.")
            st.write("The charts above show stocks that have experienced a golden cross in the past 30 days.")
        else:
            st.warning("No stocks with a golden cross in the past 30 days were found")

    # Auto-refresh functionality
    if auto_refresh:
        time.sleep(30)
        st.rerun()

    # Footer information
    st.markdown("---")
    st.markdown(
        "**Note:** Stock prices are fetched from Yahoo Finance and may have a slight delay. This application is for informational purposes only and should not be used as the sole basis for investment decisions."
    )


if __name__ == "__main__":
    main()
