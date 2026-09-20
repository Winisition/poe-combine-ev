import os
from databricks import sql
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timezone, timedelta

# Read from databricks

def format_name(name: str) -> str:
    words = name.replace('-', ' ').split()
    lowercase_words = {'of', 'the', 'a', 'an'}
    return ' '.join(
        w.lower() if w.lower() in lowercase_words and i != 0 else w.capitalize()
        for i, w in enumerate(words)
    )

def to_sgt(timestamp):

    parsed = datetime.strptime(timestamp, '%Y-%m-%d_%H-%M-%S').replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone(timedelta(hours=8)))


import os
from databricks.sdk.core import Config
from databricks import sql

cfg = Config()  # auto-reads DATABRICKS_HOST / CLIENT_ID / CLIENT_SECRET

connection = sql.connect(
    server_hostname=cfg.host,
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    credentials_provider=lambda: cfg.authenticate,
)

with connection as c:
    df_scarab = pd.read_sql("SELECT * FROM workspace.poe_economy.scarab_ev", c)
    df_essence = pd.read_sql("SELECT * FROM workspace.poe_economy.essence_ev", c)

timestamp = to_sgt(df_scarab['ingested_at'].iloc[0])
current_league = df_scarab['current_league'].iloc[0]

df_scarab = (

    df_scarab
    .rename(columns={
        'id': 'Scarab',
        'total_cost': 'Cost (Chaos)',
        'profit_margin_chaos': 'Profit Margin (Chaos)'
    })
    .drop(columns=['ingested_at','current_league'])
    .assign(Scarab=lambda df: df['Scarab'].apply(format_name))

)

df_essence = (
    df_essence
    .rename(columns={
        'id': 'Essence',
        'total_cost': 'Cost (Chaos)',
        'profit_margin_chaos': 'Profit Margin (Chaos)'
    })
    .drop(columns=['ingested_at','current_league'])
    .assign(Essence=lambda df: df['Essence'].apply(format_name))
)

# Functions

def make_profit_gradient(df, column='Profit Margin (Chaos)'):
    def profit_gradient_col(series):
        styles = []
        for v in series:
            if pd.isna(v):
                styles.append('')
            elif v > 0:
                max_val = df[column].max()
                opacity = min(v / max_val, 1.0) if max_val > 0 else 0
                styles.append(f'background-color: rgba(46, 204, 113, {opacity:.2f})')
            elif v < 0:
                min_val = df[column].min()
                opacity = min(v / min_val, 1.0) if min_val < 0 else 0
                styles.append(f'background-color: rgba(231, 76, 60, {opacity:.2f})')
            else:
                styles.append('')
        return styles
    return profit_gradient_col



# Streamlit header

st.set_page_config(page_title="PoE Combine EV", layout="wide")
st_autorefresh(interval=15 * 60 * 1000, key="autorefresh")  # reruns the script, re-querying Databricks
st.title("PoE Currency Buy Signals")

# Streamlit metrics

metric_col1, metric_col2, metric_col3 = st.columns(3)

scarab_buy_signals = (df_scarab['Profit Margin (Chaos)'] > 0).sum()
essence_buy_signals = (df_essence['Profit Margin (Chaos)'] > 0).sum()
total_buy_signals = scarab_buy_signals + essence_buy_signals

with metric_col1:
    with st.container(border=True):
        st.metric("Total Buy Signals", int(total_buy_signals))

with metric_col2:
    with st.container(border=True):
        st.metric("Scarab Buy Signals", int(scarab_buy_signals))

with metric_col3:
    with st.container(border=True):
        st.metric("Essence Buy Signals", int(essence_buy_signals))

st.divider()

# Streamlit captions
caption_col1, caption_col2 = st.columns([1, 10])
with caption_col1:
    st.caption(f"League: {current_league}")
with caption_col2:
    st.caption(f"Data as of: {timestamp.strftime('%B %d, %Y at %I:%M %p')} SGT")


# Streamlit tables

col_left, col_spacer, col_right = st.columns([10, 1, 10])

with col_left:
    st.subheader("Scarab EV")
    scarab_search = st.text_input("Search scarabs:", key="scarab_search")
    df_scarab_display = df_scarab[df_scarab['Scarab'].str.contains(scarab_search, case=False, na=False)] if scarab_search else df_scarab
    if df_scarab_display.empty:
        st.info('No matching scarabs found.')
    else:
        st.dataframe(
            df_scarab_display.style.apply(
                make_profit_gradient(df_scarab_display), subset=['Profit Margin (Chaos)']
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Cost (Chaos)": st.column_config.NumberColumn(format="%.2f"),
                "Profit Margin (Chaos)": st.column_config.NumberColumn(format="%.2f"),
            }
        )

with col_right:
    st.subheader("Essence EV")
    essence_search = st.text_input("Search essences:", key="essence_search")
    df_essence_display = df_essence[df_essence['Essence'].str.contains(essence_search, case=False, na=False)] if essence_search else df_essence
    if df_essence_display.empty:
        st.info('No matching essences found.')
    else:
        st.dataframe(
            df_essence_display.style.apply(
                make_profit_gradient(df_essence_display), subset=['Profit Margin (Chaos)']
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Cost (Chaos)": st.column_config.NumberColumn(format="%.2f"),
                "Profit Margin (Chaos)": st.column_config.NumberColumn(format="%.2f"),
            }
        )