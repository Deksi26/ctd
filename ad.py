import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime
import ta
import time
from binance.client import Client

st.set_page_config(layout="wide")
st.title("🚀 Kripto Skok Detektor + Binance RSI/MACD")

# ==== Auto Refresh ====
st_autorefresh = st.experimental_rerun if st.button("🔄 Ručno osveži") else None

# ==== Telegram funkcija ====
def send_telegram_alert(message):
    try:
        token = st.secrets["telegram_token"]
        chat_id = st.secrets["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        response = requests.post(url, data=payload)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Telegram greška: {e}")
        return False

# ==== Tutorijal za korisnika ====
with st.expander("📘 Kako tumačiti podatke i grafikone"):
    st.markdown("""
**🌟 Cilj aplikacije**: Pratimo kriptovalute koje imaju nagli rast i dodajemo tehničku analizu iz Binance-a (RSI, MACD, BB).

**📊 Kolone:**
- **Price**: Trenutna cena tokena.
- **% Change**: Promena cene u odabranom periodu (1h, 24h, 7d).
- **Volume**: Koliko je trgovano u USDT u zadnja 24h.
- **Market Cap**: Ukupna vrednost tokena.
- **Country**: Država porekla (ako je dostupna).
- **Launch Date**: Datum izlaska tokena.
- **Spike Time**: Detektovan trenutak naglog skoka cene.
- **RSI / MACD / BB**: Indikatori iz tehničke analize (ako je simbol pronađen na Binance).
""")

# ==== Parametri ====
st.sidebar.header("⚙️ Filteri")
vs_currency = st.sidebar.selectbox("Valuta prikaza", options=['usd', 'eur'], index=0)
time_period = st.sidebar.selectbox("Vremenski period", ['1h', '24h', '7d'], index=1)
min_market_cap = st.sidebar.number_input("Minimalni Market Cap (miliona $)", value=10)
min_volume = st.sidebar.number_input("Minimalni volumen (miliona $)", value=1)
skok_threshold = st.sidebar.slider("Minimalni procenat rasta za upozorenje", min_value=10, max_value=500, value=50)
refresh_interval = st.sidebar.selectbox("Auto Refresh (minuti)", [0, 1, 5, 10, 30], index=2)

if refresh_interval:
    st.experimental_set_query_params(_=str(datetime.now().timestamp()))
    st_autorefresh = st.experimental_rerun if time.time() % (refresh_interval * 60) < 2 else None

# ==== Dohvatanje podataka ====
@st.cache_data(ttl=600)
def get_top_coins():
    url = f"https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': vs_currency,
        'order': 'market_cap_desc',
        'per_page': 100,
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
        return {
            'country': data.get('country_origin') or 'N/A',
            'launch_date': data.get('genesis_date') or 'N/A'
        }
    return {'country': 'N/A', 'launch_date': 'N/A'}

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

client = Client(st.secrets["binance_api"], st.secrets["binance_secret"])

def get_binance_indicators(symbol):
    try:
        binance_symbol = symbol.upper() + 'USDT'
        klines = client.get_klines(symbol=binance_symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=100)
        df_kl = pd.DataFrame(klines, columns=['time','open','high','low','close','volume','x','x','x','x','x','x'])
        df_kl['close'] = pd.to_numeric(df_kl['close'])
        close = df_kl['close']
        rsi = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]
        macd = ta.trend.MACD(close)
        macd_line = macd.macd().iloc[-1]
        signal_line = macd.macd_signal().iloc[-1]
        bb = ta.volatility.BollingerBands(close, window=20)
        bb_low = bb.bollinger_lband().iloc[-1]
        return round(rsi, 2), round(macd_line, 4), round(signal_line, 4), round(bb_low, 4)
    except:
        return '', '', '', ''

rsi_list, macd_list, signal_list, bb_low_list, countries, launches = [], [], [], [], [], []
for _, row in df.iterrows():
    d = get_coin_details(row['id'])
    rsi, macd, signal, bb_low = get_binance_indicators(row['symbol'])
    countries.append(d['country'])
    launches.append(d['launch_date'])
    rsi_list.append(rsi)
    macd_list.append(macd)
    signal_list.append(signal)
    bb_low_list.append(bb_low)

df['Country'] = countries
df['Launch Date'] = launches
df['RSI'] = rsi_list
df['MACD'] = macd_list
df['MACD_Signal'] = signal_list
df['BB_Low'] = bb_low_list

# ==== Detekcija skokova ====
skok_std = df[change_column].std()
skok_mean = df[change_column].mean()
df['Spike Detected'] = df[change_column] > (skok_mean + 2 * skok_std)
df['Spike Time'] = datetime.now().strftime('%Y-%m-%d %H:%M')
df['Spike Time'] = df.apply(lambda row: row['Spike Time'] if row['Spike Detected'] else '', axis=1)

# ==== Vizualni prikaz ====
st.subheader(f"📈 Top rastuće kriptovalute ({time_period} change)")
fig = px.bar(df.head(20), x='name', y=change_column, text=change_column,
             title=f"Top 20 skokova u {time_period}", color=change_column,
             color_continuous_scale='Viridis')
fig.update_layout(xaxis_tickangle=-45, height=500)
st.plotly_chart(fig, use_container_width=True)

# ==== Tabela + upozorenja ====
st.subheader("🔎 Detaljna tabela")
df_display = df[['name', 'symbol', 'current_price', change_column, 'market_cap', 'total_volume', 'Country', 'Launch Date', 'RSI', 'MACD', 'MACD_Signal', 'BB_Low', 'Spike Time']]
df_display.columns = ['Name', 'Symbol', 'Price', f'% Change ({time_period})', 'Market Cap', 'Volume', 'Country', 'Launch Date', 'RSI', 'MACD', 'MACD Signal', 'BB Low', 'Spike Time']
st.dataframe(df_display.head(50), use_container_width=True)

# ==== Upozorenja ====
alerts = df[df[change_column] >= skok_threshold]
if not alerts.empty:
    st.warning(f"🚨 Pronađeno {len(alerts)} kriptovaluta sa skokom većim od {skok_threshold}%!")
    for _, row in alerts.iterrows():
        msg = f"""
🚀 *Novi skok detektovan!*
Symbol: `{row['symbol'].upper()}`
Cena: ${row['current_price']}
% Promena: {row[change_column]}%
RSI: {row['RSI']} | MACD: {row['MACD']}
BB Low: {row['BB_Low']}
"""
        send_telegram_alert(msg)
    st.table(alerts[['name', 'symbol', 'current_price', change_column]].rename(columns={
        'name': 'Naziv', 'symbol': 'Simbol', 'current_price': 'Cena', change_column: '% Skok'
    }))
else:
    st.info("📬 Nema kriptovaluta koje zadovoljavaju kriterijum za upozorenje.")
