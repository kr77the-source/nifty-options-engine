import datetime
import pandas as pd
import streamlit as st
import yfinance as yf

# Streamlit Page Config
st.set_page_config(
    page_title="3-Case Daily Bias & S&R System", page_icon="📈", layout="centered"
)

st.title("📈 3-Case Daily Bias & S&R Dashboard")
st.write(
    "Live Stock/Index data, Daily Bias, aur Support/Resistance levels upar dekhein."
)

# Top F&O Indices & Stocks Database
STOCK_DATABASE = [
    "^NSEI",  # Nifty 50
    "^BSESN",  # Sensex
    "^NSEBANK",  # Bank Nifty
    "TCS.NS",
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "INFY.NS",
    "SBIN.NS",
    "BAJFINANCE.NS",
    "MARUTI.NS",
    "HCLTECH.NS",
    "APOLLOHOSP.NS",
    "TATASTEEL.NS",
    "TATAMOTORS.NS",
]

# Compact Input Layout
col_inp1, col_inp2 = st.columns(2)
with col_inp1:
    selected_symbol = st.selectbox("Stock / Index:", options=STOCK_DATABASE)
with col_inp2:
    custom_ticker = st.text_input("Custom Ticker:", placeholder="e.g. NIFTY")

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

if st.button("Analyze Now", type="primary"):
    with st.spinner(f"Fetching data for {symbol}..."):
        try:
            ticker = yf.Ticker(symbol)
            df_daily = ticker.history(period="7d", interval="1d")

            if len(df_daily) < 2:
                st.error(
                    "Error: Live data fetch nahi ho paya. Ticker check karein."
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

                # Pivot & S&R Calculations (S1-S3 & R1-R3)
                pivot = (pdh + pdl + pdc) / 3
                r1 = round((2 * pivot) - pdl, 2)
                r2 = round(pivot + (pdh - pdl), 2)
                r3 = round(pdh + 2 * (pivot - pdl), 2)

                s1 = round((2 * pivot) - pdh, 2)
                s2 = round(pivot - (pdh - pdl), 2)
                s3 = round(pdl - 2 * (pdh - pivot), 2)

                # Case 1 & Case 2 Biases
                case1_bias = (
                    "BULLISH"
                    if close_position >= 0.70
                    else ("BEARISH" if close_position <= 0.30 else "NEUTRAL")
                )
                case2_bias = (
                    "BEARISH SWEEP"
                    if (curr_high > pdh and curr_close < pdh)
                    else (
                        "BULLISH SWEEP"
                        if (curr_low < pdl and curr_close > pdl)
                        else "NO SWEEP"
                    )
                )

                df_15m = ticker.history(period="2d", interval="15m")
                current_price = (
                    df_15m.iloc[-1]["Close"] if not df_15m.empty else curr_close
                )

                final_bias = "NEUTRAL / NO CLEAR SETUP"
                entry_price = round(current_price, 2)
                stop_loss = 0.0
                target_1 = 0.0
                target_2 = 0.0

                if "BULLISH SWEEP" in case2_bias or (
                    "BULLISH" in case1_bias and current_price > pdc
                ):
                    final_bias = "BUY (LONG)"
                    stop_loss = round(min(curr_low, pdl) * 0.998, 2)
                    target_1 = round(entry_price + (daily_range * 0.60), 2)
                    target_2 = round(
                        max(entry_price + (daily_range * 1.2), pdh), 2
                    )

                elif "BEARISH SWEEP" in case2_bias or (
                    "BEARISH" in case1_bias and current_price < pdc
                ):
                    final_bias = "SELL (SHORT)"
                    stop_loss = round(max(curr_high, pdh) * 1.002, 2)
                    target_1 = round(entry_price - (daily_range * 0.60), 2)
                    target_2 = round(
                        min(entry_price - (daily_range * 1.2), pdl), 2
                    )

                # --- DASHBOARD DISPLAY ---
                st.markdown(f"### 📌 Dashboard: {symbol}")

                # Metrics Row
                m1, m2, m3 = st.columns(3)
                m1.metric("Spot Price", f"₹{entry_price}")
                m2.metric("PDH", f"₹{round(pdh, 2)}")
                m3.metric("PDL", f"₹{round(pdl, 2)}")

                # Support & Resistance Table (Side-by-Side Clean Layout)
                sr_data = {
                    "Supports (S)": [f"S1: ₹{s1}", f"S2: ₹{s2}", f"S3: ₹{s3}"],
                    "Resistances (R)": [f"R1: ₹{r1}", f"R2: ₹{r2}", f"R3: ₹{r3}"],
                }
                st.table(pd.DataFrame(sr_data))

                # Final Bias Result Box
                if final_bias == "BUY (LONG)":
                    st.success(f"**FINAL BIAS:** {final_bias}")
                elif final_bias == "SELL (SHORT)":
                    st.error(f"**FINAL BIAS:** {final_bias}")
                else:
                    st.warning(f"**FINAL BIAS:** {final_bias}")

                # Targets & SL Row
                if final_bias in ["BUY (LONG)", "SELL (SHORT)"]:
                    t_col1, t_col2, t_col3 = st.columns(3)
                    t_col1.metric("Stop Loss", f"₹{stop_loss}")
                    t_col2.metric("Target 1", f"₹{target_1}")
                    t_col3.metric("Target 2", f"₹{target_2}")

        except Exception as e:
            st.error(f"Error processing data: {e}")
