"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardFooter } from "@/components/ui/card"
import { Loader2, ArrowLeft, FileText, RefreshCw } from "lucide-react"
import Link from "next/link"
import { toast } from "@/components/ui/use-toast"

// Définir une interface pour l'article
interface Article {
  title: string;
  content: string;
  isValidated?: boolean;
}

export default function ContentPage() {
  const router = useRouter()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [variations, setVariations] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isRegeneratingContent, setIsRegeneratingContent] = useState<Record<string, boolean>>({})
  const [regenerationProgress, setRegenerationProgress] = useState<Record<string, number>>({})
  const [isExporting, setIsExporting] = useState<string | null>(null)

  useEffect(() => {
    // Récupérer l'ID de la session actuelle
    const currentSessionId = localStorage.getItem("currentSession")
    
    if (!currentSessionId) {
      router.push("/")
      return
    }
    
    // Récupérer les données de la session
    const sessionData = JSON.parse(localStorage.getItem(`session_${currentSessionId}`) || "{}")
    
    if (!sessionData || !sessionData.variations) {
      router.push("/")
      return
    }
    
    console.log("Données de session chargées:", sessionData)
    
    setSessionId(currentSessionId)
    
    // Récupérer les logos s'ils existent
    if (sessionData.logos) {
      // Mettre à jour les variations avec les logos
      const variationsWithLogos = sessionData.variations.map((variation: any, index: number) => {
        return {
          ...variation,
          logo: sessionData.logos[variation.id] || null
        }
      })
      
      setVariations(variationsWithLogos)
    } else {
      setVariations(sessionData.variations)
    }
    
    setIsLoading(false)
  }, [router])

  const navigateToArticle = (variationIndex: number, articleIndex: number) => {
    if (!sessionId) return
    
    try {
      console.log(`Navigation vers l'article: variation=${variationIndex}, article=${articleIndex}`)
      
      // Stocker l'article sélectionné dans la session
      const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
      
      // Récupérer l'article
      const variation = sessionData.variations[variationIndex]
      const article = variation.content.articles[articleIndex]
      
      console.log("Article trouvé:", article.title)
      
      // Stocker l'article dans la structure attendue par votre page d'article existante
      if (!sessionData.articles) {
        sessionData.articles = []
      }
      
      // Ajouter l'article à la liste des articles si nécessaire
      if (!sessionData.articles.some((a: Article) => a.title === article.title)) {
        sessionData.articles.push({
          title: article.title,
          content: article.content,
          isValidated: false
        })
      }
      
      // Trouver l'index de l'article dans la liste des articles
      const articleId = sessionData.articles.findIndex((a: Article) => a.title === article.title)
      
      console.log(`ID de l'article: ${articleId}`)
      
      // Sauvegarder les modifications
      localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
      
      // Utiliser window.location pour une navigation forcée
      window.location.href = `/articles/${articleId}`
    } catch (err) {
      console.error("Erreur lors de la navigation:", err)
    }
  }

  const regenerateSiteContent = async (variationIndex: number) => {
    if (!sessionId) return;
    
    const variationId = variations[variationIndex].id;
    
    setIsRegeneratingContent(prev => ({
      ...prev,
      [variationId]: true
    }));
    
    setRegenerationProgress(prev => ({
      ...prev,
      [variationId]: 0
    }));
    
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    try {
      // Simuler la progression pendant la génération
      const progressInterval = setInterval(() => {
        setRegenerationProgress(prev => {
          const currentProgress = prev[variationId] || 0;
          if (currentProgress >= 95) {
            clearInterval(progressInterval);
            return {
              ...prev,
              [variationId]: 95
            };
          }
          return {
            ...prev,
            [variationId]: Math.min(currentProgress + 5, 95)
          };
        });
      }, 500);
      
      // Récupérer les données de la session pour obtenir les logos
      const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}");
      
      // Préparer la variation sans le contenu existant
      const { content, ...variationWithoutContent } = variations[variationIndex];
      
      const variationForRegeneration = {
        ...variationWithoutContent,
        logo: sessionData.logos && sessionData.logos[variationId] ? sessionData.logos[variationId] : null
      };
      
      const response = await fetch(`${apiUrl}/api/generate-all-content`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          variations: [variationForRegeneration],
          forceRegenerate: true
        }),
      });
      
      // Arrêter l'intervalle une fois la réponse reçue
      clearInterval(progressInterval);
      
      if (!response.ok) {
        throw new Error(`Erreur: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Mettre à jour la variation avec le contenu généré
      if (data.variations && data.variations.length > 0) {
        // Compléter la progression à 100%
        setRegenerationProgress(prev => ({
          ...prev,
          [variationId]: 100
        }));
        
        // Mettre à jour la session
        const updatedSessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}");
        
        // Mettre à jour uniquement la variation spécifique
        const updatedVariations = [...updatedSessionData.variations];
        updatedVariations[variationIndex] = {
          ...updatedVariations[variationIndex],
          content: data.variations[0].content
        };
        
        updatedSessionData.variations = updatedVariations;
        localStorage.setItem(`session_${sessionId}`, JSON.stringify(updatedSessionData));
        
        // Mettre à jour l'état local
        setVariations(updatedVariations);
        
        // Attendre un court instant pour montrer le 100%
        setTimeout(() => {
          setRegenerationProgress(prev => ({
            ...prev,
            [variationId]: 0
          }));
          
          setIsRegeneratingContent(prev => ({
            ...prev,
            [variationId]: false
          }));
        }, 1000);
      }
    } catch (err) {
      setError(`Une erreur s'est produite: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      if (regenerationProgress[variationId] < 100) {
        setRegenerationProgress(prev => ({
          ...prev,
          [variationId]: 0
        }));
      }
      
      setTimeout(() => {
        setIsRegeneratingContent(prev => ({
          ...prev,
          [variationId]: false
        }));
      }, 1000);
    }
  };

  // Fonction pour exporter le site au format WordPress
  const exportWordPressTemplate = async (variationId: string) => {
    if (!sessionId) return;
    
    setIsExporting(variationId);
    
    try {
      // Récupérer les données de la variation
      const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}");
      const variation = sessionData.variations.find((v: any) => v.id === variationId);
      
      if (!variation) {
        throw new Error("Variation non trouvée");
      }
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      const response = await fetch(`${apiUrl}/api/export-wordpress-template`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          variation_id: variationId,
          variation_data: variation
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Erreur: ${response.status}`);
      }
      
      // Télécharger le fichier
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${variation.title}_export.xml`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
    } catch (err) {
      console.error("Erreur lors de l'exportation:", err);
      toast.error("Impossible d'exporter le template WordPress");
    } finally {
      setIsExporting("");
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container max-w-6xl mx-auto px-4 py-12">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-2">
            <Link
              href="/logos"
              className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
            >
              <ArrowLeft className="h-5 w-5" />
              <span className="sr-only">Retour à l'étape 2</span>
            </Link>
            <h1 className="text-2xl md:text-3xl font-bold">Contenu des Sites</h1>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-500 dark:text-slate-400">Étape 3/3</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push('/logos')}
              className="flex items-center gap-1"
            >
              <ArrowLeft className="h-4 w-4" />
              Retour aux logos
            </Button>
          </div>
        </div>
        
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg text-red-600 dark:text-red-400 mb-6">
            {error}
          </div>
        )}
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {variations.map((variation, variationIndex) => (
            <Card key={variationIndex} className="overflow-hidden border-none shadow-lg bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm">
              <CardHeader className="p-6 border-b relative">
                <h2 className="text-xl font-bold">{variation.title}</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">{variation.description}</p>
                
                {/* Bouton de régénération */}
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute top-4 right-4 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  onClick={() => regenerateSiteContent(variationIndex)}
                  disabled={isRegeneratingContent[variation.id]}
                >
                  {isRegeneratingContent[variation.id] ? (
                    <div className="relative h-6 w-6">
                      <svg className="h-6 w-6" viewBox="0 0 24 24">
                        <circle 
                          className="text-slate-200 dark:text-slate-700" 
                          strokeWidth="2" 
                          stroke="currentColor" 
                          fill="transparent" 
                          r="10" 
                          cx="12" 
                          cy="12" 
                        />
                        <circle 
                          className="text-indigo-600 dark:text-indigo-400" 
                          strokeWidth="2" 
                          strokeLinecap="round" 
                          stroke="currentColor" 
                          fill="transparent" 
                          r="10" 
                          cx="12" 
                          cy="12" 
                          strokeDasharray={`${2 * Math.PI * 10}`}
                          strokeDashoffset={`${2 * Math.PI * 10 * (1 - (regenerationProgress[variation.id] || 0) / 100)}`}
                          style={{ transition: "stroke-dashoffset 0.5s ease" }}
                        />
                      </svg>
                    </div>
                  ) : (
                    <RefreshCw className="h-5 w-5 font-bold stroke-[2.5px]" />
                  )}
                  <span className="sr-only">Régénérer le contenu</span>
                </Button>
              </CardHeader>
              
              <CardContent className="p-6">
                {/* Logo du site */}
                <div className="mb-6">
                  {variation.logo ? (
                    <div className="bg-white dark:bg-slate-800 rounded-lg p-4 flex items-center justify-center h-[120px]">
                      <img 
                        src={variation.logo} 
                        alt={`Logo pour ${variation.title}`} 
                        className="max-h-full max-w-full object-contain"
                      />
                    </div>
                  ) : (
                    <div className="bg-slate-100 dark:bg-slate-800 rounded-lg p-4 flex items-center justify-center h-[120px]">
                      <span className="text-slate-400 dark:text-slate-500">Logo non disponible</span>
                    </div>
                  )}
                </div>
                
                {/* Articles */}
                <div>
                  <h3 className="text-lg font-semibold mb-3">Articles</h3>
                  
                  {variation.content && variation.content.articles && variation.content.articles.length > 0 ? (
                    <ul className="space-y-2">
                      {variation.content.articles.map((article: any, articleIndex: number) => (
                        <li key={articleIndex}>
                          <button
                            onClick={() => navigateToArticle(variationIndex, articleIndex)}
                            className="w-full text-left p-3 bg-slate-50 dark:bg-slate-800 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors flex items-center gap-2"
                          >
                            <FileText className="h-4 w-4 text-blue-500 dark:text-blue-400 flex-shrink-0" />
                            <span className="text-blue-600 dark:text-blue-400 font-medium">{article.title}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="text-center p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                      <p className="text-slate-500 dark:text-slate-400">Aucun article disponible</p>
                    </div>
                  )}
                </div>
              </CardContent>
              
              <CardFooter className="p-6 border-t">
                <Button
                  onClick={() => exportWordPressTemplate(variation.id)}
                  disabled={isExporting === variation.id}
                  className="w-full"
                >
                  {isExporting === variation.id ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Exportation...
                    </>
                  ) : (
                    "Voir le site complet"
                  )}
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
} 