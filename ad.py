import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta
import time

# ==== Konfiguracija stranice ====
st.set_page_config(layout="wide", page_title="Kripto Skok Detektor", page_icon="🚀")
st.title("🚀 Kripto Skok Detektor")

# ==== Help tekst ====
with st.expander("🧠 Kako koristiti aplikaciju - Strategija"):
    st.markdown("""
### 🎯 Cilj:
Pronaći male, brzo rastuće kriptovalute sa potencijalom za eksploziju (100%+ skok).

### 🔍 Filtriramo:
- Market Cap < **5 miliona $**
- Cena < **0.1 USDT**
- Volume > **500.000 $**
- Promena > **30%** (u 1h ili 24h)

### 📊 Gledamo dodatno:
- **Genesis Date**: poslednja 3 meseca
- **Twitter Followers**: 1000+
- **GitHub aktivnost**: da postoji

### ✅ Naša "Meta":
Tokeni koji ispunjavaju sve kriterijume ✔

### 📤 Telegram:
Automatski šalje upozorenje za mete koje ispunjavaju kriterijume
""")

# ==== Sidebar filteri ====
st.sidebar.header("⚙️ Filteri")
vs_currency = st.sidebar.selectbox("Valuta prikaza", options=['usd', 'eur'], index=0)
time_period = st.sidebar.selectbox("Vremenski period", ['1h', '24h', '7d'], index=0)
skok_threshold = st.sidebar.slider("% Skoka (min)", 10, 500, 30)

# ==== API dohvat podataka ====
@st.cache_data(ttl=3600)
def get_top_coins():
    url = f"https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': vs_currency,
        'order': 'market_cap_asc',
        'per_page': 250,
        'page': 1,
        'price_change_percentage': '1h,24h,7d'
    }
    response = requests.get(url, params=params)
    return pd.DataFrame(response.json())

@st.cache_data(ttl=3600)
def get_fundamentals(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        data = requests.get(url).json()
        return {
            'id': data.get('id'),
            'Genesis Date': data.get('genesis_date'),
            'Twitter Followers': data.get('community_data', {}).get('twitter_followers', 0),
            'GitHub Commits (4w)': data.get('developer_data', {}).get('commit_count_4_weeks', 0),
        }
    except:
        return {}

with st.spinner("🔄 Učitavanje podataka sa CoinGecko API-ja..."):
    df = get_top_coins()
    change_column = {
        '1h': 'price_change_percentage_1h_in_currency',
        '24h': 'price_change_percentage_24h_in_currency',
        '7d': 'price_change_percentage_7d_in_currency',
    }[time_period]

    df = df[df['market_cap'] <= 5_000_000]
    df = df[df['current_price'] <= 0.1]
    df = df[df['total_volume'] >= 500_000]
    df = df[df[change_column] >= skok_threshold]
    df = df.dropna(subset=[change_column])
    df = df.sort_values(change_column, ascending=False)

    if df.empty:
        st.warning("⚠️ Nema tokena koji ispunjavaju sve filtere. Pokušaj sa manjim uslovima.")
    else:
        st.subheader("🔢 Tokeni koji ispunjavaju kriterijume")
        rows = []
        for _, row in df.iterrows():
            fundamentals = get_fundamentals(row['id'])
            genesis_date = fundamentals.get("Genesis Date")
            recent_token = False
            if genesis_date:
                try:
                    recent_token = datetime.strptime(genesis_date, "%Y-%m-%d") >= datetime.today() - timedelta(days=90)
                except:
                    pass

            is_meta = all([
                row['market_cap'] <= 5_000_000,
                row['current_price'] <= 0.1,
                row['total_volume'] >= 500_000,
                row[change_column] >= skok_threshold,
                fundamentals.get("Twitter Followers", 0) >= 1000,
                fundamentals.get("GitHub Commits (4w)", 0) > 0,
                recent_token
            ])

            rows.append({
                "Name": row['name'],
                "Symbol": row['symbol'],
                "Price": f"{row['current_price']:,.4f}",
                f"% Change ({time_period})": f"{row[change_column]:.2f}%",
                "Market Cap": f"{row['market_cap']:,.0f}",
                "Volume": f"{row['total_volume']:,.0f}",
                "Genesis Date": genesis_date if genesis_date else "",
                "Twitter Followers": f"{fundamentals.get('Twitter Followers', 0):,}",
                "GitHub (4w)": f"{fundamentals.get('GitHub Commits (4w)', 0):,}",
                "🌟 Meta?": "🌟" if is_meta else ""
            })

        df_final = pd.DataFrame(rows)
        st.dataframe(df_final, use_container_width=True)
