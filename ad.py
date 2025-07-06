import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(layout="wide", page_title="Kripto Snajper – Lovac na brze mete", page_icon="🚨")

# ==== Tutorijal ====
with st.expander("Strategija korišćenja aplikacije"):
    st.markdown("""
    **Filtriramo:**
    - Market Cap < 5M
    - Cena < 0.1 USDT
    - Volume > 500.000 USDT
    - Skok > 30% (1h ili 24h)

    **Dodatni signali:**
    - Novi token (genesis date unazad 90 dana)
    - Twitter zajednica (1000+ followers)
    - GitHub aktivnost

    **Cilj:**
    - 2-3 ulaganja od 10–50€
    - Izlazak kada skokne 100–200%
    - Ne držimo duže od 1–2 dana ako ne skače

    🔍 *Meta je ako ispunjava sve gore navedene uslove.*
    """)

@st.cache_data(ttl=3600)
def get_top_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_asc',
        'per_page': 250,
        'page': 1,
        'price_change_percentage': '1h,24h'
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
            'Twitter Followers': data.get('community_data', {}).get('twitter_followers', 0),
            'GitHub Commits': data.get('developer_data', {}).get('commit_count_4_weeks', 0),
        }
    except:
        return {'Genesis Date': None, 'Twitter Followers': 0, 'GitHub Commits': 0}

with st.spinner("Učitavam podatke..."):
    df = get_top_coins()

change_col = 'price_change_percentage_24h_in_currency'

# Filtriranje
filtered = df[(df['market_cap'] < 5_000_000) &
              (df['current_price'] < 0.1) &
              (df['total_volume'] > 500_000) &
              (df[change_col] > 30)]

rows = []
for _, row in filtered.iterrows():
    fundamentals = get_fundamentals(row['id'])
    is_new = False
    if fundamentals['Genesis Date']:
        try:
            is_new = pd.to_datetime(fundamentals['Genesis Date']) > pd.Timestamp.now() - pd.Timedelta(days=90)
        except:
            pass

    meta = (
        is_new and
        fundamentals['Twitter Followers'] >= 1000 and
        fundamentals['GitHub Commits'] > 0
    )

    rows.append({
        'Name': row['name'],
        'Symbol': row['symbol'],
        'Price': f"{row['current_price']:,.4f}",
        '% Change (24h)': f"{row[change_col]:.2f}%",
        'Market Cap': f"{row['market_cap']:,.0f}",
        'Volume': f"{row['total_volume']:,.0f}",
        'Genesis Date': fundamentals['Genesis Date'] or '',
        'Twitter Followers': f"{fundamentals['Twitter Followers']:,}",
        'GitHub Commits': fundamentals['GitHub Commits'],
        '🎯 Meta?': "✅" if meta else ""
    })

if rows:
    df_display = pd.DataFrame(rows)
    st.subheader("🎯 Tokeni koji ispunjavaju uslove za mete")
    st.dataframe(df_display)
else:
    st.info("Nema tokena koji ispunjavaju sve kriterijume trenutno.")
