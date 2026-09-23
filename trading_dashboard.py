import streamlit as st
import akshare as ak
import pandas as pd
from supabase import create_client, Client

# -------------------------- 页面基础配置 --------------------------
st.set_page_config(page_title="股票交易复盘看板", layout="wide")
st.title("📈 个人股票交易台账 & 盘中监控系统")

# -------------------------- Supabase 连接配置 --------------------------
@st.cache_resource
def init_supabase():
    url = st.secrets["supabase_url"]
    key = st.secrets["supabase_key"]
    return create_client(url, key)

supabase: Client = init_supabase()

# -------------------------- 读取交易台账 --------------------------
@st.cache_data(ttl=60)
def load_trade_data():
    res = supabase.table("trade_records").select("*").order("trade_date", desc=True).execute()
    return pd.DataFrame(res.data)

df_trade = load_trade_data()

# -------------------------- 侧边栏菜单 --------------------------
menu = st.sidebar.selectbox("功能菜单", ["交易台账总表", "新增交易记录", "个股实时行情", "复盘分析"])

# ====================== 1. 交易台账总表 ======================
if menu == "交易台账总表":
    st.subheader("📋 交易汇总台账")
    if not df_trade.empty:
        st.dataframe(df_trade, use_container_width=True)
        total_buy = df_trade["buy_amount"].sum()
        total_pnl = df_trade["single_pnl"].sum()
        st.metric("总投入金额", f"{total_buy:.2f}")
        st.metric("合计盈亏", f"{total_pnl:.2f}", delta=f"{total_pnl/total_buy*100:.2f}%")
    else:
        st.info("暂无交易记录，请前往【新增交易记录】录入")

# ====================== 2. 新增交易记录 ======================
elif menu == "新增交易记录":
    st.subheader("✍️ 录入新交易")
    with st.form("trade_form"):
        trade_date = st.date_input("交易日期")
        stock_code = st.text_input("股票代码（如600000）")
        stock_name = st.text_input("股票名称")
        buy_price = st.number_input("买入价", min_value=0.00, step=0.01)
        buy_position = st.number_input("买入仓位", min_value=0.0, step=0.01)
        buy_amount = st.number_input("买入金额", min_value=0.0, step=1.0)
        stop_loss = st.number_input("止损点位", min_value=0.0, step=0.01)
        take_profit = st.number_input("止盈点位", min_value=0.0, step=0.01)
        submit = st.form_submit_button("保存记录")
        if submit:
            insert_data = {
                "trade_date": trade_date.isoformat(),
                "stock_code": stock_code,
                "stock_name": stock_name,
                "buy_price": buy_price,
                "buy_position": buy_position,
                "buy_amount": buy_amount,
                "stop_loss": stop_loss,
                "take_profit": take_profit
            }
            supabase.table("trade_records").insert(insert_data).execute()
            st.success("记录保存成功！")
            st.cache_data.clear()

# ====================== 3. 个股实时行情 ======================
elif menu == "个股实时行情":
    st.subheader("⏱️ 盘中实时行情查询")
    stock_code = st.text_input("输入股票代码（例如：600000）")
    if st.button("查询行情") and stock_code:
        try:
            df_stock = ak.stock_zh_a_spot_em()
            target = df_stock[df_stock["代码"] == stock_code].iloc[0]
            st.write(target)
        except Exception as e:
            st.error(f"获取行情失败：{e}")

# ====================== 4. 复盘分析 ======================
elif menu == "复盘分析":
    st.subheader("📊 交易复盘与策略评估")
    if df_trade.empty:
        st.warning("需要先录入交易记录")
    else:
        win_df = df_trade[df_trade["single_pnl"] > 0]
        lose_df = df_trade[df_trade["single_pnl"] < 0]
        win_rate = len(win_df)/len(df_trade) if len(df_trade)>0 else 0
        st.metric("总交易次数", len(df_trade))
        st.metric("胜率", f"{win_rate*100:.2f}%")
        st.dataframe(df_trade[["stock_name","buy_price","stop_loss","take_profit","single_pnl"]])

st.sidebar.info("风险提示：本工具仅用于个人交易记录复盘，不构成任何投资建议，股市有风险，入市需谨慎。")
