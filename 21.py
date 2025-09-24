import streamlit as st
import numpy as np
st.title("MIS功能")
st.header("By")
st.subheader("ldx")

h1 = st.number_input("输入数字")
height = np.float64(h1/100)#64位浮点型，h1必须为可转换的数据类型
if st.checkbox("提交"):#显示内容不会因为其他操作消失
    st.info(f"数字是：{height}")#infomation
if st.checkbox("显示"):
    num = st.slider("选择一个值：",min_value=15.0,max_value=35.0,value=20.0)
    #slider:滑动条
    #min_value:最小值 max_value:最大值
    #value:默认初始值
    if num < 16:
        st.error(f"立即")#
    if num<=18.5 and num>=16:
        st.warning(f"请增加蛋白质和碳水化合物摄入")
        st.warning(f" :( ，低碳生活标兵")
    if num >18.5 and num <=25:
        st.success(f"健康风险低，请均衡饮食，注意适量蛋白质和蔬菜")
        st.success(f" :) ，gooood")
    if num >25 and num<=30:
        st.warning(f"请减少高热量食物，增加膳食纤维")
        st.warning(f" :( ，大胃袋警告")
    if num>30:
        st.error(f"请严格控制热量摄入，少糖少油!!!")
        st.error(f"!，你现在不能进食，附近有良子在游荡")
