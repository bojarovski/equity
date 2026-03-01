import sqlite3
import json
import random

DB_FILE = "evaluations.db"
TEAM_MEMBERS = ["Mario", "Matea", "Mila", "Angela", "Nikola"]

RANKING_QUESTIONS = [
    "Труд и жртвување",
    "Преземање ризици",
    "Борба за тимот",
    "Генерирање вредност",
    "Брзина и егзекуција",
    "Снаодливост",
    "Испорака под стрес (Resilience)",
    "Фокус на приоритети"
]

PEER_QUESTIONS = [
    "Мотор на тимот",
    "Оперативен/Технички столб",
    "Кризен менаџер",
    "Продукт Визионер",
    "Бизнис Двигател",
    "Тимски лепак",
    "Најголем напредок",
    "Најдоверлив лидер (Trust)"
]

SCALE_QUESTIONS = [
    "Посветеност (Commitment)",
    "Автономија",
    "Иновативност",
    "Доверливост",
    "Тежина на задачи",
    "Комуникација и транспарентност",
    "Незаменливост",
    "Потенцијал за скалирање",
    "Прифаќање критика (Coachability)",
    "Конзистентност во работата"
]

IMPACT_QUESTIONS = [
    "Тековна и Идна Временска Посветеност",
    "Двигател на стартапот (Driver vs Fixer)",
    "Досегашен мерлив придонес (Past Contribution)"
]

MOCK_STRENGTHS = [
    "Секогаш е тука кога најмногу гори.",
    "Пишува совршен код и брзо учи.",
    "Неверојатна енергија што ги мотивира сите.",
    "Многу добро ги разбира корисниците.",
    "Не се плаши да донесе тешка одлука."
]

MOCK_WEAKNESSES = [
    "Понекогаш не прифаќа туѓа критика.",
    "Работи премногу брзо и прави мали грешки.",
    "Треба да комуницира поотворено кога има проблем.",
    "Ја губи концентрацијата на помалку битни работи.",
    "Премногу се потпира на другите за фидбек."
]

def seed_data():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS submissions
                 (evaluator TEXT PRIMARY KEY, data TEXT)''')
    c.execute("DELETE FROM submissions") # Clear old data
    
    for evaluator in TEAM_MEMBERS:
        data = {
            "cofounder_count": random.randint(1, 3),
            "rankings": {},
            "peer_selections": {},
            "scale_ratings": {member: {} for member in TEAM_MEMBERS},
            "impact_ratings": {member: {} for member in TEAM_MEMBERS},
            "anonymous_feedback": {member: {} for member in TEAM_MEMBERS}
        }
        
        # Rankings (1 to 5)
        for q in RANKING_QUESTIONS:
            shuffled = list(TEAM_MEMBERS)
            random.shuffle(shuffled)
            data["rankings"][q] = shuffled
            
        # Peer
        for q in PEER_QUESTIONS:
            data["peer_selections"][q] = random.choice(TEAM_MEMBERS)
            
        # Scale & Impact & Feedback
        for member in TEAM_MEMBERS:
            for q in SCALE_QUESTIONS:
                if member == evaluator:
                    data["scale_ratings"][member][q] = random.randint(7, 10)
                else:
                    data["scale_ratings"][member][q] = random.randint(4, 10)
                    
            for q in IMPACT_QUESTIONS:
                if member == evaluator:
                    data["impact_ratings"][member][q] = random.randint(7, 10)
                else:
                    data["impact_ratings"][member][q] = random.randint(4, 10)
            
            # Anonymous Feedback
            data["anonymous_feedback"][member] = {
                "strength": random.choice(MOCK_STRENGTHS),
                "weakness": random.choice(MOCK_WEAKNESSES)
            }
                    
        c.execute("REPLACE INTO submissions (evaluator, data) VALUES (?, ?)", 
                  (evaluator, json.dumps(data)))
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed_data()
    print("Successfully seeded evaluations.db with 5 dummy submissions!")
