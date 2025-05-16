const regenerateImage = async () => {
  setIsGeneratingImage(true);
  try {
    // Utilisez l'URL complète avec le protocole, l'hôte et le port
    const apiUrl = 'http://localhost:8000/api/generate-article-image';
    
    console.log("Appel API:", apiUrl);
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        title: article.title,
        category: article.category,
        site_description: variation.description
      }),
    });
    
    console.log("Statut de la réponse:", response.status);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error("Erreur:", errorText);
      throw new Error(`Erreur HTTP: ${response.status}`);
    }
    
    const data = await response.json();
    
    if (data.image_url) {
      // Mettre à jour l'image
      setArticleImage(data.image_url);
    }
  } catch (error) {
    console.error("Erreur:", error);
  } finally {
    setIsGeneratingImage(false);
  }
}; 