import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime

# ==== Lozinka ====
PASSWORD = st.secrets["pass"]

if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    pwd = st.text_input("\U0001f512 Unesi lozinku za pristup aplikaciji:", type="password")
    if pwd:
        if pwd == PASSWORD:
            st.session_state["password_correct"] = True
        else:
            st.error("\u274c Pogrešna lozinka, pokušaj ponovo.")
    st.stop()

st.set_page_config(layout="wide", page_title="Kripto Snajper – Lovac na brze mete", page_icon="\U0001f6a8")
st.title("\U0001f4a5 Kripto Snajper – Lovac na brze mete")

# ==== Osveženje ====
if st.button("\U0001f504 Ručno osveži podatke"):
    st.rerun()

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
def get_fundamentals(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        data = requests.get(url).json()
        return {
            'Genesis Date': data.get('genesis_date'),
            'Twitter Followers': data.get('community_data', {}).get('twitter_followers'),
            'GitHub Commits (4w)': data.get('developer_data', {}).get('commit_count_4_weeks')
        }
    except:
        return {}

# ==== Parametri ====
st.sidebar.header("⚙️ Filteri")
vs_currency = st.sidebar.selectbox("Valuta prikaza", options=['usd', 'eur'], index=0)
time_period = st.sidebar.selectbox("Vremenski period", ['1h', '24h', '7d'], index=1)
min_market_cap = st.sidebar.number_input("Minimalni Market Cap (miliona $)", value=10)
min_volume = st.sidebar.number_input("Minimalni volumen (miliona $)", value=1)
skok_threshold = st.sidebar.slider("Minimalni procenat rasta za upozorenje", min_value=10, max_value=500, value=50)

# ==== Glavni podaci ====
with st.spinner("\U0001f504 Učitavam podatke sa CoinGecko API-ja..."):
    df = get_top_coins()
    change_column = {
        '1h': 'price_change_percentage_1h_in_currency',
        '24h': 'price_change_percentage_24h_in_currency',
        '7d': 'price_change_percentage_7d_in_currency',
    }[time_period]
    df = df[(df['market_cap'] >= min_market_cap * 1e6) & (df['total_volume'] >= min_volume * 1e6)]
    df = df.dropna(subset=[change_column])
    df = df.sort_values(change_column, ascending=False).head(50)

    # ==== Grafikon ====
    st.subheader(f"\U0001f4c8 Top 20 skokova ({time_period})")
    fig = px.bar(df.head(20), x='name', y=change_column, text=change_column,
                 title=f"Top 20 kripto skokova u {time_period}", color=change_column,
                 color_continuous_scale='reds')
    fig.update_layout(xaxis_tickangle=-45, height=500)
    st.plotly_chart(fig, use_container_width=True)

    # ==== Tabela sa dodatnim kolonama ====
    rows = []
    for _, row in df.iterrows():
        coin_id = row['id']
        fundamentals = get_fundamentals(coin_id)
        rows.append({
            "Name": row['name'],
            "Symbol": row['symbol'],
            "Price": f"{row['current_price']:,.4f}",
            f"% Change ({time_period})": f"{row[change_column]:.2f}%",
            "Market Cap": f"{row['market_cap']:,.0f}",
            "Volume": f"{row['total_volume']:,.0f}",
            "Genesis Date": fundamentals.get("Genesis Date", ""),
            "Twitter Followers": f"{fundamentals.get('Twitter Followers', 0):,}" if fundamentals.get('Twitter Followers') else "",
            "GitHub Commits (4w)": f"{fundamentals.get('GitHub Commits (4w)', 0):,}" if fundamentals.get('GitHub Commits (4w)') else "",
            "CMC": f'<a href="https://coinmarketcap.com/currencies/{coin_id}/" target="_blank"><button>CMC</button></a>'
        })

    df_display = pd.DataFrame(rows)
    st.markdown(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

    # ==== Eksplozivne mete ====
    st.subheader("\U0001f525 Niskobudžetne eksplozivne mete")
    explosives = df[(df['market_cap'] <= 5_000_000) & (df['current_price'] < 0.1) & (df[change_column] > skok_threshold)]
    if not explosives.empty:
        df_explosive = explosives[['name', 'symbol', 'current_price', change_column, 'market_cap', 'total_volume']].copy()
        df_explosive.columns = ['Name', 'Symbol', 'Price', f'% Change ({time_period})', 'Market Cap', 'Volume']
        for col in ['Price', f'% Change ({time_period})']:
            df_explosive[col] = df_explosive[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
        for col in ['Market Cap', 'Volume']:
            df_explosive[col] = df_explosive[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
        st.dataframe(df_explosive)
    else:
        st.info("\U0001f6ac Nema eksplozivnih mete trenutno.")
