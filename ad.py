import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime
import ta
import time

# ==== Lozinka ====
PASSWORD = st.secrets["pass"]

if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    pwd = st.text_input("🔒 Unesi lozinku za pristup aplikaciji:", type="password")
    if pwd:
        if pwd == PASSWORD:
            st.session_state["password_correct"] = True
        else:
            st.error("❌ Pogrešna lozinka, pokušaj ponovo.")
    st.stop()

st.set_page_config(layout="wide", page_title="Kripto Snajper – Lovac na brze mete", page_icon="🚨")
st.title("💥 Kripto Snajper – Lovac na brze mete")
st.markdown("""
<style>
.big-title {
    font-size: 36px;
    font-weight: bold;
    color: #ff4b4b;
}
.metric-card {
    border-radius: 15px;
    background-color: #f0f2f6;
    padding: 15px;
    box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
}
.green-cell {
    color: #008000;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ==== Auto Refresh i osveženje ====
if st.button("🔄 Ručno osveži podatke"):
    st.rerun()

# ==== Telegram funkcija ====
def send_telegram_alert(message):
    try:
        token = st.secrets["TELEGRAM_BOT_TOKEN"]
        chat_id = st.secrets["TELEGRAM_CHAT_ID"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        response = requests.post(url, data=payload)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Telegram greška: {e}")
        return False

# ==== Parametri ====
st.sidebar.header("⚙️ Filteri")
vs_currency = st.sidebar.selectbox("Valuta prikaza", options=['usd', 'eur'], index=0)
time_period = st.sidebar.selectbox("Vremenski period", ['1h', '24h', '7d'], index=1)
min_market_cap = st.sidebar.number_input("Minimalni Market Cap (miliona $)", value=10)
min_volume = st.sidebar.number_input("Minimalni volumen (miliona $)", value=1)
skok_threshold = st.sidebar.slider("Minimalni procenat rasta za upozorenje", min_value=10, max_value=500, value=50)

# ==== Dohvatanje podataka ====
@st.cache_data(ttl=3600)
def get_top_coins():
    url = f"https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': vs_currency,
        'order': 'market_cap_desc',
        'per_page': 250,
        'page': 1,
        'price_change_percentage': '1h,24h,7d'
    }
    response = requests.get(url, params=params)
    return pd.DataFrame(response.json())

@st.cache_data(ttl=3600)
def get_new_tokens():
    url = "https://api.coingecko.com/api/v3/coins/list?include_platform=false"
    coins_list = requests.get(url).json()
    new_tokens = coins_list[-50:]
    return new_tokens

@st.cache_data(ttl=3600)
def get_fundamentals(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        data = requests.get(url).json()
        return {
            'id': data.get('id'),
            'Genesis Date': data.get('genesis_date'),
            'Twitter Followers': data.get('community_data', {}).get('twitter_followers'),
            'GitHub Commits (4w)': data.get('developer_data', {}).get('commit_count_4_weeks')
        }
    except:
        return {'id': coin_id}

with st.spinner("🔄 Učitavam podatke sa CoinGecko API-ja..."):
    df = get_top_coins()
    fundamentals = {item['id']: item for item in [get_fundamentals(coin['id']) for coin in df.to_dict('records')]}

change_column = {
    '1h': 'price_change_percentage_1h_in_currency',
    '24h': 'price_change_percentage_24h_in_currency',
    '7d': 'price_change_percentage_7d_in_currency',
}[time_period]

# Filtriranje
filtered_df = df[(df['market_cap'] >= min_market_cap * 1e6) & (df['total_volume'] >= min_volume * 1e6)]
filtered_df = filtered_df.dropna(subset=[change_column])
filtered_df = filtered_df.sort_values(change_column, ascending=False).head(50)

# Priprema prikaza
rows = []
for _, row in filtered_df.iterrows():
    coin_id = row['id']
    extra = fundamentals.get(coin_id, {})
    market_cap = row['market_cap']
    volume = row['total_volume']
    change = row[change_column]

    def format_conditional(value, condition):
        return f'<span class="green-cell">{value}</span>' if condition else f"{value}"

    rows.append({
        "Name": row['name'],
        "Symbol": row['symbol'],
        "Price": f"{row['current_price']:,.4f}",
        f"% Change ({time_period})": format_conditional(f"{change:.2f}%", change > 30),
        "Market Cap": format_conditional(f"{market_cap:,.0f}", market_cap < 5_000_000),
        "Volume": format_conditional(f"{volume:,.0f}", volume > 500_000),
        "Genesis Date": extra.get("Genesis Date", ""),
        "Twitter Followers": f"{extra.get('Twitter Followers', ''):,}" if extra.get('Twitter Followers') else "",
        "GitHub Commits (4w)": f"{extra.get('GitHub Commits (4w)', ''):,}" if extra.get('GitHub Commits (4w)') else "",
        "CMC": f'<a href="https://coinmarketcap.com/currencies/{coin_id}/" target="_blank"><button>CMC</button></a>'
    })

df_display = pd.DataFrame(rows)

st.markdown(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)
