import streamlit as st
import pandas as pd

st.set_page_config(page_title="Lead Manager", layout="wide")

st.title("🚀 Lead Export Manager")

uploaded_file = st.file_uploader("העלה קובץ לידים (Excel או CSV)")

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("תצוגה מקדימה")
    st.dataframe(df)

    columns = df.columns.tolist()
    phone_col = st.selectbox("בחר עמודת טלפון", columns)

    if st.button("נקה טלפונים"):

        def clean_phone(phone):
            if pd.isna(phone):
                return None
            
            phone = str(phone)
            phone = phone.replace("-", "").replace(" ", "")

            if phone.startswith("972"):
                phone = "0" + phone[3:]

            if len(phone) == 9 and phone.startswith("5"):
                phone = "0" + phone

            if len(phone) == 10 and phone.startswith("05"):
                return phone
            
            return None

        df["phone_clean"] = df[phone_col].apply(clean_phone)

        df["status"] = df["phone_clean"].apply(
            lambda x: "✅ תקין" if x else "❌ לא תקין"
        )

        st.success("סיום ניקוי!")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("תקינים")
            st.dataframe(df[df["status"] == "✅ תקין"])

        with col2:
            st.subheader("לא תקינים")
            st.dataframe(df[df["status"] == "❌ לא תקין"])

        csv = df.to_csv(index=False).encode('utf-8-sig')

        st.download_button(
            "📥 הורד קובץ מסודר",
            csv,
            "clean_leads.csv",
            "text/csv"
        )
