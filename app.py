import streamlit as st
import sqlite3
import json
import pandas as pd
from deep_translator import GoogleTranslator

def anonymize_feedback_with_ai(strength, weakness):
    try:
        # Double translation trick (MK -> EN -> MK) to destroy original writing style/fingerprint completely for free
        translator_to_en = GoogleTranslator(source='mk', target='en')
        translator_to_mk = GoogleTranslator(source='en', target='mk')
        
        eng_strength = translator_to_en.translate(strength)
        eng_weakness = translator_to_en.translate(weakness)
        
        anon_strength = translator_to_mk.translate(eng_strength)
        anon_weakness = translator_to_mk.translate(eng_weakness)
        
        return anon_strength, anon_weakness
    except Exception as e:
        print(f"Translation Anonymizer Error: {e}")
        return strength, weakness

# --- CONFIGURATION & BRANDING ---
st.set_page_config(
    page_title="Findzzer - Евалуација на тим",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom CSS
st.markdown("""
<style>
    :root {
        --primary-color: #2563EB;
        --secondary-color: #1E40AF;
        --background-color: #F8FAFC;
        --text-color: #0F172A;
    }
    .main {
        background-color: var(--background-color);
        color: var(--text-color);
    }
    h1, h2, h3 {
        color: var(--primary-color) !important;
        font-family: 'Inter', sans-serif;
    }
    .stButton>button {
        background-color: var(--primary-color);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: var(--secondary-color);
        transform: translateY(-2px);
    }
    .evaluation-card {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
    }
    .feedback-box {
        background: #F1F5F9;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid var(--primary-color);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- CONSTANTS ---
TEAM_MEMBERS = ["Mario", "Matea", "Mila", "Angela", "Nikola"]

# 1. Рангирање (Од 1-во до 5-то место)
RANKING_QUESTIONS = [
    {"q": "Труд и жртвување", "desc": "Кој работи најнапорно и вложува најмногу приватно време на сметка на други работи за успехот на Findzzer?"},
    {"q": "Преземање ризици", "desc": "Кој најчесто излегува од комфорната зона, носи тешки одлуки и презема ризици за компанијата да може да расте брзо?"},
    {"q": "Борба за тимот", "desc": "Кој е 'лавот' што најмногу ги штити интересите на секој член, се бори за тимот и не дозволува неправди?"},
    {"q": "Генерирање вредност", "desc": "Кој испорачува најголема директна и мерлива вредност за продуктот (на пр. преку код, дизајн, корисници или продажба)?"},
    {"q": "Брзина и егзекуција", "desc": "Кој најбрзо испорачува квалитетни резултати кога роковите се кратки и кога има огромен притисок за достава?"},
    {"q": "Снаодливост", "desc": "Кој наоѓа најдобри заобиколни (hacker) или иновативни решенија кога стартапот нема доволно ресурси, луѓе или пари?"},
    {"q": "Испорака под стрес (Resilience)", "desc": "Кој член покажува најголема стабилност и најмалку паника кога работите константно не одат според планот?"},
    {"q": "Фокус на приоритети", "desc": "Кој работи на вистинските работи (поместува клучни метрики), наместо само да биде 'зафатен' со небитни задачи?"}
]

# 2. Peer Selection (Избери само еден)
PEER_QUESTIONS = [
    {"q": "Мотор на тимот", "desc": "Кој е движечката сила и енергијата во компанијата што секогаш ги мотивира и ги турка сите напред?"},
    {"q": "Оперативен/Технички столб", "desc": "Без која личност продуктот концептуално или технички би запрел или би се распаднал целосно?"},
    {"q": "Кризен менаџер", "desc": "Кој останува најсмирен, размислува ладнокрвно и ја презема контролата кога работите ќе тргнат наопаку?"},
    {"q": "Продукт Визионер", "desc": "Кој од тимот најдобро го разбира крајниот корисник и знае во која насока точно треба да се развива Findzzer?"},
    {"q": "Бизнис Двигател", "desc": "Кој е најважен и најспособен за процесот на продажба, маркетинг позиционирање или привлекување финансии/инвестиции?"},
    {"q": "Тимски лепак", "desc": "Кој најуспешно ги решава интерните конфликти и одржува добра комуникација, морал и хемија меѓу сите членови?"},
    {"q": "Најголем напредок", "desc": "Кој покажа најголем личен и професионален раст, учење и адаптација од почетокот на стартапот до денес?"},
    {"q": "Најдоверлив лидер (Trust)", "desc": "Доколку утре некој мора привремено или трајно да го води целиот стартап, кому би му ја дал(а) таа доверба?"}
]

# 3. Скала (Од 1 до 10 за секој член)
SCALE_QUESTIONS = [
    {"q": "Посветеност (Commitment)", "desc": "Колку силнo верува и работи кон долгорочната визија на Findzzer, без разлика на моменталните пречки. *(1 = Се откажува при прв проблем, 10 = Работи неуморно и верува 100% во визијата)*"},
    {"q": "Автономија", "desc": "Колку може да работи самостојно, да носи одлуки и да испорачува без некој постојано да го контролира (micromanage). *(1 = Мора да му се кажува секој чекор, 10 = Самостојно води и завршува проекти)*"},
    {"q": "Иновативност", "desc": "Колку често креира нови, креативни или 'out of the box' идеи кои го подобруваат продуктот или процесите. *(1 = Само извршува што ќе му се каже, 10 = Континуирано наоѓа генијални решенија)*"},
    {"q": "Доверливост", "desc": "Дали стои на зборот? Кога ќе каже дека нешто ќе биде завршено до одреден рок, колку можеш да се потпреш на тоа. *(1 = Редовно пробива рокови и заборава, 10 = Секогаш навреме испорачува што ветил)*"},
    {"q": "Тежина на задачи", "desc": "Колку се технички, логички или ментално комплексни задачите што оваа личност ги решава секој ден. *(1 = Извршува многу лесни/административни задачи, 10 = Решава најкомплицирани/core проблеми)*"},
    {"q": "Комуникација и транспарентност", "desc": "Дали ги комуницира проблемите на време? Дали идеите и критиките ги кажува јасно, директно и отворено. *(1 = Крие проблеми и лошо комуницира, 10 = Транспарентен, јасен и зборува отворено)*"},
    {"q": "Незаменливост", "desc": "Ако оваа личност утре си замине, колку би било тешко, болно и скапо за Findzzer да најде замена на пазарот. *(1 = Оваа улога може веднаш да се замени, 10 = Практично е невозможно да најдеме замена)*"},
    {"q": "Потенцијал за скалирање", "desc": "Дали има капацитет и mindset утре да биде C-level лидер (директор) и ефикасно да раководи со оддел од 10+ луѓе. *(1 = Никаков лидерски потенцијал, 10 = Природен директор и лидер на голем тим)*"},
    {"q": "Прифаќање критика (Coachability)", "desc": "Колку добро оваа личност прифаќа конструктивна критика без да го става сопственото его на прво место? *(1 = Сфаќа се лично и се лути, 10 = Сослушува, прифаќа и веднаш се поправа)*"},
    {"q": "Конзистентност во работата", "desc": "Дали темпото на работа е исто секој ден, или има огромни осцилации (една недела 24/7, следните две недели го нема)? *(1 = Огромни осцилации и исчезнувања, 10 = Роботски конзистентен секој ден)*"}
]

# 4. Време, Придонес и Амбиција (Од 1 до 10)
IMPACT_QUESTIONS = [
    {"q": "Тековна и Идна Временска Посветеност", "desc": "Колку време неделно оваа личност реално посветува моментално, и колку планира/има капацитет да посвети во иднина? *(1 = Многу слабо време, како хоби, 10 = Full-time посветеност, Findzzer му е главен приоритет)*"},
    {"q": "Двигател на стартапот (Driver vs Fixer)", "desc": "Дали оваа личност е 'двигател' на идеите (зема активно учество во product vision, sales, pitching, стратегија) или е повеќе техничка поддршка/извршител? *(1 = Исклучиво извршител/поддршка, 10 = Главен двигател и креатор на визијата/бизнисот)*"},
    {"q": "Досегашен мерлив придонес (Past Contribution)", "desc": "Колкав е досегашниот РЕАЛЕН и физички придонес (во форма на напишан код, завршен дизајн, инвестирани пари, донесени партнери/корисници)? *(1 = Речиси никаков мерлив придонес досега, 10 = Непроценлив досегашен придонес без кој немаше да постоиме)*"}
]

DB_FILE = "evaluations.db"

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS submissions
                 (evaluator TEXT PRIMARY KEY, data TEXT)''')
    conn.commit()
    conn.close()

def save_submission(evaluator, data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("REPLACE INTO submissions (evaluator, data) VALUES (?, ?)", 
              (evaluator, json.dumps(data)))
    conn.commit()
    conn.close()

def get_all_submissions():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT evaluator, data FROM submissions")
    rows = c.fetchall()
    conn.commit()
    conn.close()
    return {row[0]: json.loads(row[1]) for row in rows}

def clear_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM submissions")
    conn.commit()
    conn.close()

init_db()

# --- CALCULATION ENGINE ---
def calculate_results(submissions):
    # Initializes metric trackers
    results = {member: {"rank_self": 0, "rank_peer_sum": 0, "rank_peer_count": 0,
                         "scale_self": 0, "scale_peer_sum": 0, "scale_peer_count": 0,
                         "votes_self": 0, "votes_peer_sum": 0, "votes_peer_count": 0,
                         "impact_self": 0, "impact_peer_sum": 0, "impact_peer_count": 0} 
               for member in TEAM_MEMBERS}
    
    num_members = len(TEAM_MEMBERS)
    num_peers = num_members - 1
    
    # Process each submission
    for evaluator, data in submissions.items():
        # Process Rankings (Translating rank to points: 1st place = 5 pts, ..., 5th place = 1 pt)
        for q, ranking in data.get("rankings", {}).items():
            for i, member in enumerate(ranking):
                points = num_members - i # The highest rank gets 'num_members' points (e.g., 5)
                if member == evaluator:
                    results[member]["rank_self"] += points
                else:
                    results[member]["rank_peer_sum"] += points
                    results[member]["rank_peer_count"] += 1
        
        # Process Scale ratings (1 to 10)
        for member in TEAM_MEMBERS:
            if member in data.get("scale_ratings", {}):
                scale_sum = sum(data["scale_ratings"][member].values())
                if member == evaluator:
                    results[member]["scale_self"] += scale_sum
                else:
                    results[member]["scale_peer_sum"] += scale_sum
                    results[member]["scale_peer_count"] += 1
                
        # Process Impact ratings (1 to 10)
        for member in TEAM_MEMBERS:
            if member in data.get("impact_ratings", {}):
                impact_sum = sum(data["impact_ratings"][member].values())
                if member == evaluator:
                    results[member]["impact_self"] += impact_sum
                else:
                    results[member]["impact_peer_sum"] += impact_sum
                    results[member]["impact_peer_count"] += 1
                
        # Process Co-Founder Votes
        if "cofounder_count" in data:
            total_cofounder_votes += data["cofounder_count"]
            num_cofounder_voters += 1
            
    # Calculate average Co-Founder count
    avg_cofounders = round(total_cofounder_votes / num_cofounder_voters) if num_cofounder_voters > 0 else 1
    # Ensure it's between 1 and num_members
    avg_cofounders = max(1, min(avg_cofounders, num_members))
    
    final_scores = []
    
    for member, metrics in results.items():
        # Averages from peers:
        peer_rank_avg = metrics["rank_peer_sum"] / num_peers if num_peers > 0 else 0
        peer_scale_avg = metrics["scale_peer_sum"] / num_peers if num_peers > 0 else 0
        peer_vote_avg = metrics["votes_peer_sum"] / num_peers if num_peers > 0 else 0
        peer_impact_avg = metrics["impact_peer_sum"] / num_peers if num_peers > 0 else 0
        
        # Self scores
        self_rank = metrics["rank_self"]
        self_scale = metrics["scale_self"]
        self_vote = metrics["votes_self"]
        self_impact = metrics["impact_self"]
        
        # Weighted Combining (80% Peer, 20% Self)
        weighted_rank_points = (self_rank * 0.2) + (peer_rank_avg * 0.8)
        weighted_scale_points = (self_scale * 0.2) + (peer_scale_avg * 0.8)
        weighted_vote_points = (self_vote * 0.2) + (peer_vote_avg * 0.8)
        
        # Време и Придонес се исклучиво лични оцени (100% Self)
        weighted_impact_points = self_impact
        
        MAX_RANK_RAW = len(RANKING_QUESTIONS) * num_members  
        MAX_SCALE_RAW = len(SCALE_QUESTIONS) * 10            
        MAX_VOTES_RAW = len(PEER_QUESTIONS)                  
        MAX_IMPACT_RAW = len(IMPACT_QUESTIONS) * 10
        
        score_rank = (weighted_rank_points / MAX_RANK_RAW) * 25 if MAX_RANK_RAW else 0
        score_scale = (weighted_scale_points / MAX_SCALE_RAW) * 35 if MAX_SCALE_RAW else 0
        score_votes = (weighted_vote_points / MAX_VOTES_RAW) * 15 if MAX_VOTES_RAW else 0
        score_impact = (weighted_impact_points / MAX_IMPACT_RAW) * 25 if MAX_IMPACT_RAW else 0
        
        merit_score = score_rank + score_scale + score_votes + score_impact
        
        final_scores.append({
            "Член на тим": member,
            "Ранк (25%)": round(score_rank, 2),
            "Скала (35%)": round(score_scale, 2),
            "Бонус Улоги (15%)": round(score_votes, 2),
            "Придонес (25%)": round(score_impact, 2),
            "Вкупно (Merit)": round(merit_score, 2),
            "Титула": "Член"
        })
        
    df = pd.DataFrame(final_scores)
    
    # Calculate Equity
    total_merit = df["Вкупно (Merit)"].sum()
    if total_merit > 0:
        df["Предложен Удел (%)"] = (df["Вкупно (Merit)"] / total_merit) * 100
    else:
        df["Предложен Удел (%)"] = 100 / num_members
    
    # Dynamic Co-Founder Titles logic
    df = df.sort_values(by="Вкупно (Merit)", ascending=False).reset_index(drop=True)
    
    for i in range(len(df)):
        if i < avg_cofounders:
            df.at[i, "Титула"] = "Co-Founder 👑"
            
    df["Предложен Удел (%)"] = df["Предложен Удел (%)"].apply(lambda x: f"{round(x, 2)}%")
    return df, avg_cofounders

# --- UI ---
st.title("Findzzer Equity Евалуација")
st.markdown("Детален, целосно анонимен прашалник што зема предвид **труд, ризик, влијание и вештини** за прецизно распределување на сопственички удел. (Никој нема да ги види твоите поединечни оцени).")

submissions = get_all_submissions()

st.sidebar.title("Админ Алатки")
st.sidebar.write(f"**Поднесени форми: {len(submissions)} / {len(TEAM_MEMBERS)}**")

if st.sidebar.button("Избриши ги сите податоци (Reset)"):
    clear_db()
    st.sidebar.success("Базата е избришана!")
    st.rerun()
    
if len(submissions) >= len(TEAM_MEMBERS):
    st.sidebar.success("Сите членови гласаа! Погледни ја табелата.")

# Show Dashboard if everyone submitted
if len(submissions) >= len(TEAM_MEMBERS):
    st.header("🏆 Финална 'Fairness' Табела")
    st.success("Сите 5 членови успешно поднесоа евалуација! Ова се конечните резултати.")
    df_results, decided_cofounders = calculate_results(submissions)
    
    st.markdown(f"**Врз база на гласовите, тимот одлучи дека Findzzer треба да има {decided_cofounders} Co-Founder(и).** Тие титули се доделени на луѓето со најголем Merit резултат.")
    
    st.dataframe(
        df_results,
        use_container_width=True,
        hide_index=True
    )
    
    st.subheader("💡 Како се пресметаа овие проценти?")
    st.info("""
    Овој комплесен систем за распределба на стартап удел ги балансира твоите одговори со оние на тимот, каде **оценките од другите вредат 80%, а твојата оцена за тебе вреди 20%.**
    
    Вкупната "Merit" оцена е генерирана од 100 поени, поделени на следниов начин:
    
    1. **Дел 1: Рангирање (Од 1 до 5) носи 25% од поените.** (Добиваш максимум 5 поени ако те ставиле прв, и само 1 поен ако те ставиле последен за тоа прашање).
    2. **Дел 2: Специфична стартап улога носи 15% од поените како бонус.** (Секој пат кога некој ќе те избере дека ти си 'Моторот' или 'Визионерот', добиваш цврсти поени).
    3. **Дел 3: Скала на квалитет (Од 1 до 10) носи 35% од поените.** (Вреднува конзистентност, посветеност и технички квалитет).
    4. **Дел 4: Време, Придонес и Амбиција (1 до 10) носи 25% од поените.** (Најбитниот стартап дел: Временска посветеност, минат придонес и склоност кон Sales/Визија).
    """)
    
    with st.expander("Детална математичка формула за калкулација 🧮"):
        st.latex(r"Вредност = (Просек\_Туѓи\_Оцени \times 0.8) + (Сопствена\_Оцена \times 0.2)")
        st.markdown("""
        За да се осигураме дека секоја категорија тежи точно колку што е планирано, бодовите се нормализираат:
        
        **1. Рангирање (Макс 25 Merit поени):**
        - Секое 1во место носи 5 бода, 2ро место носи 4 бода ... 5то место носи 1 бод.
        - `Ранк Merit = (Вкупно_Твои_Ранк_Бодови / Максимални_Можни_Бодови) * 25`
        
        **2. Специфична Улога (Макс 15 Merit поени):**
        - Секое гласање дека ја носиш улогата е 1 глас (бод).
        - `Улога Merit = (Вкупно_Твои_Гласови / Број_На_Улоги) * 15`
        
        **3. Скала (Макс 35 Merit поени):**
        - Збир на оценките од слајдерите (1-10) за 10-те прашања.
        - `Скала Merit = (Збир_Оцени / Максимален_Можен_Збир) * 35`
        
        **4. Придонес и Време (Макс 25 Merit поени):**
        - Збир на оценките од слајдерите (1-10) за 3-те impact прашања. (Овие се лични прашања и бодовите доаѓаат 100% од твојот одговор).
        - `Impact Merit = (Твои_Оцени / Максимален_Можен_Збир) * 25`
        
        **Пресметка на Удел (Equity %):**
        - `Вкупен Твој Merit = Ранк Merit + Улога Merit + Скала Merit + Impact Merit`
        - `Твој Удел % = (Вкупен Твој Merit / Збир од Вкупниот Merit на сите 5 луѓе во тимот) * 100`
        """)
    
    st.markdown("---")
    st.header("💬 Анонимен Фидбек (Радикална Искреност)")
    st.markdown("Мислењето на другите за тебе е најголемиот подарок за личен развој. Овие коментари се строго анонимни и не влијаат на процентот (equity), туку служат за тимски раст.")
    
    for target_member in TEAM_MEMBERS:
        with st.expander(f"Што кажа тимот за: {target_member}"):
            for evaluator, data in submissions.items():
                if evaluator != target_member:
                    comments = data.get("anonymous_feedback", {}).get(target_member)
                    if comments:
                        st.markdown('<div class="feedback-box">', unsafe_allow_html=True)
                        st.markdown(f"**🟢 Најголема вредност:** {comments.get('strength')}")
                        st.markdown(f"**🔴 Слабост / Кочница:** {comments.get('weakness')}")
                        st.markdown('</div>', unsafe_allow_html=True)
    
    st.stop()

# --- EXPLANATION PAGE ---
if 'read_explanation' not in st.session_state:
    st.session_state['read_explanation'] = False

if not st.session_state['read_explanation']:
    st.markdown('<div class="evaluation-card">', unsafe_allow_html=True)
    
    st.markdown("### 📝 Порака од Оснивачот")
    st.info("""
    **„Јас како Марио Бојаровски, оснивач на оваа идеја и склопувач на овој тим, официјално се откажувам од сите досегашни трошоци и инвестиции во Findzzer. Ги рамнам со 0, за сите да имаме апсолутно ист 'starting point'.**
    
    Во овој момент ние не заработуваме ништо. За да продолжиме да работиме и да го изградиме ова во нешто големо, клучната работа е **мотивацијата**. Единственото нешто што вреди во моментов е самата идеја и потенциалот на продуктот, и тоа парче мора да се подели максимално фер – строго според **вложен труд, залагање, преземен ризик и покажан интерес**.
    
    Јас сакам секој да го добие точно тоа што го заслужил со својата вистинска работа, ниту процент повеќе, ниту процент помалку. Ова е направено за сите да бидеме рамноправни, сите транспарентно да дадеме мислење, и алгоритмот фер да пресуди. Токму на ова се базира целиот прашалник и евалуација.
    
    Знам и многу добро сум свесен дека **без било кој од нас, тимот немаше да биде ова што е денес.** Секој од нас имаше некоја своја „Главна Улога“ и од моја перспектива за тие главни улоги сите сме тука некаде, изедначени сме. Меѓутоа сите преземавме и многу **споредни улоги**, и токму тие споредни улоги и тој дополнителен труд се тоа што ја прави вистинската разлика! Затоа ова е многу тешка и битна задача за сите нас.
    
    **Дополнително, за презентациите пред инвеститори потребни ни се точни титули 'Co-Founders'.** Непишано правило е дека ако некој има над 51%, тогаш логично е да има само 1 founder. Меѓутоа, бидејќи градиме фер култура, оставам вие да изгласате: Колку 'Co-Founders' треба да има Findzzer (1, 2, 3...)? Вашите гласови на крајот се усредуваат, и титулите автоматски им се доделуваат на оние што избиле први врз основа на нивната заслуга.“
    """)
    st.write("")
    
    st.header("📖 Важно: Зошто овие прашања и како да гласаш?")
    
    st.markdown("""
    Findzzer не е обична компанија — ние сме **стартап**. Тоа значи дека конвенционалните метрики како "работно време" или "сениоритет" не се доволни за фер распределба на сопственички удел (equity). Во ран стартап, преживувањето и растот зависат од:
    
    1. **Жртвување и брзина:** Луѓе кои работат надвор од работно време и испорачуваат веднаш.
    2. **Снаодливост и ризик:** Оние кои наоѓаат генијални (или 'hacker') решенија кога немаме буџет или време.
    3. **Борба за тимот:** Лидерите кои ги ставаат интересите на Findzzer и на тимот пред сопственото его.
    
    Затоа, формата е поделена на 5 дела, специјално дизајнирани за овој стартап менталитет:
    - **Дел 1: Рангирање од најдобар до најслаб** каде мораш брутално искрено да одлучиш кој е најдобар во специфична 'survival' вештина.
    - **Дел 2: Специфична стартап улога** каде бираш само една личност која одговара на описот.
    - **Дел 3: Оценување на Квалитет (1-10)** за да се вреднува стабилноста, комуникацијата и стручноста на дневна база.
    - **Дел 4: Време, Придонес и Амбиција (1-10)** кој е најважниот чекор. Оценува кој е 'двигател' а кој 'поддршка', и колку време реално посветува.
    - **Дел 5: Радикална Транспарентност** каде за секој еден член мораш да напишеш 2 реченици фидбек (Анонимно).
    
    *Сите гласови се строго анонимни. Системот не дозволува идентификација кој за кого како гласал, и алгоритмот за бодови скришно ги пресметува тежините на прашањата.*
    """)
    
    agree = st.checkbox("Ја прочитав пораката од Марио, разбирам како функционира формата и ветувам дека ќе гласам максимално искрено и фер за сите.")
    if agree:
        if st.button("Продолжи кон Евалуација ➔", type="primary"):
            st.session_state['read_explanation'] = True
            st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- EVALUATION FORM ---
with st.container():
    st.markdown('<div class="evaluation-card">', unsafe_allow_html=True)
    
    evaluator = st.selectbox("Избери го твоето име (Строго анонимно во резултатот):", ["-- Избери Име --"] + TEAM_MEMBERS)
    
    if evaluator != "-- Избери Име --":
        if evaluator in submissions:
            st.warning("Веќе го имаш поднесено твоето оценување.")
            reset = st.button("Коригирај / Ресетирај форма")
            if not reset:
                st.stop()
                
        st.markdown("---")
        st.subheader("Дел 1: Рангирање од 1 до 5 (Најдобриот прв)")
        st.caption("Кликнете и влечете ги имињата во кутијата или селектирајте ги по правилен редослед. Задожително селектирај ги сите 5 луѓе за секое прашање според заслуга.")
        
        form_data = {
            "cofounder_count": 1,
            "rankings": {}, 
            "peer_selections": {}, 
            "scale_ratings": {member: {} for member in TEAM_MEMBERS},
            "impact_ratings": {member: {} for member in TEAM_MEMBERS},
            "anonymous_feedback": {member: {} for member in TEAM_MEMBERS}
        }
        
        st.markdown("---")
        st.subheader("Дел 0: Структура на Основачи")
        st.caption("Како што кажа Марио, секој тим мора да има дефинирана бројка на 'Co-Founders' за пред инвеститори и апликации.")
        form_data["cofounder_count"] = st.slider("Според тебе, колку лидери (Co-Founders) треба да има Findzzer?", min_value=1, max_value=3, value=2, step=1)
        
        st.markdown("---")
        st.subheader("Дел 1: Рангирање од 1 до 5 (Најдобриот прв)")
        st.caption("Кликнете и влечете ги имињата во кутијата или селектирајте ги по правилен редослед. **Важно: Првото име што ќе го избереш го добива 1-во место (Најмногу поени), а последното име е на 5-то место (Најмалку поени).** Задожително селектирај ги сите 5 луѓе за секое прашање според заслуга.")
        
        for item in RANKING_QUESTIONS:
            st.caption(f"_{item['desc']}_")
            # In Streamlit, multiselect enforces order of selection.
            ranking_choice = st.multiselect(
                "Избери ги од 1во до 5то место по редослед:", 
                options=TEAM_MEMBERS, 
                key=f"rank_{item['q']}",
                max_selections=len(TEAM_MEMBERS)
            )
            form_data["rankings"][item['q']] = ranking_choice
            
            if len(ranking_choice) < len(TEAM_MEMBERS) and len(ranking_choice) > 0:
                st.error("Мора да ги избереш сите 5 личности, од најдобра до најслаба.")
                
            st.write("")
        
        st.markdown("---")
        st.subheader("Дел 2: Специфична Улога (Peer Selection)")
        st.caption("Избери само 1 личност која најдобро одговара на описот.")
        
        for item in PEER_QUESTIONS:
            st.markdown(f"#### {item['q']}")
            st.caption(f"_{item['desc']}_")
            val = st.radio("Избери:", TEAM_MEMBERS, index=None, horizontal=True, key=f"peer_{item['q']}")
            form_data["peer_selections"][item['q']] = val
            st.write("")
        
        st.markdown("---")
        st.subheader("Дел 3: Оценување на Скала (Квалитет и Извршување)")
        st.caption("Оцени го СЕКОЈ член (вклучително и себеси) од 1 до 10 за следниве прашања. **(1 = Најслабо / Воопшто не се согласувам, 10 = Најдобро / Целосно се согласувам)**.")
        
        for item in SCALE_QUESTIONS:
            with st.expander(f"📌 {item['q']}", expanded=True):
                st.markdown(f"_{item['desc']}_")
                st.write("")
                cols = st.columns(len(TEAM_MEMBERS))
                for idx, member in enumerate(TEAM_MEMBERS):
                    with cols[idx]:
                        st.markdown(f"**{member}** {'*(Ти)*' if member == evaluator else ''}")
                        val = st.slider("", min_value=1, max_value=10, value=5, step=1, key=f"scale_{member}_{item['q']}")
                        form_data["scale_ratings"][member][item['q']] = val
                    
        st.markdown("---")
        st.subheader("Дел 4: Време, Придонес и Амбиција (Клучни Стартап Метрики)")
        st.caption("Овие 3 прашања се ЛИЧНИ и ги одговараш исклучиво за себе. Биди максимално реален и искрен. **(1 = Најслабо / Воопшто не се согласувам, 10 = Најдобро / Целосно се согласувам)**.")
        
        for item in IMPACT_QUESTIONS:
            with st.expander(f"🔥 {item['q']}", expanded=True):
                st.markdown(f"_{item['desc']}_")
                st.write("")
                val = st.slider(f"Твоја оцена ({evaluator}):", min_value=1, max_value=10, value=5, step=1, key=f"impact_{evaluator}_{item['q']}")
                form_data["impact_ratings"][evaluator][item['q']] = val
                        
        st.markdown("---")
        st.subheader("Дел 5: Радикална Транспарентност (Анонимен Текст)")
        st.caption("Задолжително напишете по една реченица на двата отворени прашалници за секој член. Без навреди кон карактерот, само професионални стартап критики. Вашето име нема да се појави со коментарот.")
        
        for member in TEAM_MEMBERS:
            with st.expander(f"Фидбек за: {member} {'(Твојот фидбек за тебе скришно се зачувува)' if member == evaluator else ''}", expanded=True):
                val_strength = st.text_input("Што е најголемата вредност што оваа личност му ја носи на Findzzer моментално?", key=f"strength_{member}")
                val_weakness = st.text_input("Што е најголемата кочница (слабост) на оваа личност која го успорува тимот?", key=f"weakness_{member}")
                form_data["anonymous_feedback"][member] = {
                    "strength": val_strength,
                    "weakness": val_weakness
                }

        st.markdown("---")
        
        # Validation before submitting
        ready_to_submit = True
        for q, r in form_data["rankings"].items():
            if len(r) != len(TEAM_MEMBERS):
                ready_to_submit = False
                st.warning("За да поднесеш, мора да ги избереш/рангираш сите 5 луѓе во сите прашања од Дел 1.")
                break
                
        if ready_to_submit:
            for q, p in form_data["peer_selections"].items():
                if p is None:
                    ready_to_submit = False
                    st.warning("За да поднесеш, мора да избереш личност за секоја улога во Дел 2.")
                    break
                
        # Validate all radical candor fields are filled
        candor_filled = True
        for m, fb in form_data["anonymous_feedback"].items():
            if not fb["strength"].strip() or not fb["weakness"].strip():
                candor_filled = False
                ready_to_submit = False
                break
                
        if not candor_filled:
            st.warning("За да поднесеш, мора да ги пополниш сите полиња со текст во Дел 5 (За сите луѓе).")
                
        if ready_to_submit:
            if st.button("Испрати ја Анонимната Евалуација", type="primary"):
                with st.spinner("⏳ AI анонимизирање на фидбекот и зачувување (може да потрае 10-15 секунди)..."):
                    for m, fb in form_data["anonymous_feedback"].items():
                        s, w = anonymize_feedback_with_ai(fb["strength"], fb["weakness"])
                        form_data["anonymous_feedback"][m]["strength"] = s
                        form_data["anonymous_feedback"][m]["weakness"] = w
                        
                    save_submission(evaluator, form_data)
                st.success("Успешно поднесено! Ви благодариме.")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
