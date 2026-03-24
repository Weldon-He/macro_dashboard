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

# ====================== 以下代码保持不变（省略，你原有代码） ======================
# （把你原来的 INDICATORS 定义、get_macro_data 函数、页面逻辑等接在后面）
