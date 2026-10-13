import datetime
import streamlit as st
import yfinance as yf

# Streamlit Page Config
st.set_page_config(
    page_title="3-Case Daily Bias & Cheap Options (₹2-3) System",
    page_icon="📈",
    layout="centered",
)

st.title("📈 3-Case Daily Bias & ₹2-3 Cheap Options Setup")
st.write(
    "Live F&O data analyze karke **₹2-3 (Deep OTM)** wale options entry ke sath dekhein."
)

# Top F&O Indices & Stocks Database
STOCK_DATABASE = [
    "^NSEI",  # Nifty 50
    "^BSESN",  # Sensex
    "^NSEBANK",  # Bank Nifty
    "HCLTECH.NS",  # HCL Technologies
    "TCS.NS",  # TCS
    "APOLLOHOSP.NS",  # Apollo Hospitals
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "INFY.NS",
    "BHARTIARTL.NS",
    "ITC.NS",
    "SBIN.NS",
    "BAJFINANCE.NS",
    "MARUTI.NS",
    "SUNPHARMA.NS",
    "TATASTEEL.NS",
    "TATAMOTORS.NS",
    "AXISBANK.NS",
    "KOTAKBANK.NS",
]

# 1. Share / Index Selection
selected_symbol = st.selectbox(
    "1. Stock / Index Choose Karein (Type to search):",
    options=STOCK_DATABASE,
    index=0,
)

# Custom ticker input option
custom_ticker = st.text_input(
    "Ya phir koi dusra F&O Ticker yahan type karein (Optional):",
    placeholder="e.g. NIFTY or RELIANCE",
)

if custom_ticker.strip():
    symbol = custom_ticker.strip().upper()
    if (
        not symbol.startswith("^")
        and not symbol.endswith(".NS")
        and not symbol.endswith(".BO")
    ):
        symbol += ".NS"
else:
    symbol = selected_symbol

# 2. Expiry Selection Dropdown
st.markdown("---")
expiry_type = st.selectbox(
    "2. Option Expiry Choose Karein:",
    options=[
        "Current Weekly Expiry",
        "Next Weekly Expiry",
        "Monthly Expiry",
    ],
    index=0,
)

if st.button("Analyze Cheap Options Setup"):
    with st.spinner(f"Fetching live data for {symbol}..."):
        try:
            ticker = yf.Ticker(symbol)
            df_daily = ticker.history(period="7d", interval="1d")

            if len(df_daily) < 2:
                st.error(
                    "Error: Live data fetch nahi ho paya. Ticker symbol check karein."
                )
            else:
                prev_day = df_daily.iloc[-2]
                curr_day = df_daily.iloc[-1]

                pdh = prev_day["High"]
                pdl = prev_day["Low"]
                pdc = prev_day["Close"]

                curr_high = curr_day["High"]
                curr_low = curr_day["Low"]
                curr_close = curr_day["Close"]

                daily_range = pdh - pdl
                close_position = (
                    (pdc - pdl) / daily_range if daily_range > 0 else 0.5
                )

                # CASE 1: Daily Closing Bias
                case1_bias = "NEUTRAL"
                if close_position >= 0.70:
                    case1_bias = "BULLISH (Strong High Close)"
                elif close_position <= 0.30:
                    case1_bias = "BEARISH (Strong Low Close)"

                # CASE 2: Liquidity Sweep
                case2_bias = "NO SWEEP"
                if curr_high > pdh and curr_close < pdh:
                    case2_bias = "BEARISH SWEEP (BSL Grabbed above PDH)"
                elif curr_low < pdl and curr_close > pdl:
                    case2_bias = "BULLISH SWEEP (SSL Grabbed below PDL)"

                # CASE 3: Intraday Current Price Data
                df_15m = ticker.history(period="2d", interval="15m")
                current_price = (
                    df_15m.iloc[-1]["Close"] if not df_15m.empty else curr_close
                )

                final_bias = "NEUTRAL / NO CLEAR DIRECTION"
                entry_price = 0.0
                stop_loss = 0.0
                target_1 = 0.0
                target_2 = 0.0

                # Determine Strike Step-up based on Underlying Price
                if current_price > 20000:
                    strike_step = 100
                elif current_price > 5000:
                    strike_step = 50
                elif current_price > 1000:
                    strike_step = 20
                elif current_price > 500:
                    strike_step = 10
                else:
                    strike_step = 5

                # Setup-based Strategy Calculations for ₹2-3 Cheap Options
                if "BULLISH SWEEP" in case2_bias or (
                    "BULLISH" in case1_bias and current_price > pdc
                ):
                    final_bias = "BUY (LONG)"
                    entry_price = round(current_price, 2)
                    stop_loss = round(min(curr_low, pdl) * 0.998, 2)
                    target_1 = round(entry_price + (daily_range * 0.60), 2)
                    target_2 = round(
                        max(entry_price + (daily_range * 1.2), pdh), 2
                    )

                    # Far OTM Call for ₹2-3 Rate (approx 3 to 4 steps away or based on volatility)
                    atm_strike = (
                        round(current_price / strike_step) * strike_step
                    )
                    cheap_otm_call_strike = atm_strike + (strike_step * 3)
                    option_action = f"BUY CHEAP OTM CALL (₹2-3 Target)"
                    suggested_option = (
                        f"{int(cheap_otm_call_strike)} CE ({expiry_type})"
                    )

                elif "BEARISH SWEEP" in case2_bias or (
                    "BEARISH" in case1_bias and current_price < pdc
                ):
                    final_bias = "SELL (SHORT)"
                    entry_price = round(current_price, 2)
                    stop_loss = round(max(curr_high, pdh) * 1.002, 2)
                    target_1 = round(entry_price - (daily_range * 0.60), 2)
                    target_2 = round(
                        min(entry_price - (daily_range * 1.2), pdl), 2
                    )

                    # Far OTM Put for ₹2-3 Rate
                    atm_strike = (
                        round(current_price / strike_step) * strike_step
                    )
                    cheap_otm_put_strike = atm_strike - (strike_step * 3)
                    option_action = f"BUY CHEAP OTM PUT (₹2-3 Target)"
                    suggested_option = (
                        f"{int(cheap_otm_put_strike)} PE ({expiry_type})"
                    )

                else:
                    option_action = "NO TRADE / WAIT FOR SETUP"
                    suggested_option = "N/A"

                # Display Results
                st.subheader(f"Results for: {symbol}")

                col1, col2, col3 = st.columns(3)
                col1.metric("Live Spot Price", f"₹{round(current_price, 2)}")
                col2.metric("PDH (High)", f"₹{round(pdh, 2)}")
                col3.metric("PDL (Low)", f"₹{round(pdl, 2)}")

                st.markdown("---")
                st.write(f"**Selected Expiry:** {expiry_type}")
                st.write(f"**[Case 1] Closing Bias:** {case1_bias}")
                st.write(f"**[Case 2] Liquidity Sweep:** {case2_bias}")
                st.markdown("---")

                if final_bias == "BUY (LONG)":
                    st.success(f"### UNDERLYING BIAS: {final_bias}")
                elif final_bias == "SELL (SHORT)":
                    st.error(f"### UNDERLYING BIAS: {final_bias}")
                else:
                    st.warning(f"### UNDERLYING BIAS: {final_bias}")

                # Options Trade Recommendation Box for Cheap Options
                if final_bias in ["BUY (LONG)", "SELL (SHORT)"]:
                    st.markdown(
                        "### 🎯 **₹2-3 CHEAP OPTIONS ENTRY (HIGH RISK / HIGH REWARD)**"
                    )

                    opt_col1, opt_col2 = st.columns(2)
                    opt_col1.metric("Option Action", option_action)
                    opt_col2.metric(
                        "Suggested Cheap Strike", suggested_option
                    )

                    st.markdown("---")
                    res_col1, res_col2 = st.columns(2)
                    res_col1.metric("Spot Entry Price", f"₹{entry_price}")
                    res_col2.metric("Spot Stop Loss", f"₹{stop_loss}")

                    st.markdown("#### 🎯 Spot Target Levels")
                    t_col1, t_col2 = st.columns(2)
                    t_col1.metric(
                        "Target 1 (Spot)",
                        f"₹{target_1}",
                        delta="60% Day Range",
                    )
                    t_col2.metric(
                        "Target 2 (Spot)",
                        f"₹{target_2}",
                        delta="Full Range Sweep",
                    )

                    st.warning(
                        f"⚠️ **Cheap Options Note:** Yeh **{suggested_option}** ek Far OTM contract hai jiska premium ₹2-3 ke aas-pass mil sakta hai (khaas kar expiry ke din). Isme risk high hota hai kyunki agar market momentum nahi aaya toh premium zero ho sakta hai. Chhote amount ke sath hi trade karein!"
                    )

        except Exception as e:
            st.error(f"Error processing data: {e}")
