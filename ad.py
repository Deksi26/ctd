import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime
import ta
import time

PASSWORD = st.secrets["pass"]

if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    pwd = st.text_input("🔒 Unesi lozinku za pristup aplikaciji:", type="password")
    if pwd:
        if pwd == PASSWORD:
            st.session_state["password_correct"] = True
            # Rerun app nakon uspešnog unosa lozinke
            st.experimental_rerun()
        else:
            st.error("❌ Pogrešna lozinka, pokušaj ponovo.")
    # Ovde zaustavljamo dalje izvršavanje dok korisnik ne unese ispravnu lozinku
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

# ==== Tutorijal ====
with st.expander("📘 Kako tumačiti podatke i grafikone"):
    st.markdown("""
**🌟 Cilj aplikacije**: Pratimo kriptovalute koje imaju nagli rast u zadnjih 1h, 24h ili 7 dana.

**📊 Kolone:**
- **Price**: Trenutna cena tokena.
- **% Change**: Promena cene u odabranom periodu.
- **Volume**: Trgovanje u USDT u zadnja 24h.
- **Market Cap**: Ukupna vrednost tokena.

**🟢 Kada je signal zanimljiv?**
- Veliki % skoka (npr. >30%) uz dobar volumen može značiti da se projekat "budi".
- Male market cap kriptovalute + visok rast = rizične ali mogu biti eksplozivne.
- Ako je cena tokena < 0.1 USDT i skokne 100% → moguće da ide dalje, ali rizik je velik.

🔪 *Eksplozivne mete (low cap + < 0.1$ + veliki skok)* su najrizičnije, ali i najprofitabilnije ako se pogode pravovremeno.
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

with st.spinner("🔄 Učitavam podatke sa CoinGecko API-ja..."):
    df = get_top_coins()

change_column = {
    '1h': 'price_change_percentage_1h_in_currency',
    '24h': 'price_change_percentage_24h_in_currency',
    '7d': 'price_change_percentage_7d_in_currency',
}[time_period]

df = df[df['market_cap'] >= min_market_cap * 1e6]
df = df[df['total_volume'] >= min_volume * 1e6]
df = df.dropna(subset=[change_column])
df = df.sort_values(change_column, ascending=False)

st.subheader(f"📈 Top 20 skokova ({time_period})")
fig = px.bar(df.head(20), x='name', y=change_column, text=change_column,
             title=f"Top 20 kripto skokova u {time_period}", color=change_column,
             color_continuous_scale='reds')
fig.update_layout(xaxis_tickangle=-45, height=500)
st.plotly_chart(fig, use_container_width=True)

st.subheader("🔎 Detaljna tabela (Top 50)")
df_display = df[['name', 'symbol', 'current_price', change_column, 'market_cap', 'total_volume']].copy()
df_display.columns = ['Name', 'Symbol', 'Price', f'% Change ({time_period})', 'Market Cap', 'Volume']

pd.options.display.float_format = '{:,.2f}'.format
for col in ['Price', f'% Change ({time_period})']:
    df_display[col] = df_display[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
for col in ['Market Cap', 'Volume']:
    df_display[col] = df_display[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")

df_display['CoinMarketCap'] = df['id'].apply(lambda x: f'<a href="https://coinmarketcap.com/currencies/{x}/" target="_blank"><button>CMC</button></a>')

st.write("""
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

alerts = df[df[change_column] >= skok_threshold]
if not alerts.empty:
    st.warning(f"🚨 Pronađeno {len(alerts)} kriptovaluta sa skokom većim od {skok_threshold}%!")
    alert_display = alerts[['name', 'symbol', 'current_price', change_column]].rename(columns={
        'name': 'Naziv', 'symbol': 'Simbol', 'current_price': 'Cena', change_column: '% Skok'
    })
    alert_display['Cena'] = alert_display['Cena'].apply(lambda x: f"{x:,.4f}")
    alert_display['% Skok'] = alert_display['% Skok'].apply(lambda x: f"{x:.2f}%")
    st.table(alert_display)
    for i, row in alerts.iterrows():
        send_telegram_alert(f"🚀 *{row['name']}* ({row['symbol'].upper()}) skočio {row[change_column]:.2f}%!")
else:
    st.info("📬 Nema kriptovaluta koje zadovoljavaju kriterijum za upozorenje.")

# ==== Eksplozivne mete ====
st.subheader("🔥 Niskobudžetne eksplozivne mete")
explosives = df[(df['market_cap'] <= 5_000_000) & (df['current_price'] < 0.1) & (df[change_column] > skok_threshold)]
if not explosives.empty:
    st.success(f"📊 Pronađeno {len(explosives)} eksplozivnih mete!")
    df_explosive = explosives[['name', 'symbol', 'current_price', change_column, 'market_cap', 'total_volume']].copy()
    df_explosive.columns = ['Name', 'Symbol', 'Price', f'% Change ({time_period})', 'Market Cap', 'Volume']
    for col in ['Price', f'% Change ({time_period})']:
        df_explosive[col] = df_explosive[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
    for col in ['Market Cap', 'Volume']:
        df_explosive[col] = df_explosive[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
    st.dataframe(df_explosive)
else:
    st.info("🚬 Nema eksplozivnih mete trenutno.")

# ==== Novi tokeni ====
st.subheader("🆕 Novi tokeni + Fundamentalne informacije")
new_tokens = get_new_tokens()
fundamental_data = [get_fundamentals(token['id']) for token in new_tokens[:20]]
fundamental_df = pd.DataFrame(fundamental_data)

if 'Twitter Followers' in fundamental_df:
    fundamental_df['Twitter Followers'] = fundamental_df['Twitter Followers'].apply(lambda x: f"{x:,}" if pd.notnull(x) else "")
if 'GitHub Commits (4w)' in fundamental_df:
    fundamental_df['GitHub Commits (4w)'] = fundamental_df['GitHub Commits (4w)'].apply(lambda x: f"{x:,}" if pd.notnull(x) else "")

st.dataframe(fundamental_df)
