import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(layout="wide", page_title="Kripto Skok Detektor", page_icon="🚀")
st.title("🚀 Kripto Skok Detektor – Lovac na eksplozivne mete")

# ==== Parametri ====
st.sidebar.header("⚙️ Filteri")
vs_currency = st.sidebar.selectbox("Valuta prikaza", options=['usd', 'eur'], index=0)
time_period = st.sidebar.selectbox("Vremenski period", ['1h', '24h', '7d'], index=1)
skok_threshold = st.sidebar.slider("Minimalni % skok", min_value=10, max_value=200, value=30)

# ==== Dohvatanje podataka ====
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
            'id': coin_id,
            'Genesis Date': data.get('genesis_date'),
            'Twitter Followers': data.get('community_data', {}).get('twitter_followers'),
            'GitHub Commits': data.get('developer_data', {}).get('commit_count_4_weeks')
        }
    except:
        return {'id': coin_id}

# ==== Obrada ====
with st.spinner("🔄 Učitavam podatke..."):
    df = get_top_coins()
    df = df[df['market_cap'] < 5_000_000]
    df = df[df['current_price'] < 0.1]
    df = df[df['total_volume'] > 500_000]

    change_column = {
        '1h': 'price_change_percentage_1h_in_currency',
        '24h': 'price_change_percentage_24h_in_currency',
        '7d': 'price_change_percentage_7d_in_currency',
    }[time_period]

    df = df[df[change_column] >= skok_threshold]
    df = df.dropna(subset=[change_column])
    df = df.sort_values(change_column, ascending=False).head(50)

    fundamentals = {item['id']: item for item in [get_fundamentals(row['id']) for _, row in df.iterrows()]}

# ==== Formatiranje tabele ====
data = []
for _, row in df.iterrows():
    fid = row['id']
    extra = fundamentals.get(fid, {})

    meta = (
        extra.get('Genesis Date') and
        pd.to_datetime(extra['Genesis Date'], errors='coerce') >= datetime.now() - timedelta(days=90) and
        extra.get('Twitter Followers', 0) > 1000 and
        extra.get('GitHub Commits', 0) > 0
    )

    data.append({
        'Name': row['name'],
        'Symbol': row['symbol'],
        'Price': f"{row['current_price']:,.4f}",
        f'% Change ({time_period})': f"{row[change_column]:.2f}%",
        'Market Cap': f"{row['market_cap']:,.0f}",
        'Volume': f"{row['total_volume']:,.0f}",
        'Genesis Date': extra.get('Genesis Date', ''),
        'Twitter Followers': f"{extra.get('Twitter Followers', 0):,}" if extra.get('Twitter Followers') else '',
        'GitHub Commits': f"{extra.get('GitHub Commits', 0):,}" if extra.get('GitHub Commits') else '',
        '🎯 Meta?': '✅' if meta else ''
    })

result_df = pd.DataFrame(data)
st.dataframe(result_df, use_container_width=True)

# ==== Telegram obaveštenja ====
def send_telegram_alert(message):
    try:
        token = st.secrets['TELEGRAM_BOT_TOKEN']
        chat_id = st.secrets['TELEGRAM_CHAT_ID']
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
        r = requests.post(url, data=payload)
        return r.status_code == 200
    except:
        return False

for row in result_df.itertuples():
    if row._10 == '✅':
        send_telegram_alert(f"🎯 *{row.Name}* ({row.Symbol.upper()}) ispunjava sve kriterijume!")
