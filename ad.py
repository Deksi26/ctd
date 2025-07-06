import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta

# ==== Konfiguracija ==== 
st.set_page_config(layout="wide", page_title="Kripto Skok Detektor", page_icon="🚀")
st.title("🚀 Kripto Skok Detektor – Prva linija lova na mete")

# ==== Filteri ====
st.sidebar.header("🔍 Filteri za skok")
vs_currency = st.sidebar.selectbox("Valuta prikaza", options=['usd', 'eur'], index=0)
time_period = st.sidebar.selectbox("Vremenski period", ['1h', '24h'], index=1)
skok_threshold = st.sidebar.slider("📈 Minimalni skok (%)", 10, 200, 30)
min_market_cap = st.sidebar.number_input("💰 Maksimalni Market Cap (miliona)", value=5)
max_price = st.sidebar.number_input("🎯 Maksimalna cena (USDT)", value=0.1)
min_volume = st.sidebar.number_input("📊 Minimalni volumen (miliona)", value=0.5)

# ==== API pozivi ====
@st.cache_data(ttl=1800)
def get_top_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': vs_currency,
        'order': 'market_cap_asc',
        'per_page': 250,
        'page': 1,
        'price_change_percentage': '1h,24h,7d'
    }
    return pd.DataFrame(requests.get(url, params=params).json())

@st.cache_data(ttl=3600)
def get_fundamentals(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        data = requests.get(url).json()
        genesis = data.get('genesis_date')
        twitter = data.get('community_data', {}).get('twitter_followers')
        github = data.get('developer_data', {}).get('commit_count_4_weeks')
        return genesis, twitter, github
    except:
        return None, None, None

# ==== Dohvatanje podataka ====
st.info("⏳ Učitavanje podataka sa tržišta...")
df = get_top_coins()
change_col = 'price_change_percentage_24h_in_currency' if time_period == '24h' else 'price_change_percentage_1h_in_currency'

# ==== Primarna filtracija ====
df = df[(df[change_col] >= skok_threshold) &
        (df['market_cap'] <= min_market_cap * 1e6) &
        (df['current_price'] <= max_price) &
        (df['total_volume'] >= min_volume * 1e6)]

# ==== Dodavanje fundamentalnih podataka ====
st.info("🔍 Analiza fundamentalnih podataka...")
rows = []
now = datetime.utcnow()
for _, row in df.iterrows():
    genesis, twitter, github = get_fundamentals(row['id'])
    try:
        genesis_obj = datetime.strptime(genesis, "%Y-%m-%d") if genesis else None
    except:
        genesis_obj = None

    is_target = (
        genesis_obj and genesis_obj > now - timedelta(days=90) and
        (twitter or 0) > 1000 and
        (github or 0) > 0
    )

    rows.append({
        "Name": row['name'],
        "Symbol": row['symbol'].upper(),
        "Price": f"{row['current_price']:.4f}",
        "% Skok": f"{row[change_col]:.2f}%",
        "Market Cap": f"{row['market_cap'] / 1e6:,.2f}M",
        "Volume": f"{row['total_volume'] / 1e6:,.2f}M",
        "Genesis Date": genesis if genesis else "-",
        "Twitter Followers": f"{twitter:,}" if twitter else "-",
        "GitHub Commits": f"{github}" if github else "-",
        "🎯 Meta?": "✅" if is_target else ""
    })

result_df = pd.DataFrame(rows)

st.success(f"🎯 Pronađeno {len(result_df)} potencijalnih tokena koji ispunjavaju kriterijume!")
st.dataframe(result_df, use_container_width=True)

# ==== Telegram notifikacija za prave mete ====
for _, row in result_df.iterrows():
    if row['🎯 Meta?'] == "✅":
        try:
            token = st.secrets["TELEGRAM_BOT_TOKEN"]
            chat_id = st.secrets["TELEGRAM_CHAT_ID"]
            text = f"🎯 Meta otkrivena: {row['Name']} ({row['Symbol']}) – Skok: {row['% Skok']}"
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, data={"chat_id": chat_id, "text": text})
        except:
            pass
