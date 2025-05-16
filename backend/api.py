from fastapi import FastAPI, HTTPException, Body, Query
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
import markdown2  # Ajout de l'import pour markdown2
from crew_flux_image_agent import get_image_prompt_from_gemini, generate_image_with_fal

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
    allow_origins=["*"],  # Pour le développement seulement, à restreindre en production
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
        while len(titres) < 5:
            titres.append(f"Article sur {sujet} - {len(titres) + 1}")
        
        return titres[:5]
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
        - Être très court (2 à 3 lignes maximum)
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
        session_id = request.get("session_id", "")
        article_index = request.get("article_index")
        website = request.get("website", "")
        
        print(f"Génération d'article: {titre} pour le site {website}, index {article_index}")
        
        # Vérifier si une image existe déjà pour cet article
        article_image_url = None
        
        # Effectuer le scraping web pour trouver des images et du contenu
        web_content = ""
        sources = []
        
        try:
            print(f"Tentative de scraping pour: {sujet} - {titre}")
            
            # Recherche d'images via Google Images
            query = f"{sujet} {titre}"
            print(f"Requête de recherche d'images: {query}")
            
            # Utiliser SERP API pour la recherche d'images
            serp_api_key = os.getenv("SERP_API_KEY", "be83482fbc42759f8b772badebee33da859d05e98b88506bb2b7bc4e9e33fe56")
            search_url = f"https://serpapi.com/search.json?q={query.replace(' ', '+')}&api_key={serp_api_key}&engine=google&tbm=isch&num=5"
            
            try:
                print(f"Envoi de la requête à SERP API pour les images: {search_url}")
                response = requests.get(search_url, timeout=15)
                print(f"Réponse SERP API (images): {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    images_results = data.get("images_results", [])
                    
                    if images_results and len(images_results) > 0:
                        # Prendre la première image pertinente
                        article_image_url = images_results[0].get("original", "")
                        print(f"Image trouvée via SERP API: {article_image_url}")
                elif response.status_code == 429:
                    print("Limite de requêtes SERP API atteinte, utilisation d'Unsplash")
                    # Utiliser Unsplash comme alternative
                    unsplash_query = f"{sujet} {titre}".replace(" ", "+")
                    unsplash_url = f"https://source.unsplash.com/featured/?{unsplash_query}"
                    unsplash_response = requests.get(unsplash_url, allow_redirects=True, timeout=10)
                    if unsplash_response.status_code == 200:
                        article_image_url = unsplash_response.url
                        print(f"Image trouvée via Unsplash: {article_image_url}")
            except Exception as e:
                print(f"Erreur lors de la recherche d'images: {str(e)}")
            
            # Si aucune image n'a été trouvée, essayer avec Unsplash
            if not article_image_url:
                try:
                    print("Tentative avec Unsplash comme solution de secours")
                    unsplash_query = f"{sujet} {titre}".replace(" ", "+")
                    unsplash_url = f"https://source.unsplash.com/featured/?{unsplash_query}"
                    unsplash_response = requests.get(unsplash_url, allow_redirects=True, timeout=10)
                    if unsplash_response.status_code == 200:
                        article_image_url = unsplash_response.url
                        print(f"Image trouvée via Unsplash: {article_image_url}")
                except Exception as e:
                    print(f"Erreur lors de la recherche d'image sur Unsplash: {str(e)}")
            
            # Recherche de contenu web pour les sources
            search_url = f"https://serpapi.com/search.json?q={query.replace(' ', '+')}&api_key={serp_api_key}&engine=google&num=5"
            
            try:
                print(f"Envoi de la requête à SERP API pour le contenu: {search_url}")
                response = requests.get(search_url, timeout=15)
                print(f"Réponse SERP API (contenu): {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    organic_results = data.get("organic_results", [])
                    
                    if organic_results:
                        for i, result in enumerate(organic_results[:3]):
                            title = result.get("title", "")
                            snippet = result.get("snippet", "")
                            link = result.get("link", "")
                            
                            print(f"Source {i+1}: {title} - {link}")
                            web_content += f"\n\nSource {i+1}: {title}\n{snippet}\n"
                            sources.append(f"{title} - {link}")
                            
                            # Si aucune image n'a été trouvée, essayer d'en extraire une de cette page
                            if not article_image_url and i == 0:
                                try:
                                    page_response = requests.get(link, timeout=10, headers={
                                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                                    })
                                    
                                    if page_response.status_code == 200:
                                        soup = BeautifulSoup(page_response.text, 'html.parser')
                                        # Chercher une image pertinente
                                        img_tags = soup.find_all('img', src=True)
                                        for img in img_tags:
                                            src = img.get('src', '')
                                            # Filtrer les petites images et les icônes
                                            if src and ('http' in src) and not ('icon' in src.lower()) and not ('logo' in src.lower()):
                                                article_image_url = src
                                                print(f"Image extraite de la page: {article_image_url}")
                                                break
                                except Exception as e:
                                    print(f"Erreur lors de l'extraction d'image: {str(e)}")
                    else:
                        print("Aucun résultat organique trouvé")
            except Exception as e:
                print(f"Erreur lors de la recherche de contenu: {str(e)}")
        
        except Exception as e:
            print(f"Erreur lors du scraping: {str(e)}")
            traceback.print_exc()
        
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
        article_content = response.content.strip()
        
        # Sauvegarder l'article et l'image dans la session
        if session_id:
            try:
                # Vérifier si le dossier sessions existe
                os.makedirs("./sessions", exist_ok=True)
                
                session_file = f"./sessions/session_{session_id}.json"
                session_data = {}
                
                # Charger les données de session existantes si elles existent
                if os.path.exists(session_file):
                    with open(session_file, "r", encoding="utf-8") as f:
                        session_data = json.load(f)
                
                # Initialiser la structure si nécessaire
                if "articles" not in session_data:
                    session_data["articles"] = {}
                
                # Sauvegarder l'article avec son image
                if article_index is not None:
                    article_key = str(article_index)
                    if article_key not in session_data["articles"]:
                        session_data["articles"][article_key] = {}
                    
                    session_data["articles"][article_key]["title"] = titre
                    session_data["articles"][article_key]["content"] = article_content
                    session_data["articles"][article_key]["sources"] = sources
                    
                    if article_image_url:
                        session_data["articles"][article_key]["image"] = article_image_url
                        print(f"Image sauvegardée pour l'article {article_index}: {article_image_url}")
                
                # Écrire les données mises à jour
                with open(session_file, "w", encoding="utf-8") as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=2)
                
                print(f"Article et image sauvegardés dans la session {session_id}")
            
            except Exception as e:
                print(f"Erreur lors de la sauvegarde de l'article: {str(e)}")
                traceback.print_exc()
        
        return {
            "content": article_content,
            "sources": sources,
            "imageUrl": article_image_url
        }
    
    except Exception as e:
        print(f"Erreur lors de la génération de l'article: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-image")
async def generate_image(request: dict = Body(...)):
    try:
        print(f"Requête reçue pour générer une image")
        prompt = request.get("prompt", "")
        title = request.get("title", "")
        
        if not prompt and not title:
            return {"error": "Aucun prompt ou titre fourni"}
        
        # Utiliser le titre comme prompt si aucun prompt n'est fourni
        if not prompt:
            prompt = f"Illustration pour un article intitulé '{title}'"
        
        print(f"Génération d'une image avec le prompt: {prompt}")
        
        # Utiliser Gemini pour améliorer le prompt
        try:
            # Générer un meilleur prompt avec Gemini
            enhanced_prompt = get_image_prompt_from_gemini(prompt)
            print(f"Prompt amélioré par Gemini: {enhanced_prompt}")
            
            temp_file = None
            try:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                temp_file_path = temp_file.name
                temp_file.close()  # Close the file handle before generating the image
                
                generate_image_with_fal(enhanced_prompt, temp_file_path)
                
                # Lire l'image générée
                with open(temp_file_path, "rb") as f:
                    image_data = f.read()
                
                # Convertir en base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                image_url = f"data:image/png;base64,{image_base64}"
                
                return {"image_url": image_url}
            finally:
                # Nettoyer le fichier temporaire
                if temp_file and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except Exception as e:
                        print(f"Warning: Could not delete temporary file {temp_file_path}: {str(e)}")
                
        except Exception as e:
            print(f"Erreur lors de la génération de l'image: {str(e)}")
            traceback.print_exc()
            return {"error": f"Erreur lors de la génération de l'image: {str(e)}"}
            
    except Exception as e:
        print(f"Erreur lors de la génération de l'image: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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
        session_id = request.get("session_id")
        
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
            
            try:
                from crew_flux_image_agent import get_logo_prompt_from_gemini, generate_logo_with_fal
                
                # Générer un meilleur prompt avec Gemini
                enhanced_prompt = get_logo_prompt_from_gemini(logo_prompt)
                print(f"Prompt de logo amélioré par Gemini: {enhanced_prompt}")
                
                temp_file = None
                try:
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                    temp_file_path = temp_file.name
                    temp_file.close()  # Close the file handle before generating the image
                    
                    generate_logo_with_fal(enhanced_prompt, temp_file_path)
                    
                    # Read the generated logo
                    with open(temp_file_path, "rb") as f:
                        logo_data = f.read()
                    
                    # Convert to base64
                    logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                    logo_url = f"data:image/png;base64,{logo_base64}"
                    
                    # --- PERSISTENCE: enregistrer le logo dans la session backend si session_id fourni ---
                    if session_id:
                        import os, json
                        session_file = f"./sessions/session_{session_id}.json"
                        if os.path.exists(session_file):
                            try:
                                with open(session_file, "r", encoding="utf-8") as f:
                                    session_data = json.load(f)
                                if "logos" not in session_data or not isinstance(session_data["logos"], dict):
                                    session_data["logos"] = {}
                                session_data["logos"][var_id] = logo_url
                                with open(session_file, "w", encoding="utf-8") as f:
                                    json.dump(session_data, f, ensure_ascii=False, indent=2)
                            except Exception as e:
                                print(f"[WARN] Impossible de persister le logo dans la session: {e}")
                    # --- FIN PERSISTENCE ---
                    
                    # Add the result
                    results.append({
                        "variation_id": var_id,
                        "logo_url": logo_url,
                        "logo_prompt": enhanced_prompt
                    })
                    
                finally:
                    # Clean up the temporary file
                    if temp_file and os.path.exists(temp_file_path):
                        try:
                            os.unlink(temp_file_path)
                        except Exception as e:
                            print(f"Warning: Could not delete temporary file {temp_file_path}: {str(e)}")
                    
            except Exception as e:
                print(f"Erreur lors de la génération du logo: {str(e)}")
                traceback.print_exc()
                # Use a placeholder logo in case of error
                placeholder_url = f"https://via.placeholder.com/200x200.png?text=Logo+{var_id}"
                results.append({
                    "variation_id": var_id,
                    "logo_url": placeholder_url,
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

def get_random_color_palette():
    """
    Retourne une palette de couleurs aléatoire parmi les palettes prédéfinies.
    """
    palettes = [
  {
    "primary": "#0077b6",
    "secondary": "#E8F0FE",
    "background": "#FFFFFF",
    "text": "#202124"
  },
  {
    "primary": "#b2967d",
    "secondary": "#d5bdaf",
    "background": "#F5F5F5",
    "text": "#504b43"
  },
  {
    "primary": "#e76f51",
    "secondary": "#f4a261",
    "background": "#FFFFFF",
    "text": "#212121"
  },
  {
    "primary": "#009688",
    "secondary": "#B2DFDB",
    "background": "#FAFAFA",
    "text": "#263238"
  },
  {
    "primary": "#3F51B5",
    "secondary": "#C5CAE9",
    "background": "#FDFDFD",
    "text": "#212121"
  },
  {
    "primary": "#00BCD4",
    "secondary": "#B2EBF2",
    "background": "#FFFFFF",
    "text": "#023e8a"
  },
  {
    "primary": "#E91E63",
    "secondary": "#F8BBD0",
    "background": "#FFFFFF",
    "text": "#355070"
  },
  {
    "primary": "#f28482",
    "secondary": "#FFCDD2",
    "background": "#FFFFFF",
    "text": "#212121"
  },
  {
    "primary": "#588157",
    "secondary": "#C8E6C9",
    "background": "#F8F8F8",
    "text": "#344e41"
  },
  {
    "primary": "#db7c26",
    "secondary": "#FFF8E1",
    "background": "#FAFAFA",
    "text": "#212121"
  },
  {
    "primary": "#5e548e",
    "secondary": "#9f86c0",
    "background": "#FFFFFF",
    "text": "#1A1A1A"
  },
  {
    "primary": "#17c3b2",
    "secondary": "#CFD8DC",
    "background": "#f5f3f4",
    "text": "#227c9d"
  },
  {
    "primary": "#8a817c",
    "secondary": "#bcb8b1",
    "background": "#f4f3ee",
    "text": "#463f3a"
  },
  {
    "primary": "#a6a2a2",
    "secondary": "#cfd2cd",
    "background": "#fbfbf2",
    "text": "#847577"
  },
  {
    "primary": "#006494",
    "secondary": "#4cc9f0",
    "background": "#d6e3f8",
    "text": "#006daa"
  },
  {
    "primary": "#304d6d",
    "secondary": "#82a0bc",
    "background": "#d6e3f8",
    "text": "#545e75"
  },
  {
    "primary": "#007ea7",
    "secondary": "#B3E5FC",
    "background": "#F9FAFB",
    "text": "#01579B"
  },
  {
    "primary": "#00ACC1",
    "secondary": "#E0F7FA",
    "background": "#FFFFFF",
    "text": "#263238"
  },
  {
    "primary": "#C2185B",
    "secondary": "#F48FB1",
    "background": "#FFFFFF",
    "text": "#1C1C1C"
  },
  {
    "primary": "#3da35d",
    "secondary": "#A5D6A7",
    "background": "#e8fccf",
    "text": "#134611"
  },
  {
    "primary": "#303F9F",
    "secondary": "#C5CAE9",
    "background": "#FFFFFF",
    "text": "#1A1A1A"
  },
  {
    "primary": "#5D4037",
    "secondary": "#D7CCC8",
    "background": "#FAFAFA",
    "text": "#3E2723"
  },
  {
    "primary": "#0097A7",
    "secondary": "#B2EBF2",
    "background": "#F5F5F5",
    "text": "#004D40"
  },
  {
    "primary": "#ad2e24",
    "secondary": "#c75146",
    "background": "#FFFFFF",
    "text": "#3E2723"
  },
  {
    "primary": "#7B1FA2",
    "secondary": "#E1BEE7",
    "background": "#FDFDFD",
    "text": "#1A1A1A"
  },
  {
    "primary": "#1E88E5",
    "secondary": "#BBDEFB",
    "background": "#FFFFFF",
    "text": "#0D47A1"
  },
  {
    "primary": "#43A047",
    "secondary": "#C8E6C9",
    "background": "#FAFAFA",
    "text": "#1B5E20"
  },
  {
    "primary": "#b5838d",
    "secondary": "#F8BBD0",
    "background": "#ffebe7",
    "text": "#6d6875"
  },
  {
    "primary": "#6D4C41",
    "secondary": "#D7CCC8",
    "background": "#FFF",
    "text": "#3E2723"
  },
  {
    "primary": "#607D8B",
    "secondary": "#B0BEC5",
    "background": "#FFFFFF",
    "text": "#263238"
  }
    ]
    return random.choice(palettes)

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
            
            # Assigner une palette de couleurs aléatoire à chaque variation
            color_palette = get_random_color_palette()
            variation["color_palette"] = color_palette
            print(f"[Couleurs] Palette assignée à {variation.get('title')}:" )
            print(f"[Couleurs] - Primary: {color_palette['primary']}")
            print(f"[Couleurs] - Secondary: {color_palette['secondary']}")
            print(f"[Couleurs] - Text: {color_palette['text']}")
            print(f"[Couleurs] - Background: {color_palette['background']}")
            
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
                
                categories_list = ["Business", "Education", "Productivity", "Events", "Blog", "jobs"]
                # Générer 5 articles
                for j in range(5):
                    try:
                        category = categories_list[j % len(categories_list)]
                        print(f"Génération de l'article {j+1}/5 pour {site_name} (Catégorie: {category})")
                        
                        # Générer un titre d'article
                        title_prompt = f"""
                        Génère un titre d'article accrocheur pour un site web nommé '{site_name}'.
                        Description du site: {site_description}
                        Le titre doit être concis (moins de 10 mots) et attrayant.
                        Catégorie de l'article : {category}
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
                        serp_api_key = "57a4b93a29c3c3f50ed324aa1ed7150a5989e4ec47db2b8f39019ee71a44b463"
                        
                        article_web_content = ""
                        article_sources = []
                        
                        try:
                            # Construire la requête de recherche
                            query = f"{title} {site_name} {site_description} {category}"
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
                        Catégorie de l'article : {category}
                        Utilise les informations suivantes récupérées du web pour enrichir ton article:
                        {article_web_content}
                        L'article doit:
                        - Être informatif et engageant
                        - Contenir environ 500 mots
                        - Être structuré avec une introduction, un développement et une conclusion
                        - Être adapté au thème du site
                        - Être pertinent pour la catégorie : {category}
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
                        
                        # GÉNÉRATION DE L'IMAGE AVEC CREW_FLUX
                        article_image_url = None
                        try:
                            # Créer un prompt pour l'image basé sur le titre et la catégorie
                            image_topic = f"{title} - {category} - {site_description}"
                            print(f"Génération d'une image pour: {image_topic}")
                            
                            # Générer un meilleur prompt avec Gemini
                            enhanced_prompt = get_image_prompt_from_gemini(image_topic)
                            print(f"Prompt amélioré par Gemini: {enhanced_prompt}")
                            
                            # Générer l'image avec Fal.ai
                            temp_file = None
                            try:
                                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                                temp_file_path = temp_file.name
                                temp_file.close()  # Close the file handle before generating the image
                                
                                generate_image_with_fal(enhanced_prompt, temp_file_path)
                                
                                # Lire l'image générée
                                with open(temp_file_path, "rb") as f:
                                    image_data = f.read()
                                
                                # Convertir en base64
                                image_base64 = base64.b64encode(image_data).decode('utf-8')
                                article_image_url = f"data:image/png;base64,{image_base64}"
                                print(f"Image générée pour l'article: {len(article_image_url)} caractères")
                            finally:
                                if temp_file and os.path.exists(temp_file_path):
                                    try:
                                        os.unlink(temp_file_path)
                                    except Exception as e:
                                        print(f"Warning: Could not delete temporary file {temp_file_path}: {str(e)}")
                        except Exception as e:
                            print(f"Erreur lors de la génération de l'image: {str(e)}")
                            traceback.print_exc()
                        
                        # Ajouter l'article à la liste avec l'image
                        variation["content"]["articles"].append({
                            "title": title,
                            "content": content,
                            "sources": article_sources,
                            "category": category,
                            "image": article_image_url
                        })
                        
                        print(f"Article {j+1} ajouté avec image")
                        
                    except Exception as e:
                        print(f"Erreur lors de la génération de l'article {j+1}: {str(e)}")
                        traceback.print_exc()
                        
                        # Ajouter un article par défaut en cas d'erreur
                        variation["content"]["articles"].append({
                            "title": f"Article {j+1} pour {site_name}",
                            "content": f"Contenu par défaut pour l'article {j+1}. Une erreur s'est produite lors de la génération.",
                            "category": category
                        })
            
            # S'assurer que le logo est conservé
            if logo:
                variation["logo"] = logo
            
            # S'assurer que la palette de couleurs est conservée
            variation["color_palette"] = color_palette
        
        print("Génération de contenu terminée avec succès")
        return {"variations": variations}
    
    except Exception as e:
        print(f"Erreur lors de la génération du contenu: {str(e)}")
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

async def send_logo_to_wordpress(logo_url: str, logo_type: str = "main"):
    """
    Envoie le logo à WordPress via l'API Elementor.
    logo_type peut être "main" ou "second"
    """
    try:
        if not logo_url or not isinstance(logo_url, str) or not logo_url.strip():
            print(f"[WordPress] URL de logo invalide pour {logo_type}")
            return {"error": "URL de logo invalide"}
            
        print(f"[WordPress] Début de l'envoi du {logo_type} logo")
        print(f"[WordPress] URL du logo: {logo_url[:100]}...")
        
        # Vérifier si c'est une image base64
        if logo_url.startswith("data:image/"):
            print("[WordPress] Logo en base64 détecté, téléchargement sur WordPress...")
            try:
                # Extraire les données base64
                base64_data = logo_url.split(",")[1]
                image_data = base64.b64decode(base64_data)
                
                # Créer un fichier temporaire pour l'image originale
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                    temp_file.write(image_data)
                    temp_file_path = temp_file.name
                
                # Redimensionner l'image
                try:
                    with Image.open(temp_file_path) as img:
                        # Définir les dimensions maximales selon le type de logo
                        if logo_type == "main":
                            max_width = 200  # Largeur maximale pour le logo principal
                            max_height = 100  # Hauteur maximale pour le logo principal
                        else:
                            max_width = 150  # Largeur maximale pour le logo secondaire
                            max_height = 75   # Hauteur maximale pour le logo secondaire
                        
                        # Calculer les nouvelles dimensions en conservant le ratio
                        ratio = min(max_width/img.width, max_height/img.height)
                        new_size = (int(img.width * ratio), int(img.height * ratio))
                        
                        # Redimensionner l'image
                        resized_img = img.resize(new_size, Image.Resampling.LANCZOS)
                        
                        # Sauvegarder l'image redimensionnée
                        resized_img.save(temp_file_path, "PNG", quality=95)
                        print(f"[WordPress] Logo redimensionné à {new_size}")
                except Exception as e:
                    print(f"[WordPress] Erreur lors du redimensionnement: {str(e)}")
                    # Continuer avec l'image originale si le redimensionnement échoue
                
                # Vérifier les identifiants Basic Auth
                wordpress_username = os.getenv("WORDPRESS_USERNAME")
                wordpress_password = os.getenv("WORDPRESS_PASSWORD")
                
                if not wordpress_username or not wordpress_password:
                    print("[WordPress] Erreur: Identifiants WordPress non configurés")
                    return {"error": "Identifiants WordPress manquants"}
                
                # Encoder les identifiants pour Basic Auth
                credentials = f"{wordpress_username}:{wordpress_password}"
                token = base64.b64encode(credentials.encode()).decode()
                headers = {
                    "Authorization": f"Basic {token}"
                }
                
                # Télécharger l'image sur WordPress
                upload_url = "https://aic-builder.cloud-glory-creation.com/wp-json/wp/v2/media"
                with open(temp_file_path, "rb") as f:
                    files = {"file": f}
                    response = requests.post(upload_url, headers=headers, files=files)
                
                # Nettoyer le fichier temporaire
                os.unlink(temp_file_path)
                
                if response.status_code not in [201, 200]:
                    print(f"[WordPress] Erreur lors du téléchargement de l'image: {response.status_code}")
                    print(f"[WordPress] Détails: {response.text}")
                    return {"error": f"Erreur lors du téléchargement de l'image: {response.status_code}"}
                
                # Récupérer l'URL de l'image téléchargée
                image_data = response.json()
                logo_url = image_data.get("source_url")
                print(f"[WordPress] Image téléchargée avec succès: {logo_url}")
                
            except Exception as e:
                print(f"[WordPress] Erreur lors du traitement de l'image base64: {str(e)}")
                traceback.print_exc()
                return {"error": f"Erreur lors du traitement de l'image: {str(e)}"}
        
        # Vérifier si l'URL est une URL WordPress valide
        if not logo_url.startswith("https://aic-builder.cloud-glory-creation.com/wp-content/uploads/"):
            print(f"[WordPress] L'URL du logo n'est pas une URL WordPress valide: {logo_url}")
            return {"error": "URL de logo non valide pour WordPress"}
        
        # Vérifier les identifiants Basic Auth
        wordpress_username = os.getenv("WORDPRESS_USERNAME")
        wordpress_password = os.getenv("WORDPRESS_PASSWORD")
        
        if not wordpress_username or not wordpress_password:
            print("[WordPress] Erreur: Identifiants WordPress non configurés")
            return {"error": "Identifiants WordPress manquants"}
        
        # Encoder les identifiants pour Basic Auth
        credentials = f"{wordpress_username}:{wordpress_password}"
        token = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {token}"
        }
        
        # Déterminer l'endpoint en fonction du type de logo
        endpoint = "https://aic-builder.cloud-glory-creation.com/wp-json/elementor-remote/v1/set-main-logo"
        if logo_type == "second":
            endpoint = "https://aic-builder.cloud-glory-creation.com/wp-json/elementor-remote/v1/set-second-logo"
        
        # Préparer le payload
        payload = {
            "logo_url": logo_url
        }
        
        print(f"[WordPress] Envoi du logo à l'endpoint: {endpoint}")
        print(f"[WordPress] Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            print(f"[WordPress] Réponse reçue - Status: {response.status_code}")
            print(f"[WordPress] Corps de la réponse: {response.text}")
            
            if response.status_code == 200:
                print(f"[WordPress] Logo {logo_type} envoyé avec succès")
                return {"success": True, "message": f"Logo {logo_type} envoyé avec succès"}
            else:
                print(f"[WordPress] Erreur lors de l'envoi du logo: {response.status_code}")
                print(f"[WordPress] Détails de l'erreur: {response.text}")
                return {"error": f"Erreur lors de l'envoi du logo: {response.status_code}"}
                
        except Exception as e:
            print(f"[WordPress] Erreur lors de l'envoi du logo: {str(e)}")
            traceback.print_exc()
            return {"error": f"Erreur lors de l'envoi du logo: {str(e)}"}
            
    except Exception as e:
        print(f"[WordPress] Erreur générale lors de l'envoi du logo: {str(e)}")
        traceback.print_exc()
        return {"error": str(e)}

def upload_kit_json_to_wordpress(kit_data):
    """
    Uploads the kit JSON to WordPress media and returns the public URL.
    """
    wordpress_username = os.getenv("WORDPRESS_USERNAME")
    wordpress_password = os.getenv("WORDPRESS_PASSWORD")
    if not wordpress_username or not wordpress_password:
        print("[WordPress] ❌ ERREUR: Identifiants WordPress non configurés")
        return None
    credentials = f"{wordpress_username}:{wordpress_password}"
    token = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Disposition": "attachment; filename=global-kit.json",
        "Content-Type": "application/json"
    }
    # Save kit_data to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8") as temp_file:
        json.dump(kit_data, temp_file, ensure_ascii=False, indent=2)
        temp_file_path = temp_file.name
    try:
        with open(temp_file_path, "rb") as f:
            files = {"file": ("global-kit.json", f, "application/json")}
            upload_url = "https://aic-builder.cloud-glory-creation.com/wp-json/wp/v2/media"
            response = requests.post(upload_url, headers={"Authorization": f"Basic {token}"}, files=files)
        if response.status_code not in [201, 200]:
            print(f"[WordPress] Erreur lors de l'upload du kit JSON: {response.status_code}")
            print(f"[WordPress] Détails: {response.text}")
            return None
        image_data = response.json()
        kit_url = image_data.get("source_url")
        print(f"[WordPress] Kit JSON uploaded: {kit_url}")
        return kit_url
    finally:
        try:
            os.unlink(temp_file_path)
        except Exception:
            pass

async def send_color_palette_to_wordpress(color_palette: dict):
    """
    Envoie la palette de couleurs au kit Elementor de WordPress.
    """
    try:
        print("\n[WordPress] ===== DÉBUT DE L'ENVOI DE LA PALETTE DE COULEURS =====")
        print(f"[WordPress] Palette reçue: {json.dumps(color_palette, indent=2)}")
        
        # Vérifier les identifiants Basic Auth
        wordpress_username = os.getenv("WORDPRESS_USERNAME")
        wordpress_password = os.getenv("WORDPRESS_PASSWORD")
        
        if not wordpress_username or not wordpress_password:
            print("[WordPress] ❌ ERREUR: Identifiants WordPress non configurés")
            return {"error": "Identifiants WordPress manquants"}
        
        print("[WordPress] ✅ Identifiants WordPress trouvés")
        
        # Préparer le kit avec la nouvelle palette de couleurs
        kit_data = {
            "version": "0.4",
            "title": "Global Kit Styles",
            "type": "global-styles",
            "metadata": {
                "template_type": "global-styles",
                "include_in_zip": "1",
                "wp_page_template": "default"
            },
            "content": [],
            "page_settings": {
                "system_colors": [
                    {
                        "_id": "primary",
                        "title": "Primary",
                        "color": color_palette["primary"]
                    },
                    {
                        "_id": "secondary",
                        "title": "Secondary",
                        "color": color_palette["secondary"]
                    },
                    {
                        "_id": "text",
                        "title": "Text",
                        "color": color_palette["text"]
                    },
                    {
                        "_id": "accent",
                        "title": "Accent",
                        "color": color_palette["secondary"]
                    }
                ],
                "custom_colors": [
                    {
                        "_id": "e777cd9",
                        "title": "White",
                        "color": color_palette["background"]
                    },
                    {
                        "_id": "e632858",
                        "title": "transparent",
                        "color": "#FFFFFF00"
                    },
                    {
                        "_id": "e9c5ff0",
                        "title": "grey",
                        "color": "#F3F3F3"
                    },
                    {
                        "_id": "9947692",
                        "title": "white trans",
                        "color": "#FFFFFFD1"
                    },
                    {
                        "_id": "7e293d1",
                        "title": "Black Trans",
                        "color": "#22283170"
                    }
                ],
                "system_typography": [
                    {
                        "_id": "primary",
                        "title": "Large text",
                        "typography_typography": "custom",
                        "typography_font_family": "Sans-serif",
                        "typography_font_weight": "500",
                        "typography_font_size": {
                            "unit": "px",
                            "size": 150,
                            "sizes": []
                        },
                        "typography_line_height": {
                            "unit": "em",
                            "size": 1,
                            "sizes": []
                        },
                        "typography_letter_spacing": {
                            "unit": "em",
                            "size": -0.05,
                            "sizes": []
                        },
                        "typography_font_size_mobile": {
                            "unit": "px",
                            "size": 45,
                            "sizes": []
                        },
                        "typography_font_size_tablet": {
                            "unit": "px",
                            "size": 80,
                            "sizes": []
                        }
                    },
                    {
                        "_id": "secondary",
                        "title": "Secondary",
                        "typography_typography": "custom",
                        "typography_font_family": "Sans-serif",
                        "typography_font_weight": "400",
                        "typography_font_size": {
                            "unit": "px",
                            "size": 28,
                            "sizes": []
                        },
                        "typography_line_height": {
                            "unit": "em",
                            "size": 1.5,
                            "sizes": []
                        },
                        "typography_font_size_tablet": {
                            "unit": "px",
                            "size": 21,
                            "sizes": []
                        },
                        "typography_font_size_mobile": {
                            "unit": "px",
                            "size": 19,
                            "sizes": []
                        }
                    },
                    {
                        "_id": "text",
                        "title": "Text",
                        "typography_typography": "custom",
                        "typography_font_family": "Sans-serif",
                        "typography_font_weight": "400",
                        "typography_font_size": {
                            "unit": "px",
                            "size": 18,
                            "sizes": []
                        },
                        "typography_line_height": {
                            "unit": "em",
                            "size": 1.65,
                            "sizes": []
                        },
                        "typography_letter_spacing": {
                            "unit": "em",
                            "size": 0.01,
                            "sizes": []
                        }
                    },
                    {
                        "_id": "accent",
                        "title": "Accent",
                        "typography_typography": "custom",
                        "typography_font_family": "Sans-serif",
                        "typography_font_weight": "400",
                        "typography_font_size": {
                            "unit": "px",
                            "size": 16,
                            "sizes": []
                        },
                        "typography_line_height": {
                            "unit": "em",
                            "size": 1.5,
                            "sizes": []
                        },
                        "typography_letter_spacing": {
                            "unit": "px",
                            "size": 0.15,
                            "sizes": []
                        },
                        "typography_text_transform": "uppercase"
                    }
                ],
                "default_generic_fonts": "Sans-serif",
                "body_color": color_palette["text"],
                "link_normal_color": color_palette["primary"],
                "h1_color": color_palette["text"],
                "page_title_selector": "h1.entry-title",
                "hello_footer_copyright_text": "All rights reserved",
                "activeItemIndex": 1,
                "__globals__": {
                    "body_color": "globals/colors?id=text",
                    "body_typography_typography": "globals/typography?id=text",
                    "link_normal_color": "globals/colors?id=primary",
                    "link_hover_color": "globals/colors?id=text",
                    "h1_color": "globals/colors?id=text",
                    "h1_typography_typography": "globals/typography?id=8352cd5",
                    "h3_color": "globals/colors?id=text",
                    "h3_typography_typography": "globals/typography?id=d4f69a8",
                    "h2_color": "globals/colors?id=text",
                    "h4_color": "globals/colors?id=text",
                    "h5_color": "globals/colors?id=text",
                    "h6_color": "globals/colors?id=text",
                    "button_typography_typography": "globals/typography?id=87350ce",
                    "button_text_color": "globals/colors?id=e777cd9",
                    "button_hover_background_color": "globals/colors?id=e777cd9",
                    "button_background_color": "globals/colors?id=text",
                    "button_hover_text_color": "globals/colors?id=primary",
                    "form_label_typography_typography": "globals/typography?id=accent",
                    "form_label_color": "globals/colors?id=text",
                    "form_field_typography_typography": "globals/typography?id=text",
                    "form_field_text_color": "globals/colors?id=text",
                    "form_field_background_color": "globals/colors?id=e777cd9",
                    "button_border_color": "globals/colors?id=text",
                    "h2_typography_typography": "globals/typography?id=4353ebc",
                    "h4_typography_typography": "globals/typography?id=326df42",
                    "h5_typography_typography": "globals/typography?id=49ea2e1",
                    "h6_typography_typography": "globals/typography?id=6524214",
                    "form_field_border_color": "globals/colors?id=d59e8a8",
                    "body_background_color": "globals/colors?id=e777cd9",
                    "button_hover_border_color": "globals/colors?id=text"
                },
                "viewport_md": 768,
                "viewport_lg": 1025,
                "h2_color": color_palette["text"],
                "h3_color": color_palette["text"],
                "h4_color": color_palette["text"],
                "h5_color": color_palette["text"],
                "h6_color": color_palette["text"],
                "button_padding": {
                    "unit": "px",
                    "top": "20",
                    "right": "50",
                    "bottom": "20",
                    "left": "50",
                    "isLinked": False
                },
                "paragraph_spacing": {
                    "unit": "px",
                    "size": 18,
                    "sizes": []
                },
                "container_width": {
                    "unit": "%",
                    "size": 98,
                    "sizes": []
                },
                "button_border_width": {
                    "unit": "px",
                    "top": "1",
                    "right": "1",
                    "bottom": "1",
                    "left": "1",
                    "isLinked": True
                },
                "image_border_radius": {
                    "unit": "px",
                    "top": "0",
                    "right": "0",
                    "bottom": "0",
                    "left": "0",
                    "isLinked": True
                },
                "image_opacity": {
                    "unit": "px",
                    "size": 1,
                    "sizes": []
                },
                "image_hover_border_radius": {
                    "unit": "px",
                    "top": "0",
                    "right": "0",
                    "bottom": "0",
                    "left": "0",
                    "isLinked": True
                },
                "image_hover_opacity": {
                    "unit": "px",
                    "size": 1,
                    "sizes": []
                },
                "image_hover_css_filters_saturate": {
                    "unit": "px",
                    "size": 139,
                    "sizes": []
                },
                "image_hover_css_filters_hue": {
                    "unit": "px",
                    "size": 112,
                    "sizes": []
                },
                "form_field_border_border": "solid",
                "form_field_border_width": {
                    "unit": "px",
                    "top": "1",
                    "right": "1",
                    "bottom": "1",
                    "left": "1",
                    "isLinked": True
                },
                "form_field_border_radius": {
                    "unit": "px",
                    "top": "0",
                    "right": "0",
                    "bottom": "0",
                    "left": "0",
                    "isLinked": True
                },
                "button_text_color": color_palette["background"],
                "button_background_color": color_palette["primary"],
                "button_hover_text_color": color_palette["primary"],
                "button_hover_background_color": color_palette["background"],
                "form_label_color": color_palette["text"],
                "form_field_text_color": color_palette["text"],
                "form_field_background_color": color_palette["background"],
                "image_box_shadow_box_shadow": {
                    "horizontal": 0,
                    "vertical": 20,
                    "blur": 50,
                    "spread": 0,
                    "color": "rgba(98.00000000000001, 98.00000000000001, 98.00000000000001, 0.12)"
                },
                "link_hover_color": color_palette["text"],
                "button_hover_border_width": {
                    "unit": "px",
                    "top": "1",
                    "right": "1",
                    "bottom": "1",
                    "left": "1",
                    "isLinked": True
                },
                "body_background_image": {
                    "url": "",
                    "id": "",
                    "size": "",
                    "alt": "",
                    "source": "library"
                },
                "body_background_position": "center center",
                "body_background_repeat": "repeat-y",
                "body_background_size": "contain",
                "active_breakpoints": [
                    "viewport_mobile",
                    "viewport_tablet",
                    "viewport_widescreen"
                ],
                "viewport_widescreen": 1600,
                "button_hover_box_shadow_box_shadow": {
                    "horizontal": 0,
                    "vertical": 20,
                    "blur": 50,
                    "spread": 0,
                    "color": "rgba(98.22330163043478, 98.24020576116492, 98.24999999999999, 0.31)"
                },
                "body_background_background": "classic",
                "button_border_width_tablet": {
                    "unit": "px",
                    "top": "1",
                    "right": "1",
                    "bottom": "1",
                    "left": "1",
                    "isLinked": True
                },
                "button_hover_border_width_tablet": {
                    "unit": "px",
                    "top": "1",
                    "right": "1",
                    "bottom": "1",
                    "left": "1",
                    "isLinked": True
                },
                "link_hover_typography_text_decoration": "underline",
                "button_hover_background_background": "",
                "button_border_radius": {
                    "unit": "px",
                    "top": "0",
                    "right": "0",
                    "bottom": "0",
                    "left": "0",
                    "isLinked": True
                },
                "button_padding_tablet": {
                    "unit": "px",
                    "top": "15",
                    "right": "30",
                    "bottom": "15",
                    "left": "30",
                    "isLinked": False
                }
            }
        }
        
        print("[WordPress] Kit préparé avec les couleurs suivantes:")
        print(f"[WordPress] - Primary: {color_palette['primary']}")
        print(f"[WordPress] - Secondary: {color_palette['secondary']}")
        print(f"[WordPress] - Text: {color_palette['text']}")
        print(f"[WordPress] - Background: {color_palette['background']}")
        
        # 1. Upload the kit JSON to WordPress media
        kit_url = upload_kit_json_to_wordpress(kit_data)
        if not kit_url:
            print("[WordPress] ❌ Impossible d'uploader le kit JSON")
            return {"error": "Impossible d'uploader le kit JSON"}
        print(f"[WordPress] ✅ Kit JSON uploaded: {kit_url}")
        
        # 2. Send the kit_url as form-data to Elementor endpoint
        endpoint = "https://aic-builder.cloud-glory-creation.com/wp-json/elementor-remote/v1/import-kit/"
        print(f"\n[WordPress] Envoi du kit_url à l'endpoint: {endpoint}")
        print("[WordPress] Envoi de la requête form-data...")
        
        data = {"kit_url": kit_url}
        response = requests.post(
            endpoint,
            data=data,
            headers={"Authorization": f"Basic {base64.b64encode(f'{wordpress_username}:{wordpress_password}'.encode()).decode()}"},
            timeout=30
        )
        print(f"\n[WordPress] Réponse reçue:")
        print(f"[WordPress] - Status Code: {response.status_code}")
        print(f"[WordPress] - Headers: {dict(response.headers)}")
        print(f"[WordPress] - Corps de la réponse: {response.text[:500]}...")
        
        if response.status_code == 200:
            print("\n[WordPress] ✅ Palette de couleurs envoyée avec succès")
            print("[WordPress] ===== FIN DE L'ENVOI DE LA PALETTE DE COULEURS =====\n")
            return {"success": True, "message": "Palette de couleurs envoyée avec succès"}
        else:
            print(f"\n[WordPress] ❌ Erreur lors de l'envoi de la palette: {response.status_code}")
            print(f"[WordPress] Détails de l'erreur: {response.text}")
            print("[WordPress] ===== FIN DE L'ENVOI DE LA PALETTE DE COULEURS =====\n")
            return {"error": f"Erreur lors de l'envoi de la palette: {response.status_code}"}
            
    except Exception as e:
        print(f"\n[WordPress] ❌ Erreur lors de l'envoi de la palette: {str(e)}")
        traceback.print_exc()
        print("[WordPress] ===== FIN DE L'ENVOI DE LA PALETTE DE COULEURS =====\n")
        return {"error": str(e)}

@app.post("/api/publish-to-wordpress")
async def publish_to_wordpress(request: dict = Body(...)):
    try:
        print(f"\n[WordPress] ===== DÉBUT DE LA PUBLICATION =====")
        variation_data = request.get("variation_data", {})
        session_id = request.get("session_id")
        
        if not variation_data:
            print("[WordPress] ❌ Erreur: Données de variation non fournies")
            return {"error": "Données de variation non fournies"}
        
        # Debug: Afficher toutes les clés disponibles dans variation_data
        print(f"[WordPress] Clés disponibles dans variation_data: {list(variation_data.keys())}")
        
        # Récupérer la palette de couleurs
        color_palette = variation_data.get("color_palette")
        print("\n[WordPress] === PALETTE DE COULEURS ===")
        if color_palette:
            print("[WordPress] ✅ Palette de couleurs trouvée:")
            print(f"[WordPress] - Primary: {color_palette.get('primary', 'Non définie')}")
            print(f"[WordPress] - Secondary: {color_palette.get('secondary', 'Non définie')}")
            print(f"[WordPress] - Text: {color_palette.get('text', 'Non définie')}")
            print(f"[WordPress] - Background: {color_palette.get('background', 'Non définie')}")
            
            print("\n[WordPress] Envoi de la palette de couleurs...")
            palette_result = await send_color_palette_to_wordpress(color_palette)
            print(f"[WordPress] Résultat de l'envoi de la palette: {palette_result}")
        else:
            print("[WordPress] ❌ Aucune palette de couleurs trouvée dans les données")
            print("[WordPress] Données reçues:", json.dumps(variation_data, indent=2))
            # Générer une palette par défaut si aucune n'est trouvée
            default_palette = get_random_color_palette()
            print("[WordPress] Utilisation d'une palette par défaut:")
            print(f"[WordPress] - Primary: {default_palette['primary']}")
            print(f"[WordPress] - Secondary: {default_palette['secondary']}")
            print(f"[WordPress] - Text: {default_palette['text']}")
            print(f"[WordPress] - Background: {default_palette['background']}")
            palette_result = await send_color_palette_to_wordpress(default_palette)
            print(f"[WordPress] Résultat de l'envoi de la palette par défaut: {palette_result}")
        
        print("\n[WordPress] === FIN DE LA SECTION PALETTE DE COULEURS ===\n")
        
        # Récupérer le logo depuis la session si disponible
        logo_url = None
        if session_id:
            try:
                session_file = f"./sessions/session_{session_id}.json"
                if os.path.exists(session_file):
                    with open(session_file, "r", encoding="utf-8") as f:
                        session_data = json.load(f)
                        if "logos" in session_data and isinstance(session_data["logos"], dict):
                            variation_id = variation_data.get("id")
                            if variation_id and variation_id in session_data["logos"]:
                                logo_url = session_data["logos"][variation_id]
                                print(f"[WordPress] Logo trouvé dans la session: {logo_url[:100]}...")
            except Exception as e:
                print(f"[WordPress] Erreur lors de la récupération du logo depuis la session: {str(e)}")
        
        # Si pas de logo dans la session, essayer de récupérer depuis variation_data
        if not logo_url:
            logo_url = variation_data.get("logo")
            print(f"[WordPress] Logo depuis variation_data: {logo_url}")
        
        # Vérifier les identifiants Basic Auth
        wordpress_username = os.getenv("WORDPRESS_USERNAME")
        wordpress_password = os.getenv("WORDPRESS_PASSWORD")
        
        if not wordpress_username or not wordpress_password:
            print("[WordPress] Erreur: Identifiants WordPress non configurés")
            return {"error": "Identifiants WordPress manquants"}
        
        # Encoder les identifiants pour Basic Auth
        credentials = f"{wordpress_username}:{wordpress_password}"
        token = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {token}"
        }
        
        print(f"[WordPress] Préparation des articles pour la variation: {variation_data.get('title', 'Sans titre')}")
        
        # Vérifier et envoyer le logo principal
        if logo_url and isinstance(logo_url, str) and logo_url.strip():
            print(f"[WordPress] Logo principal trouvé: {logo_url[:100]}...")
            logo_result = await send_logo_to_wordpress(logo_url, "main")
            print(f"[WordPress] Résultat de l'envoi du logo principal: {logo_result}")
        else:
            print(f"[WordPress] Aucun logo principal valide trouvé dans les données. Valeur reçue: {logo_url}")
            if logo_url is None:
                print("[WordPress] Le logo est None")
            elif not isinstance(logo_url, str):
                print(f"[WordPress] Le logo n'est pas une chaîne de caractères (type: {type(logo_url)})")
            elif not logo_url.strip():
                print("[WordPress] Le logo est une chaîne vide")

        # Vérifier et envoyer le logo secondaire (utiliser le même que le principal si absent)
        second_logo_url = variation_data.get("second_logo")
        if not (second_logo_url and isinstance(second_logo_url, str) and second_logo_url.strip()):
            print("[WordPress] Aucun logo secondaire valide trouvé, utilisation du logo principal pour le secondaire.")
            second_logo_url = logo_url
        else:
            print(f"[WordPress] Logo secondaire trouvé: {second_logo_url}")
        if second_logo_url and isinstance(second_logo_url, str) and second_logo_url.strip():
            second_logo_result = await send_logo_to_wordpress(second_logo_url, "second")
            print(f"[WordPress] Résultat de l'envoi du logo secondaire: {second_logo_result}")
        else:
            print(f"[WordPress] Aucun logo secondaire valide trouvé dans les données. Valeur reçue: {second_logo_url}")
            if second_logo_url is None:
                print("[WordPress] Le logo secondaire est None")
            elif not isinstance(second_logo_url, str):
                print(f"[WordPress] Le logo secondaire n'est pas une chaîne de caractères (type: {type(second_logo_url)})")
            elif not second_logo_url.strip():
                print("[WordPress] Le logo secondaire est une chaîne vide")

        # Préparer les posts pour WordPress
        posts = []
        articles = variation_data.get("content", {}).get("articles", [])
        
        print(f"[WordPress] Nombre d'articles à publier: {len(articles)}")
        
        allowed_categories = ["Most Viewed", "Trending", "Highlights", "Latest News"]
        allowed_tags = ["Business", "Education", "Productivity", "Events", "Blog", "jobs"]
        for i, article in enumerate(articles):
            print(f"[WordPress] Traitement de l'article {i+1}/{len(articles)}: {article.get('title', 'Sans titre')}")
            
            # Extraire le titre et le contenu
            title = article.get("title", "")
            content_markdown = article.get("content", "")
            
            # Convertir le Markdown en HTML
            content_html = markdown2.markdown(content_markdown, extras=["fenced-code-blocks", "tables"])
            
            soup = BeautifulSoup(content_html, 'html.parser')
            # 1. Excerpt = texte du <h1>
            h1 = soup.find('h1')
            excerpt = h1.get_text(strip=True) if h1 else ""
            if len(excerpt) > 160:
                excerpt = excerpt[:157] + "..."
            # 2. Content = tout le HTML après le <h1>
            content_after_h1 = ""
            if h1:
                for sibling in h1.next_siblings:
                    if isinstance(sibling, str):
                        content_after_h1 += sibling
                    else:
                        content_after_h1 += str(sibling)
                content_after_h1 = content_after_h1.strip()
            else:
                content_after_h1 = str(soup)
            
            # Déterminer les catégories en fonction du contenu/titre
            categories = []
            title_content = f"{title} {content_after_h1}".lower()
            if any(word in title_content for word in ["nouveau", "important", "alerte", "news"]):
                categories.append("Latest News")
            if any(word in title_content for word in ["tendance", "populaire", "trending"]):
                categories.append("Trending")
            if any(word in title_content for word in ["événement", "event", "highlight"]):
                categories.append("Highlights")
            if not categories:
                categories.append("Most Viewed")
            # Limiter à 2 catégories max
            categories = [c for c in categories if c in allowed_categories][:2]
            
            # Déterminer les tags en fonction du contenu/titre
            tags = [article.get("category", "Blog")]
            if any(word in title_content for word in ["business", "entreprise"]):
                tags.append("Business")
            if any(word in title_content for word in ["éducation", "formation", "education"]):
                tags.append("Education")
            if "productivité" in title_content or "productivity" in title_content:
                tags.append("Productivity")
            if any(word in title_content for word in ["événement", "event"]):
                tags.append("Events")
            if "blog" in title_content:
                tags.append("Blog")
            if "job" in title_content or "emploi" in title_content:
                tags.append("jobs")
            # Always add Blog if no other tag
            if not tags:
                tags.append("Blog")
            # Limiter à 3 tags max
            tags = [t for t in tags if t in allowed_tags][:3]
            
            print(f"[WordPress] Catégories: {categories}")
            print(f"[WordPress] Tags: {tags}")
            
            # Créer l'objet post avec le contenu HTML
            post = {
                "title": title,
                "excerpt": excerpt,
                "content": content_after_h1,  # Utiliser le HTML sans le <h1>
                "status": "publish",
                "categories": categories,
                "tags": tags,
                "featured_image_url": ""
            }
            
            posts.append(post)
        
        # Build the payload with plain Python strings (let json handle escaping)
        
        
        payload = {"clear_existing": True, "posts": posts}
        # For debugging: print the JSON as a string
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        
        # Envoyer les posts à WordPress
        wordpress_endpoint = "https://aic-builder.cloud-glory-creation.com/wp-json/elementor-remote/v1/import-posts"
        
        print(f"[WordPress] Envoi des articles à l'endpoint: {wordpress_endpoint}")
        
        try:
            print("[WordPress] Envoi de la requête avec Basic Auth")
            response = requests.post(
                wordpress_endpoint,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            print(f"[WordPress] Réponse reçue - Status: {response.status_code}")
            print(f"[WordPress] Corps de la réponse: {response.text[:500]}...")
            
            if response.status_code == 200:
                print("[WordPress] Publication réussie")
                return {"success": True, "message": "Articles publiés avec succès"}
            elif response.status_code == 401:
                print("[WordPress] Erreur d'autorisation - Vérifiez les identifiants Basic Auth")
                return {"error": "Erreur d'autorisation - Vérifiez les identifiants Basic Auth"}
            elif response.status_code == 403:
                print("[WordPress] Accès refusé - Vérifiez les permissions")
                return {"error": "Accès refusé - Vérifiez les permissions"}
            else:
                print(f"[WordPress] Erreur lors de la publication: {response.status_code}")
                print(f"[WordPress] Détails de l'erreur: {response.text}")
                return {"error": f"Erreur lors de la publication: {response.status_code}"}
                
        except requests.exceptions.Timeout:
            print("[WordPress] Timeout lors de la requête")
            return {"error": "Timeout lors de la connexion à WordPress"}
        except requests.exceptions.ConnectionError:
            print("[WordPress] Erreur de connexion")
            return {"error": "Impossible de se connecter à WordPress"}
        except Exception as e:
            print(f"[WordPress] Erreur lors de la requête: {str(e)}")
            return {"error": f"Erreur de connexion: {str(e)}"}
    
    except Exception as e:
        print(f"[WordPress] Erreur générale: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-logo")
async def upload_logo(request: dict = Body(...)):
    """
    Permet d'uploader un logo (base64) pour une variation et de le stocker côté backend dans la session.
    """
    session_id = request.get("session_id")
    variation_id = request.get("variation_id")
    logo_base64 = request.get("logo_base64")
    if not session_id or not variation_id or not logo_base64:
        return {"error": "session_id, variation_id et logo_base64 sont requis"}
    import os, json
    session_file = f"./sessions/session_{session_id}.json"
    if not os.path.exists(session_file):
        return {"error": "Session non trouvée"}
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            session_data = json.load(f)
        # Stocker dans session_data["logos"][variation_id]
        if "logos" not in session_data or not isinstance(session_data["logos"], dict):
            session_data["logos"] = {}
        session_data["logos"][variation_id] = logo_base64
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        return {"logo_url": logo_base64}
    except Exception as e:
        print(f"[UPLOAD LOGO ERROR] {e}")
        return {"error": str(e)}

@app.get("/api/get-logos")
async def get_logos(session_id: str = Query(...)):
    """
    Retourne tous les logos pour une session donnée.
    """
    import os, json
    session_file = f"./sessions/session_{session_id}.json"
    if not os.path.exists(session_file):
        return {"logos": {}}
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            session_data = json.load(f)
        logos = session_data.get("logos", {})
        return {"logos": logos}
    except Exception as e:
        print(f"[GET LOGOS ERROR] {e}")
        return {"logos": {}}

@app.post("/api/create-session")
async def create_session(request: dict = Body(...)):
    session_id = request.get("session_id")
    variations = request.get("variations", [])
    if not session_id:
        return {"error": "session_id requis"}
    import os, json
    os.makedirs("./sessions", exist_ok=True)
    session_file = f"./sessions/session_{session_id}.json"
    if os.path.exists(session_file):
        return {"message": "Session déjà existante"}
    session_data = {
        "logos": {},
        "variations": variations,
        "articles": []
    }
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)
    return {"message": "Session créée"}

@app.post("/api/generate-logo")
async def generate_logo(request: dict = Body(...)):
    try:
        print("Requête reçue pour générer un logo")
        prompt = request.get("prompt", "")
        session_id = request.get("session_id")
        var_id = request.get("variation_id")
        
        if not prompt:
            return {"error": "Prompt requis"}
        
        print(f"Génération d'un logo avec le prompt: {prompt}")
        
        # Générer un meilleur prompt avec Gemini
        from crew_flux_image_agent import get_logo_prompt_from_gemini, generate_logo_with_fal
        enhanced_prompt = get_logo_prompt_from_gemini(prompt)
        print(f"Prompt amélioré par Gemini: {enhanced_prompt}")
        
        # Générer le logo avec Fal.ai
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        temp_file_path = temp_file.name
        temp_file.close()
        
        try:
            generate_logo_with_fal(enhanced_prompt, temp_file_path)
            
            # Lire le logo généré
            with open(temp_file_path, "rb") as f:
                logo_data = f.read()
            
            # Convertir en base64
            logo_base64 = base64.b64encode(logo_data).decode('utf-8')
            logo_url = f"data:image/png;base64,{logo_base64}"
            
            # Ne pas sauvegarder dans la session
            
            return {"logo_url": logo_url}
        finally:
            # Supprimer le fichier temporaire
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    except Exception as e:
        print(f"Erreur lors de la génération du logo: {str(e)}")
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    print("Démarrage du serveur API...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 