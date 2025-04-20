from faker import Faker
import mysql.connector
import random

fake = Faker()

# Conexão com MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="recruitment_ai"
)

cursor = db.cursor()

# Gerar Vagas Fictícias
jobs = [
    ("Desenvolvedor Python", "Desenvolver aplicações web com Django e Flask", "Python, Django, SQL"),
    ("Analista de Dados", "Analisar dados com Python e SQL", "Python, SQL, Power BI"),
    ("Designer UI/UX", "Criar interfaces no Figma", "Figma, Adobe XD, Photoshop")
]

for job in jobs:
    cursor.execute("INSERT INTO jobs (title, description, required_skills) VALUES (%s, %s, %s)", job)

# Gerar Candidatos Fictícios
skills_pool = ["Python", "SQL", "Django", "Figma", "Power BI", "Photoshop", "Java", "React"]
for _ in range(50):
    name = fake.name()
    resume = fake.text(max_nb_chars=200)
    skills = ", ".join(random.sample(skills_pool, k=3))
    applied_jobs = ", ".join(random.sample([job[0] for job in jobs], k=2))
    
    cursor.execute(
        "INSERT INTO candidates (name, resume_text, skills, applied_jobs) VALUES (%s, %s, %s, %s)",
        (name, resume, skills, applied_jobs)
    )

db.commit()
cursor.close()
db.close()