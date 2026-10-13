import datetime
import pandas as pd
import streamlit as st
import yfinance as yf

# Streamlit Page Config
st.set_page_config(
    page_title="3-Case Daily Bias & Option Chain",
    page_icon="📈",
    layout="centered",
)

st.title("📈 3-Case Daily Bias & Option Setup")
st.write(
    "Live Data, Support/Resistance (S1-S3, R1-R3) aur ₹2-3 Option Chain ek sath upar."
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

# Compact Input Layout using Columns
col_inp1, col_inp2 = st.columns(2)
with col_inp1:
    selected_symbol = st.selectbox("Stock / Index:", options=STOCK_DATABASE)
with col_inp2:
    custom_ticker = st.text_input(
        "Custom Ticker (Opt):", placeholder="e.g. NIFTY"
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

ticker = yf.Ticker(symbol)
try:
    available_expiries = ticker.options
except Exception:
    available_expiries = []

selected_expiry = st.selectbox(
    "Option Chain Expiry:",
    options=available_expiries if available_expiries else ["N/A"],
)

if st.button("Analyze Now", type="primary"):
    with st.spinner("Fetching data..."):
        try:
            df_daily = ticker.history(period="7d", interval="1d")

            if len(df_daily) < 2:
                st.error("Error: Data fetch nahi ho paya.")
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

                # Pivot & S&R Calculations (S1, S2, S3 & R1, R2, R3)
                pivot = (pdh + pdl + pdc) / 3
                r1 = round((2 * pivot) - pdl, 2)
                r2 = round(pivot + (pdh - pdl), 2)
                r3 = round(pdh + 2 * (pivot - pdl), 2)

                s1 = round((2 * pivot) - pdh, 2)
                s2 = round(pivot - (pdh - pdl), 2)
                s3 = round(pdl - 2 * (pdh - pivot), 2)

                # Biases
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

                final_bias = "NEUTRAL"
                entry_price = round(current_price, 2)
                stop_loss = 0.0
                target_1 = 0.0
                target_2 = 0.0
                option_action = "NO TRADE"
                suggested_option = "N/A"
                found_option_price = 0.0

                if "BULLISH SWEEP" in case2_bias or (
                    "BULLISH" in case1_bias and current_price > pdc
                ):
                    final_bias = "BUY (LONG)"
                    stop_loss = round(min(curr_low, pdl) * 0.998, 2)
                    target_1 = round(entry_price + (daily_range * 0.60), 2)
                    target_2 = round(
                        max(entry_price + (daily_range * 1.2), pdh), 2
                    )

                    if selected_expiry and selected_expiry != "N/A":
                        try:
                            opt_chain = ticker.option_chain(selected_expiry)
                            otm_calls = opt_chain.calls[
                                opt_chain.calls["strike"] > current_price
                            ].copy()
                            if not otm_calls.empty:
                                otm_calls["diff"] = abs(
                                    otm_calls["lastPrice"] - 2.5
                                )
                                best_row = otm_calls.loc[
                                    otm_calls["diff"].idxmin()
                                ]
                                suggested_option = f"{int(best_row['strike'])} CE ({selected_expiry})"
                                found_option_price = best_row["lastPrice"]
                                option_action = "BUY OTM CALL"
                        except Exception:
                            pass

                elif "BEARISH SWEEP" in case2_bias or (
                    "BEARISH" in case1_bias and current_price < pdc
                ):
                    final_bias = "SELL (SHORT)"
                    stop_loss = round(max(curr_high, pdh) * 1.002, 2)
                    target_1 = round(entry_price - (daily_range * 0.60), 2)
                    target_2 = round(
                        min(entry_price - (daily_range * 1.2), pdl), 2
                    )

                    if selected_expiry and selected_expiry != "N/A":
                        try:
                            opt_chain = ticker.option_chain(selected_expiry)
                            otm_puts = opt_chain.puts[
                                opt_chain.puts["strike"] < current_price
                            ].copy()
                            if not otm_puts.empty:
                                otm_puts["diff"] = abs(
                                    otm_puts["lastPrice"] - 2.5
                                )
                                best_row = otm_puts.loc[
                                    otm_puts["diff"].idxmin()
                                ]
                                suggested_option = f"{int(best_row['strike'])} PE ({selected_expiry})"
                                found_option_price = best_row["lastPrice"]
                                option_action = "BUY OTM PUT"
                        except Exception:
                            pass

                # --- COMPACT TOP DASHBOARD DISPLAY ---
                st.markdown(f"### 📌 Dashboard: {symbol}")

                # Top Row: Spot, PDH, PDL Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Spot", f"₹{entry_price}")
                m2.metric("PDH", f"₹{round(pdh, 2)}")
                m3.metric("PDL", f"₹{round(pdl, 2)}")

                # S&R Table (S1-S3 & R1-R3 Side-by-Side Compact Layout)
                sr_data = {
                    "Level": ["Level 1", "Level 2", "Level 3"],
                    "Support": [f"₹{s1}", f"₹{s2}", f"₹{s3}"],
                    "Resistance": [f"₹{r1}", f"₹{r2}", f"₹{r3}"],
                }
                st.dataframe(pd.DataFrame(sr_data), use_container_width=True)

                # Final Bias & Option Setup Box
                if final_bias == "BUY (LONG)":
                    st.success(
                        f"**BIAS:** {final_bias} | **Action:** {option_action} -> **{suggested_option}** (LTP: ₹{round(found_option_price, 2)})"
                    )
                elif final_bias == "SELL (SHORT)":
                    st.error(
                        f"**BIAS:** {final_bias} | **Action:** {option_action} -> **{suggested_option}** (LTP: ₹{round(found_option_price, 2)})"
                    )
                else:
                    st.warning(f"**BIAS:** {final_bias} (No Clear Setup)")

                # Targets & SL Compact Row
                if final_bias in ["BUY (LONG)", "SELL (SHORT)"]:
                    t_col1, t_col2, t_col3 = st.columns(3)
                    t_col1.metric("Stop Loss", f"₹{stop_loss}")
                    t_col2.metric("Target 1", f"₹{target_1}")
                    t_col3.metric("Target 2", f"₹{target_2}")

        except Exception as e:
            st.error(f"Error: {e}")
