import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime
import ta
import time

# === Podešavanje stranica ===
st.set_page_config(layout="wide", page_title="Kripto Snajper – Lovac na brze mete", page_icon="🚨")

page = st.sidebar.selectbox("📂 Izaberi stranicu", ["Top Skokovi", "Eksplozivne Mete", "Stabilni Skokovi"])

# ==== Funkcije za podatke ====
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
            'Name': data.get('name'),
            'Symbol': data.get('symbol').upper(),
            'Genesis Date': data.get('genesis_date'),
            'Country': data.get('country_origin'),
            'Twitter Followers': data.get('community_data', {}).get('twitter_followers'),
            'GitHub Commits (4w)': data.get('developer_data', {}).get('commit_count_4_weeks'),
            'CoinMarketCap': f"[🔗 CoinMarketCap](https://coinmarketcap.com/currencies/{data.get('id', '')}/)"
        }
    except:
        return {}

# ==== Parametri ====
st.sidebar.header("⚙️ Filteri")
vs_currency = st.sidebar.selectbox("Valuta prikaza", options=['usd', 'eur'], index=0)
time_period = st.sidebar.selectbox("Vremenski period", ['1h', '24h', '7d'], index=0)
min_market_cap = st.sidebar.number_input("Minimalni Market Cap (miliona $)", value=3)
min_volume = st.sidebar.number_input("Minimalni volumen (miliona $)", value=1)
skok_threshold = st.sidebar.slider("Minimalni procenat rasta za upozorenje", min_value=10, max_value=500, value=34)

change_column = {
    '1h': 'price_change_percentage_1h_in_currency',
    '24h': 'price_change_percentage_24h_in_currency',
    '7d': 'price_change_percentage_7d_in_currency',
}[time_period]

# === GLAVNI SADRŽAJ ===
if page == "Top Skokovi":
    st.title("📈 Top 20 Skokova")
    df = get_top_coins()
    df = df[df['market_cap'] >= min_market_cap * 1e6]
    df = df[df['total_volume'] >= min_volume * 1e6]
    df = df.dropna(subset=[change_column])
    df = df.sort_values(change_column, ascending=False)

    fig = px.bar(df.head(20), x='name', y=change_column, text=change_column,
                 title=f"Top 20 kripto skokova u {time_period}", color=change_column,
                 color_continuous_scale='reds')
    fig.update_layout(xaxis_tickangle=-45, height=500)
    st.plotly_chart(fig, use_container_width=True)

    df_display = df[['name', 'symbol', 'current_price', change_column, 'market_cap', 'total_volume']].copy()
    df_display.columns = ['Name', 'Symbol', 'Price', f'% Change ({time_period})', 'Market Cap', 'Volume']
    df_display['CoinMarketCap'] = df['id'].apply(lambda x: f'<a href="https://coinmarketcap.com/currencies/{x}/" target="_blank"><button>CMC</button></a>')

    st.markdown("""
    <style>
    button {
      background-color: #4CAF50;
      border: none;
      color: white;
      padding: 4px 10px;
      text-align: center;
      text-decoration: none;
      display: inline-block;
      font-size: 12px;
      margin: 2px 1px;
      cursor: pointer;
      border-radius: 6px;
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown(df_display.head(50).to_html(escape=False, index=False), unsafe_allow_html=True)

elif page == "Eksplozivne Mete":
    st.title("🔥 Niskobudžetne eksplozivne mete")
    df = get_top_coins()
    df = df[(df['market_cap'] <= 5_000_000) & (df['current_price'] < 0.1) & (df[change_column] > skok_threshold)]
    if not df.empty:
        df_display = df[['name', 'symbol', 'current_price', change_column, 'market_cap', 'total_volume']].copy()
        df_display.columns = ['Name', 'Symbol', 'Price', f'% Change ({time_period})', 'Market Cap', 'Volume']
        for col in ['Price', f'% Change ({time_period})']:
            df_display[col] = df_display[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
        for col in ['Market Cap', 'Volume']:
            df_display[col] = df_display[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
        st.dataframe(df_display)
    else:
        st.info("🚬 Nema eksplozivnih mete trenutno.")

elif page == "Stabilni Skokovi":
    st.title("🟢 Stabilni i postepeni skokovi")
    df = get_top_coins()
    df = df[(df['market_cap'] >= 50_000_000) & (df['total_volume'] > 5_000_000) & (df[change_column] > 5) & (df[change_column] < skok_threshold)]
    if not df.empty:
        df_display = df[['name', 'symbol', 'current_price', change_column, 'market_cap', 'total_volume']].copy()
        df_display.columns = ['Name', 'Symbol', 'Price', f'% Change ({time_period})', 'Market Cap', 'Volume']
        for col in ['Price', f'% Change ({time_period})']:
            df_display[col] = df_display[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
        for col in ['Market Cap', 'Volume']:
            df_display[col] = df_display[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
        st.dataframe(df_display)
    else:
        st.info("📉 Nema stabilnih skokova trenutno.")
