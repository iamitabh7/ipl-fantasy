import streamlit as st

st.set_page_config(page_title="IPL 2026 Fantasy", page_icon="🏏", layout="centered")

st.title("IPL 2026 Fantasy 🏏")
st.caption("Amitabh vs Shivam · Season Tracker")

st.write("---")

col1, col2 = st.columns(2)
with col1:
    st.metric(label="🟡 Amitabh", value="898 pts", delta="leads by 370")
with col2:
    st.metric(label="🔵 Shivam", value="528 pts")

st.write("---")

with st.expander("📋 Scoring Rules"):
    st.markdown("""
| Action | Points |
|---|---|
| 1 Run | 1 pt |
| 1 Wicket | 20 pts |
| Catch / Run Out / Stumping | 10 pts |
| Half Century (50+ runs) | +10 bonus |
| Century (100+ runs) | +20 bonus |
| Five Wicket Haul | +20 bonus |
| Captain | 2x all points |
    """)
    st.caption("Fielding tracked as per Cricbuzz scorecard.")

st.write("---")

st.subheader("Match History")

with st.expander("Match 4 — GT vs PBKS · Mar 31  |  🔵 Shivam wins  191 vs 144"):
    c1, c2 = st.columns(2)
    with c1:
        st.write("**🟡 Amitabh**")
        st.write("Sai Sudharsan ⭐ — 26")
        st.write("Shubman Gill — 49")
        st.write("Glenn Phillips — 25")
        st.write("Prabhsimran Singh — 37")
        st.write("Priyansh Arya — 7")
        st.write("**Total: 144**")
    with c2:
        st.write("**🔵 Shivam 🏆**")
        st.write("Shreyas Iyer ⭐ — 56")
        st.write("Jos Buttler — 48")
        st.write("Marco Jansen — 39")
        st.write("Washington Sundar — 48")
        st.write("Mohammed Siraj — 0")
        st.write("**Total: 191**")

with st.expander("Match 3 — RR vs CSK · Mar 30  |  🟡 Amitabh wins  142 vs 77"):
    c1, c2 = st.columns(2)
    with c1:
        st.write("**🟡 Amitabh 🏆**")
        st.write("Vaibhav Sooryavanshi ⭐ — 124")
        st.write("Shivam Dube — 6")
        st.write("Matthew Short — 2")
        st.write("Ayush Mhatre — 0")
        st.write("Shimron Hetmyer — 10")
        st.write("**Total: 142**")
    with c2:
        st.write("**🔵 Shivam**")
        st.write("Sanju Samson ⭐ — 12")
        st.write("Riyan Parag — 14")
        st.write("Nandre Burger — 40")
        st.write("Matt Henry — 5")
        st.write("Ruturaj Gaikwad — 6")
        st.write("**Total: 77**")

with st.expander("Match 2 — MI vs KKR · Mar 29  |  🟡 Amitabh wins  295 vs 96"):
    c1, c2 = st.columns(2)
    with c1:
        st.write("**🟡 Amitabh 🏆**")
        st.write("Angkrish ⭐ — 122")
        st.write("Rohit Sharma — 88")
        st.write("Finn Allen — 37")
        st.write("Hardik Pandya — 48")
        st.write("Jasprit Bumrah — 0")
        st.write("**Total: 295**")
    with c2:
        st.write("**🔵 Shivam**")
        st.write("Cameron Green ⭐ — 36")
        st.write("Trent Boult — 0")
        st.write("Tilak Varma — 40")
        st.write("Sunil Narine — 20")
        st.write("Varun Chakravarthy — 0")
        st.write("**Total: 96**")

with st.expander("Match 1 — RCB vs SRH · Mar 28  |  🟡 Amitabh wins  317 vs 164"):
    c1, c2 = st.columns(2)
    with c1:
        st.write("**🟡 Amitabh 🏆**")
        st.write("Ishan Kishan ⭐ — 180")
        st.write("Phil Salt — 39")
        st.write("Travis Head — 7")
        st.write("Rajat Patidar — 31")
        st.write("Romario Shepherd — 60")
        st.write("**Total: 317**")
    with c2:
        st.write("**🔵 Shivam**")
        st.write("Abhishek Sharma ⭐ — 14")
        st.write("Virat Kohli — 89")
        st.write("H. Klaasen — 41")
        st.write("Harshal Patel — 0")
        st.write("Bhuvneshwar Kumar — 20")
        st.write("**Total: 164**")
