# Générateur de Titres d'Articles avec IA

Une application qui utilise l'IA pour générer des titres d'articles accrocheurs à partir d'un sujet général.

## Fonctionnalités

- Génération de 5 titres d'articles à partir d'un sujet
- Personnalisation du ton des titres
- Historique des générations précédentes
- Interface utilisateur intuitive

## Installation

1. Cloner le dépôt
2. Installer les dépendances: `pip install -r requirements.txt`
3. Créer un fichier `.env` avec votre clé API OpenAI
4. Lancer l'application: `streamlit run app.py`

## Technologies utilisées

- Streamlit pour l'interface utilisateur
- CrewAI pour l'orchestration des agents IA
- LangChain pour l'intégration avec les modèles de langage
