import streamlit as st

st.title("IPL 2026 Fantasy 🏏")

# Season totals
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Amitabh", value="612 pts")
with col2:
    st.metric(label="Shivam", value="260 pts")

st.caption("Amitabh leads by 352 points")
st.write("---")

# Match history
st.subheader("Match History")

with st.expander("Match 1 — RCB vs SRH · Mar 28"):
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Amitabh** 🏆")
        st.write("Ishan Kishan (C) — 180")
        st.write("Phil Salt — 39")
        st.write("Travis Head — 7")
        st.write("Rajat Patidar — 31")
        st.write("Romario Shepherd — 60")
        st.write("**Total: 317**")
    with c2:
        st.write("**Shivam**")
        st.write("Abhishek Sharma (C) — 14")
        st.write("Virat Kohli — 89")
        st.write("H. Klaasen — 41")
        st.write("Harshal Patel — 0")
        st.write("Bhuvneshwar Kumar — 20")
        st.write("**Total: 164**")

with st.expander("Match 2 — MI vs KKR · Mar 29"):
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Amitabh** 🏆")
        st.write("Angkrish (C) — 122")
        st.write("Rohit Sharma — 88")
        st.write("Finn Allen — 37")
        st.write("Hardik Pandya — 48")
        st.write("Jasprit Bumrah — 0")
        st.write("**Total: 295**")
    with c2:
        st.write("**Shivam**")
        st.write("Cameron Green (C) — 36")
        st.write("Trent Boult — 0")
        st.write("Tilak Varma — 40")
        st.write("Sunil Narine — 20")
        st.write("Varun Chakravarthy — 0")
        st.write("**Total: 96**")