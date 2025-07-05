import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime
import time

st.set_page_config(layout="wide")
st.title("🚀 Kripto Skok Detektor – Lovac na Brze Mete")

# ==== Tutorijal za korisnika ====
with st.expander("📘 Kako tumačiti podatke i grafikone"):
    st.markdown("""
**🎯 Cilj aplikacije**: Pratimo kriptovalute koje imaju nagli rast u zadnjih 1h, 24h ili 7 dana.

**📊 Kolone:**
- **Price**: Trenutna cena tokena.
- **% Change**: Promena cene u odabranom periodu (1h, 24h, 7d).
- **Volume**: Koliko je trgovano u USDT u zadnja 24h (veći volumen = ozbiljniji projekti).
- **Market Cap**: Ukupna vrednost tokena (veći cap = stabilniji projekti).
- **Country**: Država porekla (ako je dostupna).
- **Launch Date**: Datum izlaska tokena.
- **Spike Time**: Detektovan trenutak naglog skoka cene.
- **RSI / MACD**: Tehnički indikatori za jačinu trenda.
- **BB Low**: Donja granica Bollinger opsega (da li je cena blizu minimuma?).

**🟢 Kada je signal zanimljiv?**
- Veliki % skoka (npr. >30%) uz dobar volumen može značiti da se projekat "budi".
- Male market cap kriptovalute + visok rast = rizične ali mogu biti eksplozivne.
- Ako je cena tokena < 0.1 USDT i skokne 100% → moguće da ide dalje, ali rizik je velik.

👉 Preporuka: Prati i dalje trendove, ne kupuj odmah — ovo je alat za otkrivanje, ne savet za investiranje.
""")

# ==== Parametri ====
st.sidebar.header("⚙️ Filteri")
vs_currency = st.sidebar.selectbox("Valuta prikaza", options=['usd', 'eur'], index=0)
time_period = st.sidebar.selectbox("Vremenski period", ['1h', '24h', '7d'], index=1)
min_market_cap = st.sidebar.number_input("Minimalni Market Cap (miliona $)", value=10)
min_volume = st.sidebar.number_input("Minimalni volumen (miliona $)", value=1)
skok_threshold = st.sidebar.slider("Minimalni procenat rasta za upozorenje", min_value=10, max_value=500, value=50)
refresh_interval = st.sidebar.slider("🔁 Auto-refresh (sekundi)", 30, 600, 300, step=30)

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

def get_coin_details(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        rsi = data.get("market_data", {}).get("rsi", {}).get("14", None)
        macd = data.get("market_data", {}).get("macd", {}).get("macd", None)
        bb_low = data.get("market_data", {}).get("bollinger_bands_20", {}).get("lower", None)
        twitter_followers = data.get("community_data", {}).get("twitter_followers", None)
        github = data.get("developer_data", {}).get("github_contributors", None)
        return {
            'country': data.get('country_origin') or 'N/A',
            'launch_date': data.get('genesis_date') or 'N/A',
            'twitter': twitter_followers,
            'github': github,
            'rsi': rsi,
            'macd': macd,
            'bb_low': bb_low
        }
    return {'country': 'N/A', 'launch_date': 'N/A', 'twitter': None, 'github': None, 'rsi': None, 'macd': None, 'bb_low': None}

# ==== Auto refresh ====
st_autorefresh = st.empty()
count = st_autorefresh.experimental_rerun() if st_autorefresh.button("🔄 Osveži odmah") else time.sleep(refresh_interval)

with st.spinner("🔄 Učitavam podatke sa CoinGecko API-ja..."):
    df = get_top_coins()

change_column = {
    '1h': 'price_change_percentage_1h_in_currency',
    '24h': 'price_change_percentage_24h_in_currency',
    '7d': 'price_change_percentage_7d_in_currency',
}[time_period]

# ==== Filtriranje ====
df = df[df['market_cap'] >= min_market_cap * 1e6]
df = df[df['total_volume'] >= min_volume * 1e6]
df = df.dropna(subset=[change_column])
df = df.sort_values(change_column, ascending=False)

# ==== Obogaćivanje ====
coin_details = []
for _, row in df.iterrows():
    details = get_coin_details(row['id'])
    coin_details.append(details)

df['Country'] = [d['country'] for d in coin_details]
df['Launch Date'] = [d['launch_date'] for d in coin_details]
df['Twitter'] = [d['twitter'] for d in coin_details]
df['GitHub'] = [d['github'] for d in coin_details]
df['RSI'] = [d['rsi'] for d in coin_details]
df['MACD'] = [d['macd'] for d in coin_details]
df['BB_Low'] = [d['bb_low'] for d in coin_details]

skok_std = df[change_column].std()
skok_mean = df[change_column].mean()
df['Spike Detected'] = df[change_column] > (skok_mean + 2 * skok_std)
df['Spike Time'] = datetime.now().strftime('%Y-%m-%d %H:%M')
df['Spike Time'] = df.apply(lambda row: row['Spike Time'] if row['Spike Detected'] else '', axis=1)

# ==== Vizualizacija ====
st.subheader(f"📈 Top rastuće kriptovalute ({time_period} change)")
fig = px.bar(df.head(20), x='name', y=change_column, text=change_column,
             title=f"Top 20 skokova u {time_period}", color=change_column,
             color_continuous_scale='Viridis')
fig.update_layout(xaxis_tickangle=-45, height=500)
st.plotly_chart(fig, use_container_width=True)

# ==== Tabela ====
st.subheader("🔎 Detaljna tabela")
df_display = df[['name', 'symbol', 'current_price', change_column, 'market_cap', 'total_volume',
                 'Country', 'Launch Date', 'RSI', 'MACD', 'BB_Low', 'Twitter', 'GitHub', 'Spike Time']]
df_display.columns = ['Name', 'Symbol', 'Price', f'% Change ({time_period})', 'Market Cap', 'Volume',
                      'Country', 'Launch Date', 'RSI', 'MACD', 'BB Low', 'Twitter', 'GitHub', 'Spike Time']
st.dataframe(df_display.head(50), use_container_width=True)

# ==== Upozorenja ====
alerts = df[df[change_column] >= skok_threshold]
if not alerts.empty:
    st.warning(f"🚨 Pronađeno {len(alerts)} kriptovaluta sa skokom većim od {skok_threshold}%!")
    st.table(alerts[['name', 'symbol', 'current_price', change_column]].rename(columns={
        'name': 'Naziv', 'symbol': 'Simbol', 'current_price': 'Cena', change_column: '% Skok'
    }))
else:
    st.info("📭 Nema kriptovaluta koje zadovoljavaju kriterijum za upozorenje.")
