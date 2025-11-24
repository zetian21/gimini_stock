import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 页面配置 ---
st.set_page_config(page_title="A股实时行情看板", layout="wide")

# --- 侧边栏：用户输入 ---
st.sidebar.title("📈 股票查询")
stock_code = st.sidebar.text_input("输入股票代码 (例如: 600519)", value="600519")
period = st.sidebar.selectbox("K线周期", ["daily", "weekly", "monthly"], index=0)
days_back = st.sidebar.slider("显示最近多少天的数据", min_value=30, max_value=365*3, value=120)

st.sidebar.markdown("---")
st.sidebar.caption("数据来源: AkShare (开源)")

# --- 核心函数 ---

@st.cache_data(ttl=60) # 缓存数据60秒，避免频繁请求
def get_realtime_price(code):
    """获取个股最新实时行情"""
    try:
        # AkShare 获取实时行情通常需要拉取全市场数据后筛选，或者使用特定接口
        # 这里使用东方财富的个股人气榜或实时行情接口
        df = ak.stock_zh_a_spot_em()
        stock_info = df[df['代码'] == code]
        if not stock_info.empty:
            return stock_info.iloc[0]
        else:
            return None
    except Exception as e:
        st.error(f"获取实时数据失败: {e}")
        return None

@st.cache_data(ttl=3600) # 历史数据缓存1小时
def get_history_data(code, period='daily', start_date='20200101', end_date='20991231'):
    """获取个股历史K线数据"""
    try:
        # 调整周期参数以适配AkShare
        adjust = "qfq" # 前复权
        df = ak.stock_zh_a_hist(symbol=code, period=period, start_date=start_date, end_date=end_date, adjust=adjust)
        
        # 清洗数据列名以便Plotly使用
        df.rename(columns={'日期': 'Date', '开盘': 'Open', '收盘': 'Close', 
                           '最高': 'High', '最低': 'Low', '成交量': 'Volume'}, inplace=True)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except Exception as e:
        st.error(f"获取历史数据失败 (请检查代码是否正确): {e}")
        return None

def get_stock_name(code):
    """简单获取股票名称"""
    try:
        df = ak.stock_individual_info_em(symbol=code)
        # 假设返回的df中包含名称信息，不同接口返回格式不同，这里做简易处理
        # 通常 stock_zh_a_spot_em 已经包含了名称
        return "查询中..." 
    except:
        return "Unknown"

# --- 主页面逻辑 ---

if stock_code:
    # 1. 获取实时数据
    realtime_data = get_realtime_price(stock_code)
    
    if realtime_data is not None:
        name = realtime_data['名称']
        price = realtime_data['最新价']
        change = realtime_data['涨跌额']
        pct_change = realtime_data['涨跌幅']
        volume = realtime_data['成交量']
        amount = realtime_data['成交额']
        
        # 颜色判断
        color_metric = "normal"
        if change > 0: color_metric = "off" # Streamlit delta 默认绿色是涨，A股红色是涨，需要反着看或者自定义
        
        st.title(f"{name} ({stock_code})")
        
        # 显示主要指标
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="最新价", value=price, delta=f"{change} ({pct_change}%)")
        with col2:
            st.metric(label="最高", value=realtime_data['最高'])
        with col3:
            st.metric(label="最低", value=realtime_data['最低'])
        with col4:
            # 成交量换算为万手
            vol_wan = round(volume / 100, 2) 
            st.metric(label="成交量(手)", value=f"{vol_wan:,.0f}")

        # 2. 获取历史数据并绘图
        start_dt = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
        end_dt = datetime.now().strftime("%Y%m%d")
        
        hist_df = get_history_data(stock_code, period, start_dt, end_dt)
        
        if hist_df is not None and not hist_df.empty:
            st.subheader(f"{period.capitalize()} K-Line Chart")
            
            # 计算移动平均线
            hist_df['MA5'] = hist_df['Close'].rolling(window=5).mean()
            hist_df['MA20'] = hist_df['Close'].rolling(window=20).mean()

            # 绘制K线图
            fig = go.Figure()

            # K线
            fig.add_trace(go.Candlestick(
                x=hist_df['Date'],
                open=hist_df['Open'],
                high=hist_df['High'],
                low=hist_df['Low'],
                close=hist_df['Close'],
                name='K线',
                increasing_line_color='red', 
                decreasing_line_color='green'
            ))

            # 均线
            fig.add_trace(go.Scatter(x=hist_df['Date'], y=hist_df['MA5'], opacity=0.7, line=dict(color='blue', width=1), name='MA5'))
            fig.add_trace(go.Scatter(x=hist_df['Date'], y=hist_df['MA20'], opacity=0.7, line=dict(color='orange', width=1), name='MA20'))

            # 布局设置
            fig.update_layout(
                xaxis_rangeslider_visible=False,
                height=600,
                title_text=f"{name} 走势图",
                template="plotly_white"
            )

            st.plotly_chart(fig, use_container_width=True)
            
            # 显示数据表格（可选）
            with st.expander("查看历史数据详情"):
                st.dataframe(hist_df.sort_values(by='Date', ascending=False))
        
    else:
        st.warning("未找到该股票数据，请检查代码是否正确（如：600519）。")
else:
    st.info("请在左侧输入股票代码开始查询。")