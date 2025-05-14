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
        additional_context = request.get("additional_context", "")
        avoid_context = request.get("avoid_context", "")
        article_length = request.get("article_length", 1500)
        detail_level = request.get("detail_level", 3)
        
        if not api_key:
            raise ValueError("Clé API OpenAI non configurée")
        
        try:
            llm = ChatOpenAI(api_key=api_key, model_name=model, temperature=0.7)
            
            # Construire le prompt avec les éléments à inclure et à éviter
            include_section = ""
            if additional_context:
                include_section = f"""
                Éléments à inclure:
                {additional_context}
                """
            
            avoid_section = ""
            if avoid_context:
                avoid_section = f"""
                Éléments à éviter:
                {avoid_context}
                """
            
            prompt = f"""
            Tu es un rédacteur professionnel spécialisé dans la création d'articles de blog de haute qualité.
            
            Écris un article complet et détaillé sur le sujet suivant: "{titre}".
            
            Contexte général: {sujet}
            
            {include_section}
            
            {avoid_section}
            
            Longueur approximative: {article_length} mots
            Niveau de détail: {detail_level}/5
            
            L'article doit être bien structuré avec:
            - Une introduction engageante
            - Des sections clairement définies avec des sous-titres
            - Des paragraphes concis et informatifs
            - Une conclusion qui résume les points clés
            
            Utilise le format Markdown pour la mise en forme.
            """
            
            response = llm.invoke([HumanMessage(content=prompt)])
            content = response.content
            
            print(f"Article généré avec succès pour: {titre}")
            return {"content": content}
        except Exception as e:
            print(f"Erreur lors de la génération de l'article avec LLM: {str(e)}")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
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

if __name__ == "__main__":
    print("Démarrage du serveur API...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 