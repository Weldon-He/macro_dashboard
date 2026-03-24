# -*- coding: utf-8 -*-
"""
宏观指标监控仪表盘
"""
import os
# ====================== 关键修复：禁用OpenBB自动构建 ======================
# 设置环境变量，跳过OpenBB的自动构建（解决权限问题）
os.environ["OPENBB_AUTO_BUILD"] = "false"
os.environ["OPENBB_ENABLE_PROMPT_TOOLKIT"] = "false"

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 延迟导入OpenBB（先设置环境变量再导入）
try:
    from openbb import obb
    OPENBB_AVAILABLE = True
except ImportError:
    OPENBB_AVAILABLE = False
    st.error("❌ 未安装 openbb 库！请检查 requirements.txt")

# ====================== 基础配置 ======================
st.set_page_config(page_title="宏观指标监控仪表盘", layout="wide")

# ====================== 读取FRED Key ======================
if OPENBB_AVAILABLE:
    fred_api_key = os.getenv("FRED_API_KEY")
    if not fred_api_key:
        st.error("❌ 未读取到FRED API Key！请先配置环境变量并重启")
        st.stop()
    # 手动初始化FRED凭证（避免OpenBB自动加载配置）
    obb.user.credentials.fred_api_key = fred_api_key
else:
    st.stop()

# ====================== 定义指标 ======================
INDICATORS = {
    "T5YIE": {"name": "5年期盈亏平衡通胀率", "desc": "反映市场对5年通胀的预期", "color": "#1f77b4"},
    "T5YIFR": {"name": "5年期远期通胀预期", "desc": "更前瞻的通胀预期指标", "color": "#ff7f0e"},
    "DGS2": {"name": "2年期美债收益率", "desc": "反映美联储政策预期", "color": "#2ca02c"},
    "BAMLH0A0HYM2": {"name": "高收益债OAS", "desc": "信用利差，越高信用风险越大", "color": "#d62728"},
    "VIXCLS": {"name": "VIX恐慌指数", "desc": ">30为高恐慌，<20为低恐慌", "color": "#9467bd"},
    "NFCI": {"name": "金融状况指数", "desc": ">0收紧，<0宽松", "color": "#8c564b"},
    "ICSA": {"name": "初请失业金人数", "desc": "失业金首次申请数，反映就业情况", "color": "#e377c2"},
    "SAHMREALTIME": {"name": "Sahm衰退指标", "desc": ">0.5大概率进入衰退", "color": "#7f7f7f"},
}

# ====================== 缓存数据 ======================
@st.cache_data(ttl=3600)
def get_macro_data():
    data_dict = {}
    # 先拉取全量数据（2018至今）
    for code, cfg in INDICATORS.items():
        df = obb.economy.fred_series(
            symbol=code,
            start_date="2018-01-01",
            api_key=fred_api_key
        ).to_df()
        
        # 适配列名
        if "value" in df.columns:
            df.rename(columns={"value": cfg["name"]}, inplace=True)
        elif code not in df.columns and len(df.columns) >= 1:
            df.rename(columns={df.columns[-1]: cfg["name"]}, inplace=True)
        else:
            df.rename(columns={code: cfg["name"]}, inplace=True)
        
        # 确保索引是日期格式
        df.index = pd.to_datetime(df.index)
        # 去空值并保留必要列
        if cfg["name"] in df.columns:
            data_dict[code] = df[[cfg["name"]]].dropna()
        else:
            data_dict[code] = pd.DataFrame()
    return data_dict

# ====================== 数据预处理（合并用于叠加） ======================
def merge_selected_data(selected_codes, data_dict):
    """合并选中的指标数据，对齐日期"""
    df_list = []
    for code in selected_codes:
        if not data_dict[code].empty:
            df_list.append(data_dict[code])
    if df_list:
        merged_df = pd.concat(df_list, axis=1, join='outer').sort_index()
        return merged_df
    return pd.DataFrame()

# ====================== 主页面 ======================
st.title("📊 宏观指标交互式监控仪表盘")
st.divider()

# 拉取数据
with st.spinner("正在拉取最新数据..."):
    data_dict = get_macro_data()

# ----------------------
# 侧边栏：交互配置（核心）
# ----------------------
with st.sidebar:
    st.header("⚙️ 交互配置")
    
    # 1. 自定义时间范围
    st.subheader("1. 时间范围")
    # 获取全量数据的日期范围
    all_dates = []
    for df in data_dict.values():
        if not df.empty:
            all_dates.extend(df.index.tolist())
    min_date = pd.to_datetime(min(all_dates)) if all_dates else pd.to_datetime("2018-01-01")
    max_date = pd.to_datetime(max(all_dates)) if all_dates else pd.to_datetime("2026-03-01")
    
    # 时间选择器
    start_date = st.date_input(
        "起始日期",
        value=min_date,
        min_value=min_date,
        max_value=max_date
    )
    end_date = st.date_input(
        "结束日期",
        value=max_date,
        min_value=min_date,
        max_value=max_date
    )
    # 转换为datetime
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    # 2. 指标选择（支持多选，用于叠加）
    st.subheader("2. 指标选择")
    # 单选（单独查看）
    single_code = st.selectbox(
        "单独查看指标",
        options=list(INDICATORS.keys()),
        format_func=lambda x: INDICATORS[x]["name"],
        index=0
    )
    # 多选（叠加对比）
    selected_codes = st.multiselect(
        "叠加对比指标（最多选4个）",
        options=list(INDICATORS.keys()),
        format_func=lambda x: INDICATORS[x]["name"],
        default=[single_code],
        max_selections=4
    )

# ----------------------
# 主体内容
# ----------------------
tab1, tab2 = st.tabs(["📈 单个指标详情", "🔄 多指标叠加对比"])

# Tab1：单个指标详情（重点支持鼠标悬停）
with tab1:
    st.subheader(f"{INDICATORS[single_code]['name']} - 详情")
    st.caption(INDICATORS[single_code]["desc"])
    
    # 获取该指标数据并筛选时间范围
    df_single = data_dict[single_code]
    if not df_single.empty:
        # 筛选时间范围
        df_filtered = df_single[
            (df_single.index >= start_dt) & 
            (df_single.index <= end_dt)
        ]
        
        if not df_filtered.empty:
            # 用Plotly绘制交互式图表（核心：鼠标悬停显示日期+数值）
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_filtered.index,
                y=df_filtered[INDICATORS[single_code]["name"]],
                mode="lines+markers",  # 线+点，方便悬停
                line=dict(color=INDICATORS[single_code]["color"], width=2),
                hovertemplate=(
                    "📅 日期: %{x}<br>" +
                    "📊 数值: %{y:.2f}<br>" +
                    "<extra></extra>"  # 隐藏额外信息
                ),
                name=INDICATORS[single_code]["name"]
            ))
            
            # 图表样式优化
            fig.update_layout(
                title=f"{INDICATORS[single_code]['name']} ({start_date} 至 {end_date})",
                xaxis_title="日期",
                yaxis_title="数值",
                hovermode="x unified",  # 悬停时同步显示x轴信息
                height=600,
                template="plotly_white"
            )
            
            # 显示图表
            st.plotly_chart(fig, use_container_width=True)
            
            # 显示最新数据
            st.subheader("📌 最新数据")
            latest_row = df_filtered.iloc[-1]
            col1, col2, col3 = st.columns(3)
            col1.metric("最新值", f"{latest_row.iloc[0]:.2f}" if single_code != "ICSA" else f"{int(latest_row.iloc[0]):,}")
            col2.metric("最新日期", latest_row.name.strftime("%Y-%m-%d"))
            col3.metric("数据条数", len(df_filtered))
        else:
            st.warning(f"该时间范围（{start_date} 至 {end_date}）内无数据")
    else:
        st.warning("暂无有效数据")

# Tab2：多指标叠加对比（支持悬停+自定义时间）
with tab2:
    st.subheader("多指标叠加对比")
    st.caption("支持最多4个指标叠加，鼠标悬停可查看每个指标的数值")
    
    # 合并选中的指标数据
    merged_df = merge_selected_data(selected_codes, data_dict)
    if not merged_df.empty:
        # 筛选时间范围
        df_merged_filtered = merged_df[
            (merged_df.index >= start_dt) & 
            (merged_df.index <= end_dt)
        ]
        
        if not df_merged_filtered.empty:
            # 绘制叠加对比图
            fig = go.Figure()
            
            # 逐个添加选中的指标
            for code in selected_codes:
                cfg = INDICATORS[code]
                if cfg["name"] in df_merged_filtered.columns:
                    fig.add_trace(go.Scatter(
                        x=df_merged_filtered.index,
                        y=df_merged_filtered[cfg["name"]],
                        mode="lines",
                        line=dict(color=cfg["color"], width=2),
                        hovertemplate=(
                            f"📅 日期: %{{x}}<br>" +
                            f"📊 {cfg['name']}: %{{y:.2f}}<br>" +
                            "<extra></extra>"
                        ) if code != "ICSA" else (
                            f"📅 日期: %{{x}}<br>" +
                            f"📊 {cfg['name']}: %{{y:,.0f}}<br>" +
                            "<extra></extra>"
                        ),
                        name=cfg["name"]
                    ))
            
            # 图表样式
            fig.update_layout(
                title=f"多指标叠加对比 ({start_date} 至 {end_date})",
                xaxis_title="日期",
                yaxis_title="数值",
                hovermode="x unified",
                height=600,
                template="plotly_white",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.2,
                    xanchor="center",
                    x=0.5
                )
            )
            
            # 显示图表
            st.plotly_chart(fig, use_container_width=True)
            
            # 显示选中指标的最新值汇总
            st.subheader("📌 选中指标最新值")
            latest_merged = df_merged_filtered.iloc[-1].dropna()
            cols = st.columns(len(latest_merged))
            for idx, (name, value) in enumerate(latest_merged.items()):
                cols[idx].metric(
                    name,
                    f"{value:.2f}" if "初请失业金" not in name else f"{int(value):,}"
                )
        else:
            st.warning(f"该时间范围（{start_date} 至 {end_date}）内无数据")
    else:
        st.warning("请选择至少1个有效指标")

st.divider()
st.caption("💡 核心交互说明：\n1. 鼠标悬停在曲线上可显示「日期+精确数值」；\n2. 侧边栏可自定义时间范围；\n3. 支持单个指标详情/多指标叠加对比；\n4. 图表可缩放、下载、平移。")
