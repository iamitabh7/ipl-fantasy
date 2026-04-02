import streamlit as st

st.set_page_config(
    page_title="IPL 2026 Fantasy",
    page_icon="🏏",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0a0f;
    color: #f0f0f5;
}
.main { background-color: #0a0a0f; }
.block-container { padding-top: 2rem; padding-bottom: 4rem; }
h1, h2, h3 { font-family: 'Rajdhani', sans-serif !important; letter-spacing: 0.02em; }

.top-banner {
    background: linear-gradient(135deg, #1a1200 0%, #0a0a0f 60%);
    border: 1px solid rgba(245,166,35,0.3);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 8px;
}
.brand-label {
    font-family: 'Rajdhani', sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.15em;
    color: #f5a623;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.main-title {
    font-family: 'Rajdhani', sans-serif;
    font-size: 38px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1;
    margin: 0;
}
.main-title span { color: #f5a623; }
.subtitle { font-size: 13px; color: #7070a0; margin-top: 6px; }

.score-grid {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 0;
    align-items: center;
    margin: 20px 0;
}
.score-card {
    background: #13131a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 20px 18px;
}
.score-card.leader {
    background: linear-gradient(135deg, #1a1200 0%, #13131a 100%);
    border-color: #f5a623;
}
.score-name {
    font-family: 'Rajdhani', sans-serif;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.1em;
    color: #7070a0;
    text-transform: uppercase;
}
.score-card.leader .score-name { color: #f5a623; }
.score-pts {
    font-family: 'Rajdhani', sans-serif;
    font-size: 44px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1;
    margin-top: 4px;
}
.score-card.leader .score-pts { color: #f5a623; }
.score-label { font-size: 11px; color: #404060; margin-top: 3px; }
.score-wins { font-size: 12px; color: #7070a0; margin-top: 10px; }
.vs-col { text-align: center; padding: 0 14px; }
.vs-text {
    font-family: 'Rajdhani', sans-serif;
    font-size: 14px;
    font-weight: 700;
    color: #404060;
    letter-spacing: 0.1em;
}
.gap-pill {
    display: inline-block;
    background: rgba(245,166,35,0.1);
    border: 1px solid rgba(245,166,35,0.4);
    border-radius: 20px;
    padding: 4px 10px;
    font-size: 11px;
    color: #f5a623;
    margin-top: 8px;
    white-space: nowrap;
}

.section-title {
    font-family: 'Rajdhani', sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.12em;
    color: #7070a0;
    text-transform: uppercase;
    margin: 28px 0 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}

.rules-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.rules-table th {
    font-family: 'Rajdhani', sans-serif;
    font-size: 11px;
    letter-spacing: 0.1em;
    color: #7070a0;
    text-transform: uppercase;
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.rules-table td {
    padding: 8px 12px;
    color: #c0c0d0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.rules-table td:last-child { color: #f5a623; font-weight: 500; text-align: right; }

.player-grid { display: grid; grid-template-columns: 1fr 1fr; border-top: 1px solid rgba(255,255,255,0.06); }
.player-col { padding: 14px 18px; }
.player-col:first-child { border-right: 1px solid rgba(255,255,255,0.06); }
.team-head {
    font-family: 'Rajdhani', sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.1em;
    color: #7070a0;
    text-transform: uppercase;
    margin-bottom: 10px;
}
.team-head.winner { color: #2ecc71; }
.p-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 5px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.p-row:last-of-type { border-bottom: none; }
.p-name { font-size: 12px; color: #c0c0d0; display: flex; align-items: center; gap: 5px; }
.cap-badge {
    font-size: 9px;
    background: rgba(245,166,35,0.15);
    color: #f5a623;
    border: 1px solid rgba(245,166,35,0.4);
    border-radius: 3px;
    padding: 1px 4px;
    font-weight: 600;
}
.p-pts { font-family: 'Rajdhani', sans-serif; font-size: 14px; font-weight: 600; color: #ffffff; }
.p-detail { font-size: 10px; color: #404060; margin-top: 1px; }
.total-row {
    display: flex;
    justify-content: space-between;
    padding-top: 8px;
    margin-top: 6px;
    border-top: 1px solid rgba(255,255,255,0.08);
}
.total-label { font-size: 11px; color: #7070a0; }
.total-val { font-family: 'Rajdhani', sans-serif; font-size: 15px; font-weight: 700; color: #f5a623; }

.match-result {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
    padding: 10px 0;
}
.result-score { font-family: 'Rajdhani', sans-serif; font-size: 24px; font-weight: 700; }
.result-label { font-size: 12px; color: #7070a0; }

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="top-banner">
    <div class="brand-label">IPL 2026 · Fantasy League</div>
    <div class="main-title">The <span>Rivalry</span></div>
    <div class="subtitle">Amitabh vs Shivam &nbsp;·&nbsp; 5 matches played</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="score-grid">
    <div class="score-card leader">
        <div class="score-name">Amitabh</div>
        <div class="score-pts">1059</div>
        <div class="score-label">total points</div>
        <div class="score-wins">4W · 1L</div>
    </div>
    <div class="vs-col">
        <div class="vs-text">VS</div>
        <div class="gap-pill">+463 pts</div>
    </div>
    <div class="score-card">
        <div class="score-name">Shivam</div>
        <div class="score-pts">596</div>
        <div class="score-label">total points</div>
        <div class="score-wins">1W · 4L</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-title">Scoring Rules</div>', unsafe_allow_html=True)
with st.expander("View Rules"):
    st.markdown("""
<table class="rules-table">
<tr><th>Action</th><th>Points</th></tr>
<tr><td>1 Run</td><td>1 pt</td></tr>
<tr><td>1 Wicket</td><td>20 pts</td></tr>
<tr><td>Catch / Run Out / Stumping</td><td>10 pts</td></tr>
<tr><td>Half Century (50+ runs)</td><td>+10 bonus</td></tr>
<tr><td>Century (100+ runs)</td><td>+20 bonus</td></tr>
<tr><td>Five Wicket Haul</td><td>+20 bonus</td></tr>
<tr><td>Captain</td><td>2x all points</td></tr>
</table>
<p style="font-size:11px;color:#404060;margin-top:10px;">
5 players each, selected after toss from playing XI + impact subs. Fielding tracked as per Cricbuzz API.
</p>
""", unsafe_allow_html=True)

st.markdown('<div class="section-title">Match History</div>', unsafe_allow_html=True)

def match_card(title, date, status, a_total, s_total, a_winner, a_players, s_players):
    a_trophy = "🏆" if a_winner else ""
    s_trophy = "" if a_winner else "🏆"
    a_col = "#2ecc71" if a_winner else "#7070a0"
    s_col = "#7070a0" if a_winner else "#2ecc71"
    a_head = "winner" if a_winner else ""
    s_head = "" if a_winner else "winner"

    a_rows = ""
    for name, runs, wkts, catches, ros, pts, cap in a_players:
        cap_html = '<span class="cap-badge">C</span>' if cap else ""
        detail = f"{runs}r · {wkts}w · {catches}c"
        if ros: detail += f" · {ros}ro"
        a_rows += f'<div class="p-row"><div><span class="p-name">{name} {cap_html}</span><div class="p-detail">{detail}</div></div><span class="p-pts">{pts}</span></div>'

    s_rows = ""
    for name, runs, wkts, catches, ros, pts, cap in s_players:
        cap_html = '<span class="cap-badge">C</span>' if cap else ""
        detail = f"{runs}r · {wkts}w · {catches}c"
        if ros: detail += f" · {ros}ro"
        s_rows += f'<div class="p-row"><div><span class="p-name">{name} {cap_html}</span><div class="p-detail">{detail}</div></div><span class="p-pts">{pts}</span></div>'

    with st.expander(f"{title}  ·  {date}"):
        st.markdown(f"""
<div style="font-size:11px;color:#7070a0;margin-bottom:12px;">{status}</div>
<div class="match-result">
    <div>
        <div class="result-score" style="color:{a_col}">{a_total}</div>
        <div class="result-label">Amitabh {a_trophy}</div>
    </div>
    <div style="color:#404060;font-family:Rajdhani,sans-serif;font-size:14px;font-weight:700;padding:0 8px;">VS</div>
    <div>
        <div class="result-score" style="color:{s_col}">{s_total}</div>
        <div class="result-label">Shivam {s_trophy}</div>
    </div>
</div>
<div class="player-grid">
    <div class="player-col">
        <div class="team-head {a_head}">Amitabh {a_trophy}</div>
        {a_rows}
        <div class="total-row"><span class="total-label">Total</span><span class="total-val">{a_total}</span></div>
    </div>
    <div class="player-col">
        <div class="team-head {s_head}">Shivam {s_trophy}</div>
        {s_rows}
        <div class="total-row"><span class="total-label">Total</span><span class="total-val">{s_total}</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# name, runs, wickets, catches, runouts, points, is_captain
match_card("Match 5 — LSG vs DC", "Apr 1", "Delhi Capitals won by 6 wkts", 156, 58, True,
    [("KL Rahul", 0, 0, 1, 0, 20, True),
     ("Lungi Ngidi", 0, 3, 0, 0, 60, False),
     ("Mitchell Marsh", 35, 0, 0, 0, 35, False),
     ("Aiden Markram", 11, 0, 0, 0, 11, False),
     ("Mohsin Khan", 0, 1, 1, 0, 30, False)],
    [("Nicholas Pooran", 8, 0, 0, 0, 16, True),
     ("Mohammed Shami", 1, 1, 0, 0, 21, False),
     ("Axar Patel", 0, 1, 0, 0, 20, False),
     ("Anrich Nortje", 0, 0, 0, 0, 0, False),
     ("Pathum Nissanka", 1, 0, 0, 0, 1, False)])

match_card("Match 4 — GT vs PBKS", "Mar 31", "Punjab Kings won by 3 wkts", 154, 191, False,
    [("Shubman Gill", 39, 0, 2, 0, 59, False),
     ("Sai Sudharsan", 13, 0, 0, 0, 26, True),
     ("Glenn Phillips", 25, 0, 0, 0, 25, False),
     ("Prabhsimran Singh", 37, 0, 0, 0, 37, False),
     ("Priyansh Arya", 7, 0, 0, 0, 7, False)],
    [("Jos Buttler", 38, 0, 1, 0, 48, False),
     ("Shreyas Iyer", 18, 0, 1, 0, 56, True),
     ("Marco Jansen", 9, 1, 1, 0, 39, False),
     ("Washington Sundar", 18, 1, 1, 0, 48, False),
     ("Mohammed Siraj", 0, 0, 0, 0, 0, False)])

match_card("Match 3 — RR vs CSK", "Mar 30", "Rajasthan Royals won by 8 wkts", 142, 77, True,
    [("Vaibhav Sooryavanshi", 52, 0, 0, 0, 124, True),
     ("Shivam Dube", 6, 0, 0, 0, 6, False),
     ("Matthew Short", 2, 0, 0, 0, 2, False),
     ("Ayush Mhatre", 0, 0, 0, 0, 0, False),
     ("Shimron Hetmyer", 0, 0, 0, 1, 10, False)],
    [("Sanju Samson", 6, 0, 0, 0, 12, True),
     ("Riyan Parag", 14, 0, 0, 0, 14, False),
     ("Nandre Burger", 0, 2, 0, 0, 40, False),
     ("Matt Henry", 5, 0, 0, 0, 5, False),
     ("Ruturaj Gaikwad", 6, 0, 0, 0, 6, False)])

match_card("Match 2 — MI vs KKR", "Mar 29", "Mumbai Indians won by 6 wkts", 295, 96, True,
    [("Angkrish Raghuvanshi", 51, 0, 0, 0, 122, True),
     ("Rohit Sharma", 78, 0, 0, 0, 88, False),
     ("Finn Allen", 37, 0, 0, 0, 37, False),
     ("Hardik Pandya", 18, 1, 1, 0, 48, False),
     ("Jasprit Bumrah", 0, 0, 0, 0, 0, False)],
    [("Cameron Green", 18, 0, 0, 0, 36, True),
     ("Trent Boult", 0, 0, 0, 0, 0, False),
     ("Tilak Varma", 20, 0, 2, 0, 40, False),
     ("Sunil Narine", 0, 1, 0, 0, 20, False),
     ("Varun Chakaravarthy", 0, 0, 0, 0, 0, False)])

match_card("Match 1 — RCB vs SRH", "Mar 28", "Royal Challengers Bengaluru won by 6 wkts", 312, 174, True,
    [("Ishan Kishan", 80, 0, 0, 0, 180, True),
     ("Phil Salt", 0, 0, 3, 0, 30, False),
     ("Travis Head", 11, 0, 0, 0, 11, False),
     ("Rajat Patidar", 31, 0, 0, 0, 31, False),
     ("Romario Shepherd", 0, 3, 0, 0, 60, False)],
    [("Abhishek Sharma", 7, 0, 0, 0, 14, True),
     ("Virat Kohli", 69, 0, 1, 0, 89, False),
     ("Heinrich Klaasen", 31, 0, 2, 0, 51, False),
     ("Harshal Patel", 0, 0, 0, 0, 0, False),
     ("Bhuvneshwar Kumar", 0, 1, 0, 0, 20, False)])
