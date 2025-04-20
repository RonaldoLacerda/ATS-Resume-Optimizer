import json
import re
import random
import joblib
import mysql.connector
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Carrega configuração externalizada
with open("config.json", encoding="utf-8") as f:
    cfg = json.load(f)

# Configurações gerais
db_config = cfg["db_config"]
MIN_SAMPLES_FOR_RETRAIN = cfg.get("min_samples_for_retrain", 5)

class ATSOptimizer:
    def __init__(self):
        # Configurações dinâmicas
        self.stopwords = list(cfg["stopwords"])
        self.generic_terms = set(cfg["generic_terms"])
        self.universal_synonyms = cfg["universal_synonyms"]
        self.technical_weights = cfg["technical_weights"]
        self.vocabulary = set(cfg["technical_vocabulary"])
        
        # Componentes de ML e dados
        self.vectorizer = None
        self.jobs = []
        self.candidates = []
        
        # Controle de retrain
        self.last_training_count = 0
        self.min_samples_for_retrain = MIN_SAMPLES_FOR_RETRAIN

    def expand_synonyms(self, text):
        for term, synonyms in self.universal_synonyms.items():
            for syn in synonyms:
                text = re.sub(r'\b' + re.escape(syn) + r'\b', term, text)
        return text

    def check_and_retrain(self):
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs")
        current_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        if current_count >= self.last_training_count + self.min_samples_for_retrain:
            self.load_and_train()
            self.last_training_count = current_count

    def calculate_ats_score(self, similarity, missing_keywords):
        core_tech_penalty = sum(3 for kw in missing_keywords if kw in ['laravel', 'php'])
        secondary_tech_penalty = sum(2 for kw in missing_keywords if kw in ['docker', 'mysql'])
        workflow_penalty = sum(1 for kw in missing_keywords if kw in ['git', 'ci/cd'])
        total_penalty = core_tech_penalty + secondary_tech_penalty + workflow_penalty
        return max(30, round((similarity * 100) - total_penalty))

    def get_relevant_keywords(self, text):
        text = self.expand_synonyms(text.lower())
        keywords = re.findall(r'(?u)\b\w[\w\-\+\.]+' + r'\b', text)
        filtered = [
            kw for kw in keywords
            if kw not in self.stopwords
            and kw not in self.generic_terms
            and not kw.isnumeric()
            and len(kw) > 3
            and any(c.isalpha() for c in kw)
        ]
        return list(set(filtered))

    def sort_by_relevance(self, keywords, job_description):
        weights = []
        desc = job_description.lower()
        for kw in keywords:
            w = self.technical_weights.get(kw, 1) * desc.count(kw)
            if kw.isupper(): w *= 1.5
            if '-' in kw:     w *= 1.3
            weights.append((kw, w))
        return [kw for kw, _ in sorted(weights, key=lambda x: x[1], reverse=True)[:8]]

    def analyze_with_custom_job(self, job_title, job_description, resume_text):
        try:
            vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                token_pattern=r'(?u)\b\w[\w\-\+\.]+' + r'\b',
                stop_words=self.stopwords,
                vocabulary=self.vocabulary
            )

            doc_job = self.expand_synonyms(job_description.lower())
            doc_res = self.expand_synonyms(resume_text.lower())
            X = vectorizer.fit_transform([doc_job, doc_res])
            sim = cosine_similarity(X[0], X[1])[0][0]

            job_kws = self.get_relevant_keywords(job_description)
            res_kws = self.get_relevant_keywords(resume_text)
            missing = list(set(job_kws) - set(res_kws))

            return {
                "job_title": job_title,
                "similarity_score": round(sim * 100, 2),
                "missing_keywords": self.sort_by_relevance(missing, job_description)[:5],
                "ats_score": self.calculate_ats_score(sim, missing),
                "dynamic_suggestions": self.generate_dynamic_suggestions(
                    missing_keywords=missing,
                    similarity_score=sim * 100,
                    resume_text=resume_text,
                    job_description=job_description
                )
            }
        except Exception as e:
            print(f"Erro na análise: {e}")
            return None

    def generate_dynamic_suggestions(self, missing_keywords, similarity_score, resume_text, job_description):
        suggestions = []
        # 1. Mapeamento ampliado de conselhos técnicos
        keyword_advice = {
            'docker': {
                'icon': 'fab fa-docker',
                'text': 'Experiência com Docker',
                'tooltip': 'Mencione orquestração de containers e otimizações',
                'example': random.choice([
                    'Orquestração de 15+ containers com Docker Swarm em ambiente cloud',
                    'Otimização de imagens Docker reduzindo tamanho em 60%',
                    'Implementação de CI/CD com Docker e Jenkins'
                ]),
                'priority': 4
            },
            'laravel': {
                'icon': 'fab fa-laravel',
                'text': 'Especificação do Laravel',
                'tooltip': 'Detalhe versões e componentes utilizados',
                'example': random.choice([
                    'Desenvolvimento de API RESTful com Laravel 10 utilizando Sanctum',
                    'Implementação de sistema de filas com Redis e Horizon',
                    'Migração de Laravel 8 para 10 com atualização de PHP'
                ]),
                'priority': 5
            },
            'react': {
                'icon': 'fab fa-react',
                'text': 'Projetos com React',
                'tooltip': 'Descreva componentes complexos e integrações',
                'example': random.choice([
                    'Criação de SPA com React 18 utilizando Redux Toolkit',
                    'Implementação de testes E2E com Cypress em componentes React',
                    'Otimização de renderização com memoization e virtualização'
                ]),
                'priority': 4
            },
            'mysql': {
                'icon': 'fas fa-database',
                'text': 'Otimização de Bancos',
                'tooltip': 'Mostre experiência em tuning de queries',
                'example': random.choice([
                    'Redução de 70% no tempo de query com indexação estratégica',
                    'Implementação de replicação Master-Slave para alta disponibilidade',
                    'Migração de schema com zero downtime para tabelas de 50GB+'
                ]),
                'priority': 3
            }
        }

        # 2. Sugestões contextuais baseadas no título da vaga
        job_title_keywords = {
            'php': [
                "Implementação de middlewares customizados em PHP",
                "Integração com serviços SOAP/XML",
                "Otimização de performance com OPcache"
            ],
            'react': [
                "Gerenciamento de estado global com Context API",
                "Implementação de SSR com Next.js",
                "Integração com bibliotecas de visualização de dados"
            ],
            'fullstack': [
                "Arquitetura de microfrontends",
                "Configuração de ambientes Docker multi-camadas",
                "Implementação de testes de integração E2E"
            ]
        }

        # 3. Contexto industrial e de domínio
        job_context = {
            'industrias': {
                'varejo': [
                    "Desenvolvimento de sistemas de inventário em tempo real",
                    "Integração com gateways de pagamento (PagSeguro, MercadoPago)"
                ],
                'banco': [
                    "Implementação de APIs seguras para transações PIX",
                    "Conformidade com regulamentações financeiras (LGPD, PCI-DSS)"
                ]
            },
            'nivel': {
                'sênior': [
                    "Liderança técnica de squads multidisciplinares",
                    "Tomada de decisão arquitetural em sistemas críticos"
                ],
                'pleno': [
                    "Desenvolvimento de features complexas de forma independente",
                    "Refatoração de código legado com abordagem incremental"
                ]
            }
        }

        # 4. Análise de termos genéricos
        generic_replacements = {
            'ajustes': [
                "Otimização de queries SQL complexas",
                "Refatoração de código para padrões PSR-12",
                "Migração de versão do PHP com compatibilidade retroativa"
            ],
            'melhorias': [
                "Redução de 40% no consumo de memória",
                "Aumento de throughput em APIs REST",
                "Implementação de sistema de cache distribuído"
            ],
            'sistema': [
                "Arquitetura de microserviços escaláveis",
                "Plataforma de e-commerce distribuída",
                "Solução de gestão logística integrada"
            ]
        }

        # 5. Sugestões baseadas no conteúdo do texto
        for term, phrases in job_title_keywords.items():
            if term in job_description.lower():
                suggestions.append({
                    'icon': 'fas fa-bullseye',
                    'text': f'Destaque {term.upper()} no contexto',
                    'tooltip': f'Relevante para a posição de {term.upper()}',
                    'example': random.choice(phrases),
                    'priority': 4
                })

        # 6. Substituição de termos genéricos dinâmicos
        for term, replacements in generic_replacements.items():
            if term in resume_text.lower():
                suggestions.append({
                    'icon': 'fas fa-sync-alt',
                    'text': f'Substituir "{term}" por:',
                    'tooltip': 'Use termos técnicos específicos',
                    'example': random.choice(replacements),
                    'priority': 3
                })

        # 7. Sugestões de contexto industrial
        for industry, tips in job_context['industrias'].items():
            if industry in job_description.lower():
                suggestions.append({
                    'icon': 'fas fa-industry',
                    'text': f'Experiência em {industry.capitalize()}',
                    'tooltip': 'Contextualize com desafios do setor',
                    'example': random.choice(tips),
                    'priority': 2
                })

        # 8. Sugestões de nível de experiência
        for level, tips in job_context['nivel'].items():
            if level in job_description.lower():
                suggestions.append({
                    'icon': 'fas fa-user-tie',
                    'text': f'Habilidades para {level.capitalize()}',
                    'tooltip': 'Demonstre maturidade técnica',
                    'example': random.choice(tips),
                    'priority': 3
                })

        # 9. Métricas quantificáveis
        metrics_examples = [
            "Aumento de 150% no throughput de API",
            "Redução de 65% no tempo de execução de queries",
            "Implementação de 300+ cases de teste automatizados"
        ]
        if len(re.findall(r'\d+[\+\%]?', resume_text)) < 4:
            suggestions.append({
                'icon': 'fas fa-chart-line',
                'text': 'Adicione métricas impactantes',
                'tooltip': 'Quantifique resultados e conquistas',
                'example': random.choice(metrics_examples),
                'priority': 3
            })

        # 10. Arquitetura e padrões
        architecture_keywords = {
            'microserviços': "Implementação de comunicação assíncrona com RabbitMQ",
            'serverless': "Desenvolvimento de funções AWS Lambda com Node.js",
            'monolito': "Refatoração modular de sistema legado"
        }
        for kw, example in architecture_keywords.items():
            if kw in job_description.lower():
                suggestions.append({
                    'icon': 'fas fa-project-diagram',
                    'text': f'Arquitetura {kw.capitalize()}',
                    'tooltip': 'Demonstre habilidades de design arquitetural',
                    'example': example,
                    'priority': 4
                })

        # 11. Sugestões para keywords faltantes
        for keyword in missing_keywords:
            lower_key = keyword.lower()
            if lower_key in keyword_advice:
                suggestions.append(keyword_advice[lower_key])
            else:
                suggestions.append({
                    'icon': 'fas fa-exclamation-circle',
                    'text': f'Adicione referências a: {keyword}',
                    'tooltip': 'Contextualize com experiências específicas',
                    'example': f'Implementação de solução {keyword} para...',
                    'priority': 2
                })

        # 12. Estrutura do currículo
        sections = {
            'habilidades': ["Linguagens: PHP 8.1, Python", "Frameworks: Laravel, Django"],
            'projetos': ["Sistema de gestão de pedidos", "Plataforma de análise de dados"],
            'certificações': ["AWS Certified Developer", "Scrum Master Certified"]
        }
        for section, examples in sections.items():
            if section not in resume_text.lower():
                suggestions.append({
                    'icon': 'fas fa-file-alt',
                    'text': f'Seção de {section.capitalize()}',
                    'tooltip': 'Organize informações chave',
                    'example': random.choice(examples),
                    'priority': 2
                })

        # 13. Priorização e desduplicação
        unique = {}
        for s in suggestions:
            key = s['text']
            if key not in unique or s['priority'] > unique[key]['priority']:
                unique[key] = s

        return sorted(unique.values(), key=lambda x: (-x['priority'], x['text']))[:7]

    def load_data(self):
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT title, required_skills, description FROM jobs")
        self.jobs = cursor.fetchall()
        cursor.execute("SELECT id, resume_text, skills FROM candidates")
        self.candidates = cursor.fetchall()
        cursor.close()
        conn.close()

    def train_model(self):
        texts = [f"{j[1]} {j[2]}" for j in self.jobs]
        self.vectorizer = TfidfVectorizer(stop_words=self.stopwords)
        self.vectorizer.fit(texts)

    def load_and_train(self):
        self.load_data()
        self.train_model()
        joblib.dump((self.vectorizer, self.jobs), "modelo_treinado.pkl")

    def load_pretrained_model(self):
        self.vectorizer, self.jobs = joblib.load("modelo_treinado.pkl")

    def analyze_uploaded_resume(self, job_title, resume_text):
        try:
            job = next(j for j in self.jobs if j[0].lower() == job_title.lower().strip())
            target = f"{job[1]} {job[2]}"
            X = self.vectorizer.transform([resume_text, target])
            sim = cosine_similarity(X[0], X[1])[0][0]
            kws_job = re.findall(r'\b\w+\b', target.lower())
            kws_res = re.findall(r'\b\w+\b', resume_text.lower())
            missing = list(set(kws_job) - set(kws_res))
            return {
                "similarity_score": round(sim * 100, 2),
                "missing_keywords": missing[:5],
                "ats_score": min(100, int(sim * 100 + len(missing) * 5))
            }
        except StopIteration:
            return None
        except Exception as e:
            print(f"Erro na análise: {e}")
            return None

    def optimize_resume(self, candidate_id, target_job_title):
        try:
            job = next(j for j in self.jobs if j[0] == target_job_title)
            target = f"{job[1]} {job[2]}"
            cand = next(c for c in self.candidates if c[0] == candidate_id)
            resume_text = f"{cand[1]} {cand[2]}"
            X = self.vectorizer.transform([resume_text, target])
            sim = cosine_similarity(X[0], X[1])[0][0]
            kws_job = re.findall(r'\b\w+\b', target.lower())
            kws_res = re.findall(r'\b\w+\b', resume_text.lower())
            missing = list(set(kws_job) - set(kws_res))
            return {
                "similarity_score": round(sim * 100, 2),
                "missing_keywords": missing[:5],
                "ats_score": min(100, int(sim * 100 + len(missing) * 5))
            }
        except StopIteration:
            return None
        except Exception as e:
            print(f"Erro na otimização: {e}")
            return None
