import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime
import ta
import time

st.set_page_config(layout="wide")
st.title("🚀 Kripto Skok Detektor (CoinGecko verzija)")

# ==== Auto Refresh i osveženje ====
if st.button("🔄 Ručno osveži"):
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

# ==== Tutorijal ====
with st.expander("📘 Kako tumačiti podatke i grafikone"):
    st.markdown("""
**🎯 Cilj aplikacije**: Pratimo kriptovalute koje imaju nagli rast u zadnjih 1h, 24h ili 7 dana.

**📊 Kolone:**
- **Price**: Trenutna cena tokena.
- **% Change**: Promena cene u odabranom periodu.
- **Volume**: Trgovanje u USDT u zadnja 24h.
- **Market Cap**: Ukupna vrednost tokena.

**🟢 Kada je signal zanimljiv?**
- Veliki % skoka (npr. >30%) uz dobar volumen može značiti da se projekat "budi".
- Male market cap kriptovalute + visok rast = rizične ali mogu biti eksplozivne.
- Ako je cena tokena < 0.1 USDT i skokne 100% → moguće da ide dalje, ali rizik je velik.

👉 Preporuka: Prati trendove, ne kupuj odmah — ovo je alat za otkrivanje, ne savet za ulaganje.
""")

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

with st.spinner("🔄 Učitavam podatke sa CoinGecko API-ja..."):
    df = get_top_coins()

# ==== Priprema kolone po periodu ====
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

# ==== Vizualni prikaz ====
st.subheader(f"📈 Top rastuće kriptovalute ({time_period} change)")
fig = px.bar(df.head(20), x='name', y=change_column, text=change_column,
             title=f"Top 20 skokova u {time_period}", color=change_column,
             color_continuous_scale='Viridis')
fig.update_layout(xaxis_tickangle=-45, height=500)
st.plotly_chart(fig, use_container_width=True)

# ==== Tabela + upozorenja ====
st.subheader("🔎 Detaljna tabela")
df_display = df[['name', 'symbol', 'current_price', change_column, 'market_cap', 'total_volume']]
df_display.columns = ['Name', 'Symbol', 'Price', f'% Change ({time_period})', 'Market Cap', 'Volume']
st.dataframe(df_display.head(50), use_container_width=True)

# ==== Upozorenja ====
alerts = df[df[change_column] >= skok_threshold]
if not alerts.empty:
    st.warning(f"🚨 Pronađeno {len(alerts)} kriptovaluta sa skokom većim od {skok_threshold}%!")
    st.table(alerts[['name', 'symbol', 'current_price', change_column]].rename(columns={
        'name': 'Naziv', 'symbol': 'Simbol', 'current_price': 'Cena', change_column: '% Skok'
    }))
    for i, row in alerts.iterrows():
        send_telegram_alert(f"🚀 *{row['name']}* ({row['symbol'].upper()}) skočio {row[change_column]:.2f}%!")
else:
    st.info("📭 Nema kriptovaluta koje zadovoljavaju kriterijum za upozorenje.")
