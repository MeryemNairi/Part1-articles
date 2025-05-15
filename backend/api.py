from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
import re
import uuid
import json
import requests
from fastapi.responses import FileResponse
import io
import base64
from PIL import Image
import traceback
import random
import tempfile
import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
from starlette.background import BackgroundTask
from bs4 import BeautifulSoup

# Importation conditionnelle des bibliothèques LLM
try:
    # Essayer les importations pour les versions récentes
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    LLM_AVAILABLE = True
except ImportError:
    try:
        # Essayer les importations pour les versions plus anciennes
        from langchain.chat_models import ChatOpenAI
        from langchain.schema import HumanMessage
        LLM_AVAILABLE = True
    except ImportError:
        print("Erreur: Impossible d'importer les modules langchain nécessaires")
        raise

# Chargement des variables d'environnement
load_dotenv()

# Récupération de la clé API depuis les variables d'environnement
api_key = os.getenv("OPENAI_API_KEY", "")
model = "gpt-3.5-turbo"  # Modèle par défaut

app = FastAPI()

# Configuration CORS pour permettre les requêtes depuis votre frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Ajoutez toutes les URL possibles de votre frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TitleRequest(BaseModel):
    sujet: str
    tone: str = "standard"
    additional_context: str = ""
    avoid_context: str = ""

class TitleResponse(BaseModel):
    titles: List[str]
    title_ids: Dict[str, str]

class RegenerateRequest(BaseModel):
    index: int
    sujet: str
    tone: str
    titres: List[str]

class ArticleRequest(BaseModel):
    titre: str
    sujet: str
    additional_context: str = ""
    avoid_context: str = ""

class ArticleResponse(BaseModel):
    content: str

class ThemeAnalysisRequest(BaseModel):
    theme: str

# Fonction pour générer des titres
def generate_titles_with_llm(sujet: str, tone: str, additional_context: str, avoid_context: str) -> List[str]:
    """Génère des titres en utilisant le modèle de langage."""
    if not api_key:
        raise ValueError("Clé API OpenAI non configurée")
    
    try:
        llm = ChatOpenAI(api_key=api_key, model_name=model, temperature=0.7)
        
        context_info = ""
        if additional_context:
            context_info += f"\nÉléments à inclure: {additional_context}"
        if avoid_context:
            context_info += f"\nÉléments à éviter: {avoid_context}"
        
        prompt = f"""
        Génère 5 titres d'articles différents sur le sujet: {sujet}.
        Ton: {tone}
        {context_info}
        
        Les titres doivent être:
        - Accrocheurs et attrayants
        - Pertinents pour le sujet
        - Uniques et variés entre eux
        - Entre 5 et 12 mots
        - Optimisés pour le référencement
        
        Retourne uniquement les 5 titres, un par ligne, sans numérotation ni formatage supplémentaire.
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        
        # Extraction des titres
        titles = [line.strip() for line in response.content.split('\n') if line.strip()]
        
        # S'assurer qu'on a exactement 5 titres
        while len(titles) < 5:
            titles.append(f"Article sur {sujet} - {len(titles) + 1}")
        
        return titles[:5]
    except Exception as e:
        print(f"Erreur lors de la génération des titres avec LLM: {str(e)}")
        raise

# Fonction pour régénérer un titre spécifique
def regenerer_titre(index: int, sujet: str, tone: str, titres: List[str]) -> str:
    llm = ChatOpenAI(openai_api_key=api_key, model=model)
    
    # Création de l'agent spécialisé
    agent_titres = Agent(
        role="Expert en Rédaction de Titres",
        goal="Créer un titre d'article captivant et optimisé pour le SEO",
        backstory="""Je suis un rédacteur professionnel avec 15 ans d'expérience dans la création
                  de titres qui génèrent des clics tout en restant informatifs et pertinents.""",
        verbose=True,
        llm=llm
    )
    
    # Adaptation du ton selon le choix de l'utilisateur
    tone_instructions = {
        "standard": "équilibré entre information et attractivité",
        "professionnel": "formel, sérieux et adapté à un public professionnel",
        "créatif": "original, avec des jeux de mots ou des formulations surprenantes",
        "accrocheur": "conçu pour maximiser les clics et l'engagement",
        "informatif": "clair, précis et axé sur l'information"
    }
    
    # Définition de la tâche
    tache_regeneration = Task(
        description=f"""
        En fonction du sujet général suivant: "{sujet}", 
        génère UN SEUL titre d'article qui est {tone_instructions[tone]}.
        
        Le titre doit être:
        1. Pertinent par rapport au sujet principal
        2. Optimisé pour le référencement
        3. De longueur appropriée (60-70 caractères idéalement)
        4. Différent des titres suivants:
        {', '.join([f'"{t}"' for t in titres])}
        
        Retourne uniquement le titre, sans numérotation ni autre texte.
        """,
        expected_output="Un titre d'article unique",
        agent=agent_titres
    )
    
    # Création et exécution de l'équipage
    crew = Crew(
        agents=[agent_titres],
        tasks=[tache_regeneration],
        verbose=True
    )
    
    # Exécution et récupération du résultat
    resultat = crew.kickoff()
    
    # Nettoyage du résultat
    nouveau_titre = str(resultat).strip()
    # Supprimer les numéros ou puces éventuels
    nouveau_titre = re.sub(r'^[\d\.\-\*]+\s*', '', nouveau_titre)
    # Supprimer les guillemets éventuels
    nouveau_titre = nouveau_titre.strip('"\'')
    
    return nouveau_titre

# Fonction pour générer un article complet
def generate_article_with_llm(titre: str, sujet: str, additional_context: str, avoid_context: str) -> str:
    """Génère un article en utilisant le modèle de langage."""
    if not api_key:
        raise ValueError("Clé API OpenAI non configurée")
    
    try:
        llm = ChatOpenAI(api_key=api_key, model_name=model, temperature=0.7)
        
        context_info = ""
        if additional_context:
            context_info += f"\nÉléments à inclure: {additional_context}"
        if avoid_context:
            context_info += f"\nÉléments à éviter: {avoid_context}"
        
        prompt = f"""
        Rédige un article complet avec le titre: "{titre}" sur le sujet: {sujet}.
        {context_info}
        
        L'article doit:
        - Être bien structuré avec une introduction, des sections et une conclusion
        - Inclure des sous-titres pertinents
        - Être informatif et factuel
        - Être engageant et facile à lire
        - Inclure des exemples concrets
        
        Format: Markdown
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        print(f"Erreur lors de la génération de l'article avec LLM: {str(e)}")
        raise

@app.post("/api/titles", response_model=TitleResponse)
async def create_titles(request: TitleRequest):
    try:
        print(f"Requête reçue pour le sujet: {request.sujet}")
        
        if LLM_AVAILABLE and api_key:
            try:
                # Essayer d'utiliser le LLM
                titles = generate_titles_with_llm(
                    request.sujet, 
                    request.tone,
                    request.additional_context,
                    request.avoid_context
                )
                print(f"Titres générés avec LLM: {titles}")
            except Exception as e:
                print(f"Échec de la génération avec LLM: {str(e)}")
                # Fallback vers des titres statiques
                titles = [
                    f"Comment {request.sujet} transforme notre quotidien",
                    f"Les 5 aspects essentiels de {request.sujet} à connaître",
                    f"Pourquoi {request.sujet} est important aujourd'hui",
                    f"{request.sujet}: guide complet pour les débutants",
                    f"L'avenir de {request.sujet}: tendances et prédictions"
                ]
        else:
            # Utiliser des titres statiques si LLM n'est pas disponible
            titles = [
                f"Comment {request.sujet} transforme notre quotidien",
                f"Les 5 aspects essentiels de {request.sujet} à connaître",
                f"Pourquoi {request.sujet} est important aujourd'hui",
                f"{request.sujet}: guide complet pour les débutants",
                f"L'avenir de {request.sujet}: tendances et prédictions"
            ]
        
        title_ids = {title: str(i) for i, title in enumerate(titles)}
        return {"titles": titles, "title_ids": title_ids}
    except Exception as e:
        print(f"Erreur lors de la génération des titres: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/regenerate-title", response_model=dict)
async def regenerate_title(request: RegenerateRequest):
    if not api_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    
    try:
        new_title = regenerer_titre(request.index, request.sujet, request.tone, request.titres)
        return {"title": new_title, "id": str(uuid.uuid4())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/article")
async def generate_article(request: dict = Body(...)):
    try:
        print(f"Requête reçue pour générer un article")
        titre = request.get("titre", "")
        sujet = request.get("sujet", "")
        
        # Effectuer le scraping web avec une approche plus robuste
        web_content = ""
        sources = []
        
        try:
            print(f"Tentative de scraping pour: {sujet} - {titre}")
            
            # Code de scraping intégré directement
            query = f"{sujet} {titre}"
            print(f"Requête de recherche: {query}")
            
            # Utiliser une approche plus simple avec requests
            serp_api_key = "f4dc513226b4b703cdc98a18c2d325a559dcccd3b2e73da115045fe22a152af0"
            search_url = f"https://serpapi.com/search.json?q={query.replace(' ', '+')}&api_key={serp_api_key}&engine=google&num=5"
            print(f"URL de recherche: {search_url}")
            
            # Vérifier la connectivité Internet avant d'envoyer la requête
            try:
                test_connection = requests.get("https://www.google.com", timeout=5)
                print(f"Test de connexion Internet: {test_connection.status_code}")
            except Exception as e:
                print(f"Erreur lors du test de connexion Internet: {str(e)}")
            
            # Envoyer la requête à SERP API avec un timeout plus long
            response = requests.get(search_url, timeout=30)
            print(f"Réponse SERP API reçue: status code {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Extraire les résultats organiques
                organic_results = data.get("organic_results", [])
                print(f"Nombre de résultats organiques: {len(organic_results)}")
                
                if organic_results:
                    for i, result in enumerate(organic_results[:3]):
                        title = result.get("title", "")
                        snippet = result.get("snippet", "")
                        link = result.get("link", "")
                        
                        print(f"Résultat {i+1}: {title} - {link}")
                        web_content += f"## {title}\n\n{snippet}\n\n"
                        sources.append(f"{title} - {link}")
                        
                        # Essayer de récupérer plus de contenu en visitant la page
                        try:
                            print(f"Tentative d'extraction de contenu supplémentaire depuis: {link}")
                            page_response = requests.get(link, timeout=10, headers={
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                            })
                            
                            if page_response.status_code == 200:
                                # Extraire le texte principal de la page
                                soup = BeautifulSoup(page_response.text, 'html.parser')
                                
                                # Supprimer les scripts, styles et balises non pertinentes
                                for script in soup(["script", "style", "header", "footer", "nav"]):
                                    script.extract()
                                
                                # Extraire le texte
                                page_text = soup.get_text(separator=' ', strip=True)
                                
                                # Nettoyer le texte
                                page_text = re.sub(r'\s+', ' ', page_text).strip()
                                
                                # Limiter la taille du texte extrait
                                if len(page_text) > 1500:
                                    page_text = page_text[:1500] + "..."
                                
                                web_content += f"\nContenu supplémentaire de {title}:\n{page_text}\n\n"
                                print(f"Contenu supplémentaire extrait: {len(page_text)} caractères")
                        except Exception as e:
                            print(f"Erreur lors de l'extraction de contenu supplémentaire: {str(e)}")
                    
                    print(f"Contenu web total récupéré: {len(web_content)} caractères")
                    print(f"Sources trouvées: {len(sources)}")
                else:
                    print("Aucun résultat organique trouvé")
            else:
                print(f"Erreur API SERP: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Erreur lors du scraping: {str(e)}")
            traceback.print_exc()
        
        # Si aucun contenu n'a été trouvé, utiliser un message par défaut
        if not web_content:
            web_content = f"Aucune information spécifique trouvée sur '{titre}'. Génération d'un article basé sur les connaissances générales."
            print("Utilisation du contenu par défaut")
        
        # Générer l'article avec le contenu web
        llm = ChatOpenAI(api_key=api_key, model_name=model, temperature=0.7)
        
        # Inclure les sources dans le prompt
        sources_text = "\n".join([f"- {source}" for source in sources]) if sources else "Aucune source spécifique disponible"
        
        prompt = f"""
        Tu es un expert en rédaction d'articles.
        
        Rédige un article complet et détaillé sur "{titre}".
        
        Utilise ces informations comme base pour ton article:
        {web_content}
        
        Sources d'information:
        {sources_text}
        
        L'article doit:
        - Avoir une introduction captivante
        - Contenir au moins 3 sections principales avec sous-titres
        - Inclure des exemples concrets
        - Se terminer par une conclusion
        - Citer les sources d'information quand c'est pertinent
        
        Format: Markdown avec des sections et sous-sections.
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content
        
        # Ne pas ajouter les sources à la fin de l'article, mais les renvoyer séparément
        print(f"Article généré avec succès pour: {titre}")
        return {"content": content, "sources": sources}
    except Exception as e:
        print(f"Erreur lors de la génération de l'article: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-image")
async def generate_image(request: dict = Body(...)):
    try:
        print(f"Requête reçue pour générer une image")
        prompt = request.get("prompt", "")
        
        # Essayer d'utiliser l'API fal.ai si la clé est disponible
        fal_api_key = os.getenv("FAL_API_KEY", "")
        if fal_api_key:
            try:
                # Vérifier la connectivité Internet
                test_connection = requests.get("https://www.google.com", timeout=5)
                if test_connection.status_code == 200:
                    print("Connexion Internet fonctionnelle, tentative d'accès à fal.ai...")
                    
                    headers = {
                        "Authorization": f"Key {fal_api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    payload = {
                        "prompt": prompt or "A beautiful cat in a garden",
                        "negative_prompt": "low quality, blurry, distorted, deformed",
                        "height": 768,
                        "width": 1024,
                        "num_images": 1
                    }
                    
                    # Utiliser un timeout plus court pour éviter de bloquer trop longtemps
                    response = requests.post(
                        "https://api.fal.ai/v1/stable-diffusion/sdxl",
                        headers=headers,
                        json=payload,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        image_url = data.get("images", [{}])[0].get("url", "")
                        print(f"Image générée avec fal.ai: {image_url}")
                        return {"image_url": image_url}
                    else:
                        print(f"Erreur fal.ai: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                print(f"Échec de la connexion à fal.ai: {str(e)}")
                traceback.print_exc()
        
        # Utiliser des URLs d'images plus fiables comme fallback
        fallback_images = [
            "https://images.unsplash.com/photo-1518791841217-8f162f1e1131",
            "https://images.unsplash.com/photo-1583337130417-3346a1be7dee",
            "https://images.unsplash.com/photo-1573865526739-10659fec78a5",
            "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba",
            "https://images.unsplash.com/photo-1495360010541-f48722b34f7d"
        ]
        image_url = random.choice(fallback_images)
        print(f"URL d'image de secours utilisée: {image_url}")
        return {"image_url": image_url}
    except Exception as e:
        print(f"Erreur lors de la génération de l'image: {str(e)}")
        traceback.print_exc()
        # Utiliser une image SVG intégrée comme fallback
        svg_image = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='600' viewBox='0 0 800 600'%3E%3Crect width='800' height='600' fill='%23f0f0f0'/%3E%3Ctext x='400' y='300' font-family='Arial' font-size='24' text-anchor='middle' fill='%23666666'%3EImage générée%3C/text%3E%3C/svg%3E"
        print(f"URL d'image SVG utilisée")
        return {"image_url": svg_image}

@app.post("/api/export-json")
async def export_json(request: dict = Body(...)):
    try:
        print("Requête reçue pour exporter en JSON")
        return {"success": True, "data": request.get("article_data", {})}
    except Exception as e:
        print(f"Erreur lors de l'exportation JSON: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/export-pdf")
async def export_pdf(request: dict = Body(...)):
    try:
        print("Requête reçue pour exporter en PDF")
        return {"success": True}
    except Exception as e:
        print(f"Erreur lors de l'exportation PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/translate")
async def translate_content(request: dict = Body(...)):
    try:
        print(f"Requête de traduction reçue")
        content = request.get("content", "")
        target_language = request.get("target_language", "fr")
        
        if not api_key:
            print("Clé API OpenAI non configurée, utilisation du fallback")
            # Fallback simple pour les tests
            if target_language == "ar":
                return {"translated_content": "هذا هو النص المترجم. هذا مجرد نص للاختبار."}
            elif target_language == "en":
                return {"translated_content": "This is the translated text. This is just a test text."}
            else:  # fr
                return {"translated_content": "Voici le texte traduit. Ceci est juste un texte de test."}
        
        try:
            llm = ChatOpenAI(api_key=api_key, model_name=model, temperature=0.3)
            
            language_name = ""
            if target_language == "ar":
                language_name = "arabe"
            elif target_language == "en":
                language_name = "anglais"
            else:  # fr
                language_name = "français"
            
            prompt = f"""
            Traduis le texte suivant en {language_name}. 
            Conserve le formatage Markdown, les titres, les listes et tous les éléments de mise en forme.
            
            Texte à traduire:
            {content}
            """
            
            response = llm.invoke([HumanMessage(content=prompt)])
            translated_content = response.content
            
            print(f"Traduction réussie vers {target_language}")
            return {"translated_content": translated_content}
        except Exception as e:
            print(f"Erreur lors de la traduction avec LLM: {str(e)}")
            traceback.print_exc()
            
            # Fallback: texte simple indiquant l'échec de traduction
            if target_language == "ar":
                return {"translated_content": "عذرًا، فشلت الترجمة. يرجى المحاولة مرة أخرى لاحقًا."}
            elif target_language == "en":
                return {"translated_content": "Sorry, translation failed. Please try again later."}
            else:  # fr
                return {"translated_content": "Désolé, la traduction a échoué. Veuillez réessayer plus tard."}
    except Exception as e:
        print(f"Erreur lors de la traduction: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-website-theme")
async def generate_website_theme(request: dict = Body(...)):
    try:
        print(f"Requête reçue pour générer un thème de site web")
        theme = request.get("theme", "")
        number_of_variations = request.get("variations", 3)
        
        if not api_key:
            # Fallback pour les tests
            variations = [
                {
                    "id": "var1",
                    "title": f"{theme} - Version Professionnelle",
                    "description": f"Un site web professionnel sur {theme} avec une approche business.",
                    "style": "Professionnel et épuré"
                },
                {
                    "id": "var2",
                    "title": f"{theme} - Version Créative",
                    "description": f"Un site web créatif sur {theme} avec un design unique.",
                    "style": "Créatif et coloré"
                },
                {
                    "id": "var3",
                    "title": f"{theme} - Version Minimaliste",
                    "description": f"Un site web minimaliste sur {theme} avec un design simple.",
                    "style": "Minimaliste et élégant"
                }
            ]
            
            return {"variations": variations[:number_of_variations]}
        
        try:
            llm = ChatOpenAI(api_key=api_key, model_name=model, temperature=0.7)
            
            prompt = f"""
            Génère {number_of_variations} variations de thèmes de sites web basés sur le sujet principal: "{theme}".
            
            Pour chaque variation, fournis:
            1. Un titre unique
            2. Une brève description (1-2 phrases)
            3. Un style visuel suggéré
            
            Les variations doivent être différentes les unes des autres et explorer différentes approches du même thème.
            
            Format de réponse: JSON
            [
                {{
                    "title": "Titre de la variation",
                    "description": "Description de la variation",
                    "style": "Style visuel suggéré"
                }},
                ...
            ]
            """
            
            response = llm.invoke([HumanMessage(content=prompt)])
            
            # Extraire le JSON de la réponse
            import json
            import re
            
            # Rechercher un bloc JSON dans la réponse
            json_match = re.search(r'\[[\s\S]*\]', response.content)
            if json_match:
                json_str = json_match.group(0)
                variations_data = json.loads(json_str)
                
                # Ajouter des IDs aux variations
                variations = []
                for i, var in enumerate(variations_data):
                    variations.append({
                        "id": f"var{i+1}",
                        "title": var.get("title", f"{theme} - Variation {i+1}"),
                        "description": var.get("description", f"Une variation de site web sur {theme}."),
                        "style": var.get("style", "Style standard")
                    })
                
                return {"variations": variations[:number_of_variations]}
            else:
                # Fallback si le format JSON n'est pas détecté
                variations = [
                    {
                        "id": "var1",
                        "title": f"{theme} - Version Professionnelle",
                        "description": f"Un site web professionnel sur {theme} avec une approche business.",
                        "style": "Professionnel et épuré"
                    },
                    {
                        "id": "var2",
                        "title": f"{theme} - Version Créative",
                        "description": f"Un site web créatif sur {theme} avec un design unique.",
                        "style": "Créatif et coloré"
                    },
                    {
                        "id": "var3",
                        "title": f"{theme} - Version Minimaliste",
                        "description": f"Un site web minimaliste sur {theme} avec un design simple.",
                        "style": "Minimaliste et élégant"
                    }
                ]
                
                return {"variations": variations[:number_of_variations]}
        except Exception as e:
            print(f"Erreur lors de la génération des variations avec LLM: {str(e)}")
            traceback.print_exc()
            
            # Fallback en cas d'erreur
            variations = [
                {
                    "id": "var1",
                    "title": f"{theme} - Version Professionnelle",
                    "description": f"Un site web professionnel sur {theme} avec une approche business.",
                    "style": "Professionnel et épuré"
                },
                {
                    "id": "var2",
                    "title": f"{theme} - Version Créative",
                    "description": f"Un site web créatif sur {theme} avec un design unique.",
                    "style": "Créatif et coloré"
                },
                {
                    "id": "var3",
                    "title": f"{theme} - Version Minimaliste",
                    "description": f"Un site web minimaliste sur {theme} avec un design simple.",
                    "style": "Minimaliste et élégant"
                }
            ]
            
            return {"variations": variations[:number_of_variations]}
    except Exception as e:
        print(f"Erreur lors de la génération des variations de thème: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-logos")
async def generate_logos(request: dict = Body(...)):
    try:
        print(f"Requête reçue pour générer des logos")
        variations = request.get("variations", [])
        logo_descriptions = request.get("logo_descriptions", {})
        
        # Vérifier si fal.ai est disponible
        fal_api_key = os.getenv("FAL_API_KEY", "")
        
        # Résultats à retourner
        results = []
        
        for variation in variations:
            var_id = variation.get("id", "")
            title = variation.get("title", "")
            description = variation.get("description", "")
            style = variation.get("style", "")
            
            # Obtenir la description du logo si fournie, sinon en générer une
            logo_prompt = logo_descriptions.get(var_id, "")
            if not logo_prompt:
                # Générer une description de logo basée sur le thème
                logo_prompt = f"Un logo moderne pour {title}. Style: {style}."
            
            logo_url = ""
            
            # Essayer de générer un logo avec fal.ai si disponible
            if fal_api_key:
                try:
                    headers = {
                        "Authorization": f"Key {fal_api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    payload = {
                        "prompt": f"logo design: {logo_prompt}. Minimalist, professional, vector style, white background, no text",
                        "negative_prompt": "text, words, letters, signature, watermark, low quality, blurry",
                        "height": 512,
                        "width": 512,
                        "num_images": 1
                    }
                    
                    response = requests.post(
                        "https://api.fal.ai/v1/stable-diffusion/sdxl",
                        headers=headers,
                        json=payload,
                        timeout=15
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        logo_url = data.get("images", [{}])[0].get("url", "")
                    else:
                        print(f"Erreur fal.ai: {response.status_code} - {response.text}")
                except Exception as e:
                    print(f"Erreur lors de la génération du logo avec fal.ai: {str(e)}")
                    traceback.print_exc()
            
            # Si pas de logo généré, utiliser un placeholder
            if not logo_url:
                # Utiliser des logos placeholder différents pour chaque variation
                placeholder_logos = [
                    "https://via.placeholder.com/200x200.png?text=Logo+1",
                    "https://via.placeholder.com/200x200.png?text=Logo+2",
                    "https://via.placeholder.com/200x200.png?text=Logo+3",
                    "https://via.placeholder.com/200x200.png?text=Logo+4",
                    "https://via.placeholder.com/200x200.png?text=Logo+5"
                ]
                
                # Utiliser un index basé sur l'ID de variation pour choisir un logo placeholder
                index = int(var_id.replace("var", "")) % len(placeholder_logos) if var_id.replace("var", "").isdigit() else 0
                logo_url = placeholder_logos[index - 1]
            
            # Ajouter le résultat
            results.append({
                "variation_id": var_id,
                "logo_url": logo_url,
                "logo_prompt": logo_prompt
            })
        
        return {"logos": results}
    except Exception as e:
        print(f"Erreur lors de la génération des logos: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-theme-color")
async def analyze_theme_color(request: ThemeAnalysisRequest):
    try:
        theme = request.theme
        
        if not api_key:
            # Fallback si pas de clé API
            return {"colorScheme": get_automatic_color_scheme(theme)}
        
        try:
            llm = ChatOpenAI(api_key=api_key, model_name=model, temperature=0.3)
            
            prompt = f"""
            Analyse le thème suivant: "{theme}"
            
            Détermine la palette de couleurs la plus appropriée parmi les options suivantes:
            - vert: pour les thèmes liés à la nature, l'environnement, la nourriture, la santé naturelle
            - bleu: pour les thèmes liés au voyage, à la technologie professionnelle, à la santé médicale, à l'eau
            - violet: pour les thèmes liés à la technologie créative, l'innovation, le luxe
            - rouge: pour les thèmes liés à la mode, la beauté, la passion, l'urgence
            - orange: pour les thèmes liés à la créativité, l'enthousiasme, la chaleur
            - jaune: pour les thèmes liés à l'optimisme, la jeunesse, l'énergie
            
            Réponds uniquement avec le nom de la palette (vert, bleu, violet, rouge, orange ou jaune) sans aucun autre texte.
            """
            
            response = llm.invoke([HumanMessage(content=prompt)])
            
            # Extraire la réponse et la nettoyer
            color_scheme = response.content.strip().lower()
            
            # Vérifier si la réponse est valide
            valid_schemes = ["vert", "bleu", "violet", "rouge", "orange", "jaune"]
            if color_scheme not in valid_schemes:
                # Si la réponse n'est pas valide, utiliser la méthode de secours
                color_scheme = get_automatic_color_scheme(theme)
            
            return {"colorScheme": color_scheme}
        except Exception as e:
            print(f"Erreur lors de l'analyse du thème avec LLM: {str(e)}")
            return {"colorScheme": get_automatic_color_scheme(theme)}
    except Exception as e:
        print(f"Erreur lors de l'analyse du thème: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Fonction de secours pour déterminer la palette de couleurs
def get_automatic_color_scheme(theme: str) -> str:
    theme_lower = theme.lower()
    
    if any(keyword in theme_lower for keyword in ["nourriture", "food", "restaurant", "bio", "café", "cuisine"]):
        return "vert"
    elif any(keyword in theme_lower for keyword in ["voyage", "travel", "tourisme", "aventure", "destination"]):
        return "bleu"
    elif any(keyword in theme_lower for keyword in ["tech", "digital", "innovation", "startup", "ai", "ia"]):
        return "violet"
    elif any(keyword in theme_lower for keyword in ["santé", "health", "médical", "clinique", "hôpital"]):
        return "bleu"
    elif any(keyword in theme_lower for keyword in ["mode", "fashion", "beauté", "beauty", "luxe", "style"]):
        return "rouge"
    elif any(keyword in theme_lower for keyword in ["créatif", "creative", "art", "design", "studio"]):
        return "orange"
    elif any(keyword in theme_lower for keyword in ["enfant", "kid", "école", "school", "éducation", "formation"]):
        return "jaune"
    else:
        return "default"

@app.post("/api/generate-all-content")
async def generate_all_content(request: dict = Body(...)):
    try:
        print(f"Requête reçue pour générer du contenu pour tous les sites")
        variations = request.get("variations", [])
        force_regenerate = request.get("forceRegenerate", False)
        
        print(f"Nombre de variations à traiter: {len(variations)}")
        print(f"Régénération forcée: {force_regenerate}")
        
        for i, variation in enumerate(variations):
            print(f"Traitement de la variation {i+1}/{len(variations)}: {variation.get('title', 'Sans titre')}")
            
            # Récupérer le logo s'il existe
            logo = variation.get("logo", None)
            
            # Initialiser le contenu si nécessaire
            if "content" not in variation:
                variation["content"] = {}
            
            if "articles" not in variation["content"]:
                variation["content"]["articles"] = []
            
            # Générer 5 articles si aucun n'existe déjà ou si force_regenerate est True
            if force_regenerate or len(variation["content"].get("articles", [])) == 0:
                # Récupérer les informations de la variation
                site_name = variation.get("title", "Site")
                site_description = variation.get("description", "")
                
                # Générer 5 articles
                for j in range(5):
                    try:
                        print(f"Génération de l'article {j+1}/5 pour {site_name}")
                        
                        # Générer un titre d'article
                        title_prompt = f"""
                        Génère un titre d'article accrocheur pour un site web nommé '{site_name}'.
                        Description du site: {site_description}
                        Le titre doit être concis (moins de 10 mots) et attrayant.
                        """
                        
                        title = ""
                        if api_key:
                            llm = ChatOpenAI(api_key=api_key, model_name=model, temperature=0.7)
                            response = llm.invoke([HumanMessage(content=title_prompt)])
                            title = response.content.strip().replace('"', '')
                        else:
                            # Fallback pour les tests
                            title = f"Article {j+1} pour {site_name}"
                        
                        print(f"Titre généré: {title}")
                        
                        # DÉBUT DU SCRAPING WEB POUR CET ARTICLE
                        print(f"Démarrage du scraping web pour l'article: {title}")
                        serp_api_key = "f4dc513226b4b703cdc98a18c2d325a559dcccd3b2e73da115045fe22a152af0"
                        
                        article_web_content = ""
                        article_sources = []
                        
                        try:
                            # Construire la requête de recherche
                            query = f"{title} {site_name} {site_description}"
                            search_url = f"https://serpapi.com/search.json?q={query.replace(' ', '+')}&api_key={serp_api_key}&engine=google&num=5"
                            
                            print(f"Requête SERP API pour l'article: {search_url}")
                            response = requests.get(search_url, timeout=30)
                            
                            print(f"Réponse SERP API reçue: status code {response.status_code}")
                            
                            if response.status_code == 200:
                                data = response.json()
                                
                                # Extraire les résultats organiques
                                organic_results = data.get("organic_results", [])
                                print(f"Nombre de résultats organiques trouvés: {len(organic_results)}")
                                
                                if organic_results:
                                    for k, result in enumerate(organic_results[:3]):
                                        result_title = result.get("title", "")
                                        result_snippet = result.get("snippet", "")
                                        result_link = result.get("link", "")
                                        
                                        print(f"Source {k+1}: {result_title} - {result_link}")
                                        
                                        # Ajouter à notre contenu web
                                        article_web_content += f"\n\nSource {k+1}: {result_title}\n{result_snippet}\n"
                                        article_sources.append(f"{result_title} - {result_link}")
                                else:
                                    print("Aucun résultat organique trouvé")
                            else:
                                print(f"Erreur API SERP: {response.status_code} - {response.text}")
                        except Exception as e:
                            print(f"Erreur lors du scraping web: {str(e)}")
                            traceback.print_exc()
                            article_web_content = ""
                        
                        # Si aucun contenu n'a été trouvé, utiliser un message par défaut
                        if not article_web_content:
                            article_web_content = f"Aucune information spécifique trouvée sur '{title}'. Génération d'un article basé sur les connaissances générales."
                            print("Utilisation du contenu par défaut")
                        else:
                            print(f"Contenu web récupéré avec succès: {len(article_web_content)} caractères")
                        # FIN DU SCRAPING WEB
                        
                        # Générer le contenu de l'article avec le contenu web
                        content_prompt = f"""
                        Écris un article complet pour un site web nommé '{site_name}' avec le titre '{title}'.
                        
                        Description du site: {site_description}
                        
                        Utilise les informations suivantes récupérées du web pour enrichir ton article:
                        {article_web_content}
                        
                        L'article doit:
                        - Être informatif et engageant
                        - Contenir environ 500 mots
                        - Être structuré avec une introduction, un développement et une conclusion
                        - Être adapté au thème du site
                        - Inclure des faits et informations pertinentes tirés des sources web
                        
                        Format: Markdown avec des sections et sous-sections.
                        """
                        
                        content = ""
                        
                        if api_key:
                            llm = ChatOpenAI(api_key=api_key, model_name=model, temperature=0.7)
                            response = llm.invoke([HumanMessage(content=content_prompt)])
                            content = response.content.strip()
                            
                            print(f"Article généré: {len(content)} caractères")
                        else:
                            # Fallback pour les tests
                            content = f"Contenu par défaut pour l'article {j+1}."
                        
                        # Ajouter l'article à la liste
                        variation["content"]["articles"].append({
                            "title": title,
                            "content": content,
                            "sources": article_sources
                        })
                        
                    except Exception as e:
                        print(f"Erreur lors de la génération de l'article {j+1}: {str(e)}")
                        traceback.print_exc()
                        
                        # Ajouter un article par défaut en cas d'erreur
                        variation["content"]["articles"].append({
                            "title": f"Article {j+1} pour {site_name}",
                            "content": f"Contenu par défaut pour l'article {j+1}. Une erreur s'est produite lors de la génération."
                        })
            
            # S'assurer que le logo est conservé
            if logo:
                variation["logo"] = logo
        
        print("Génération de contenu terminée avec succès")
        return {"variations": variations}
    
    except Exception as e:
        print(f"Erreur lors de la génération du contenu: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-article-image")
async def generate_article_image(request: dict = Body(...)):
    try:
        print(f"Requête reçue pour générer une image d'article")
        prompt = request.get("prompt", "")
        title = request.get("title", "")
        
        if not prompt and not title:
            return {"error": "Aucun prompt ou titre fourni"}
        
        # Utiliser le titre comme prompt si aucun prompt n'est fourni
        if not prompt:
            prompt = f"Illustration pour un article intitulé '{title}'"
        
        print(f"Génération d'une image avec le prompt: {prompt}")
        
        # Utiliser l'API fal.ai pour générer l'image
        try:
            # Configuration de l'API fal.ai
            fal_key = os.getenv("FAL_KEY", "")
            fal_secret = os.getenv("FAL_SECRET", "")
            
            if not fal_key or not fal_secret:
                return {"error": "Clés d'API fal.ai non configurées"}
            
            # Appel à l'API fal.ai
            response = requests.post(
                "https://api.fal.ai/text-to-image",
                json={
                    "prompt": prompt,
                    "negative_prompt": "low quality, blurry, distorted, deformed",
                    "width": 768,
                    "height": 512,
                    "num_images": 1,
                    "model": "realistic-vision-v5.1"
                },
                headers={
                    "Authorization": f"Key {fal_key}:{fal_secret}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 200:
                print(f"Erreur lors de l'appel à fal.ai: {response.status_code}")
                print(response.text)
                return {"error": f"Erreur lors de la génération de l'image: {response.status_code}"}
            
            data = response.json()
            
            # Extraire l'URL de l'image générée
            image_url = data.get("images", [{}])[0].get("url", "")
            
            if not image_url:
                return {"error": "Aucune image générée"}
            
            print(f"Image générée avec succès: {image_url}")
            
            return {"imageUrl": image_url}
            
        except Exception as e:
            print(f"Erreur lors de la génération de l'image avec fal.ai: {str(e)}")
            traceback.print_exc()
            
            # Utiliser une image de secours si fal.ai échoue
            return {"error": f"Erreur lors de la génération de l'image: {str(e)}"}
        
    except Exception as e:
        print(f"Erreur lors de la génération de l'image d'article: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/export-wordpress-template")
async def export_wordpress_template(request: dict = Body(...)):
    try:
        print(f"Requête reçue pour exporter un template WordPress")
        variation_id = request.get("variation_id")
        variation_data = request.get("variation_data", {})
        
        if not variation_data:
            return {"error": "Données de variation non fournies"}
        
        # Générer le contenu WXR
        wxr_content = generate_simple_wxr(variation_data)
        
        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(wxr_content.encode('utf-8'))
        
        # Retourner le fichier pour téléchargement
        return FileResponse(
            path=temp_file_path,
            filename=f"{variation_data.get('title', 'site')}_export.xml",
            media_type="application/xml",
            background=BackgroundTask(lambda: os.unlink(temp_file_path))
        )
    
    except Exception as e:
        print(f"Erreur lors de l'exportation: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

def generate_simple_wxr(variation_data):
    """Génère un fichier WXR simplifié"""
    
    # Créer la structure XML de base
    rss = ET.Element("rss")
    rss.set("version", "2.0")
    rss.set("xmlns:excerpt", "http://wordpress.org/export/1.2/excerpt/")
    rss.set("xmlns:content", "http://purl.org/rss/1.0/modules/content/")
    rss.set("xmlns:wfw", "http://wellformedweb.org/CommentAPI/")
    rss.set("xmlns:dc", "http://purl.org/dc/elements/1.1/")
    rss.set("xmlns:wp", "http://wordpress.org/export/1.2/")
    
    channel = ET.SubElement(rss, "channel")
    
    # Informations du site
    title = ET.SubElement(channel, "title")
    title.text = variation_data.get("title", "Site généré")
    
    description = ET.SubElement(channel, "description")
    description.text = variation_data.get("description", "")
    
    language = ET.SubElement(channel, "language")
    language.text = "fr-FR"
    
    wxr_version = ET.SubElement(channel, "wp:wxr_version")
    wxr_version.text = "1.2"
    
    # Ajouter les articles
    articles = variation_data.get("content", {}).get("articles", [])
    
    for i, article in enumerate(articles):
        item = ET.SubElement(channel, "item")
        
        # Titre de l'article
        item_title = ET.SubElement(item, "title")
        item_title.text = article.get("title", "")
        
        # Contenu de l'article
        content_encoded = ET.SubElement(item, "content:encoded")
        content_encoded.text = f"<![CDATA[{article.get('content', '')}]]>"
        
        # Type de post
        post_type = ET.SubElement(item, "wp:post_type")
        post_type.text = "post"
        
        # Statut de publication
        status = ET.SubElement(item, "wp:status")
        status.text = "publish"
        
        # ID unique pour l'article
        post_id = ET.SubElement(item, "wp:post_id")
        post_id.text = str(i + 1)
    
    # Convertir l'arbre XML en chaîne formatée
    rough_string = ET.tostring(rss, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

if __name__ == "__main__":
    print("Démarrage du serveur API...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 