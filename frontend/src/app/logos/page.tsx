"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { ArrowLeft, ArrowRight, Loader2, RefreshCw, ImageIcon } from "lucide-react"
import Link from "next/link"

export default function LogosPage() {
  const router = useRouter()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [variations, setVariations] = useState<any[]>([])
  const [logoDescriptions, setLogoDescriptions] = useState<Record<string, string>>({})
  const [logos, setLogos] = useState<Record<string, string>>({})
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isGeneratingLogo, setIsGeneratingLogo] = useState<Record<string, boolean>>({})
  const [isGeneratingAllContent, setIsGeneratingAllContent] = useState(false)
  const [contentExists, setContentExists] = useState(false)
  const [isFirstVisit, setIsFirstVisit] = useState(true)
  const [generationProgress, setGenerationProgress] = useState(0)
  const [generationStatus, setGenerationStatus] = useState("")

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
    
    setSessionId(currentSessionId)
    setVariations(sessionData.variations)
    
    // Initialiser les descriptions de logo
    const initialDescriptions: Record<string, string> = {}
    sessionData.variations.forEach((variation: any) => {
      initialDescriptions[variation.id] = `Logo pour "${variation.title}" avec un style ${variation.style.toLowerCase()}`
    })
    setLogoDescriptions(initialDescriptions)
    
    // Récupérer les logos s'ils existent déjà
    if (sessionData.logos) {
      setLogos(sessionData.logos)
      setIsFirstVisit(false) // Ce n'est plus la première visite si des logos existent déjà
    } else {
      // C'est la première visite et aucun logo n'existe encore
      setIsFirstVisit(true)
    }

    // Vérifier si le contenu existe déjà
    if (sessionData && sessionData.variations) {
      const hasContent = sessionData.variations.some(
        (variation: any) => variation.content && 
        variation.content.articles && 
        variation.content.articles.length > 0
      )
      setContentExists(hasContent)
    }
    
    // Générer automatiquement les logos lors de la première visite
    if (isFirstVisit && !sessionData.logos) {
      // Utiliser setTimeout pour s'assurer que le composant est complètement monté
      const timer = setTimeout(() => {
        generateLogos()
        setIsFirstVisit(false)
      }, 500)
      
      return () => clearTimeout(timer)
    }
  }, [router, isFirstVisit])

  const handleDescriptionChange = (id: string, value: string) => {
    setLogoDescriptions(prev => ({
      ...prev,
      [id]: value
    }))
  }

  const handleLogoUpload = (id: string, event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files || event.target.files.length === 0) return;
    
    const file = event.target.files[0];
    if (!file.type.startsWith('image/')) {
      setError("Veuillez télécharger uniquement des fichiers image");
      return;
    }
    
    // Vérifier la taille du fichier (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      setError("Le fichier est trop volumineux. Taille maximale: 5MB");
      return;
    }
    
    setIsGenerating(true); // Montrer un indicateur de chargement
    
    const reader = new FileReader();
    reader.onload = (e) => {
      if (e.target?.result) {
        const newLogos = {...logos};
        newLogos[id] = e.target.result as string;
        setLogos(newLogos);
        
        // Mettre à jour la session
        if (sessionId) {
          const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}");
          sessionData.logos = newLogos;
          localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData));
        }
        setIsGenerating(false);
      }
    };
    reader.onerror = () => {
      setError("Erreur lors de la lecture du fichier");
      setIsGenerating(false);
    };
    reader.readAsDataURL(file);
  };

  // Fonction pour générer un prompt créatif
  const generateAutoPrompt = (id: string) => {
    // Trouver la variation correspondante
    const variation = variations.find(v => v.id === id);
    if (!variation) return;
    
    // Générer un prompt créatif basé sur le titre et le style
    const styles = {
      "Minimaliste": "épuré, simple, élégant, avec beaucoup d'espace négatif",
      "Moderne": "contemporain, géométrique, avec des lignes épurées",
      "Professionnel": "sérieux, fiable, avec une typographie claire",
      "Créatif": "artistique, coloré, avec des formes organiques",
      "Luxueux": "élégant, sophistiqué, avec des détails dorés ou argentés",
      "Ludique": "amusant, coloré, avec des formes arrondies"
    };
    
    // Obtenir le style ou utiliser un style par défaut
    const styleDescription = styles[variation.style as keyof typeof styles] || "moderne et professionnel";
    
    // Créer des prompts différents à chaque clic
    const prompts = [
      `Logo pour "${variation.title}" avec un style ${styleDescription}. Utilisez des couleurs qui évoquent la confiance et la qualité.`,
      `Créez un logo ${styleDescription} pour "${variation.title}". Le logo doit être mémorable et représenter l'essence de la marque.`,
      `Un logo distinctif pour "${variation.title}" dans un style ${styleDescription}. Incorporez des éléments visuels qui représentent le domaine d'activité.`,
      `Logo ${styleDescription} pour "${variation.title}". Utilisez une palette de couleurs harmonieuse et une typographie adaptée au secteur.`,
      `Concevez un logo ${styleDescription} pour "${variation.title}" qui soit à la fois unique et facilement reconnaissable.`
    ];
    
    // Sélectionner un prompt aléatoire
    const randomPrompt = prompts[Math.floor(Math.random() * prompts.length)];
    
    // Mettre à jour l'état
    setLogoDescriptions(prev => ({
      ...prev,
      [id]: randomPrompt
    }));
    
    // Mettre à jour la session
    if (sessionId) {
      const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}");
      if (!sessionData.logoDescriptions) {
        sessionData.logoDescriptions = {};
      }
      sessionData.logoDescriptions[id] = randomPrompt;
      localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData));
    }
  };

  const generateLogos = async () => {
    if (!sessionId) return
    
    setIsGenerating(true)
    setError(null)

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

    try {
      const response = await fetch(`${apiUrl}/api/generate-logos`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          variations: variations,
          logo_descriptions: logoDescriptions
        }),
      })

      if (!response.ok) {
        throw new Error(`Erreur: ${response.status}`)
      }

      const data = await response.json()
      
      // Mettre à jour les logos
      const newLogos: Record<string, string> = {}
      data.logos.forEach((logo: any) => {
        newLogos[logo.variation_id] = logo.logo_url
      })
      
      setLogos(newLogos)
      
      // Mettre à jour la session
      const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
      sessionData.logos = newLogos
      sessionData.logoDescriptions = logoDescriptions
      localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
    } catch (err) {
      setError(`Une erreur s'est produite: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const generateSingleLogo = async (id: string) => {
    if (!sessionId) return
    
    setIsGeneratingLogo(prev => ({
      ...prev,
      [id]: true
    }))
    setError(null)

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    
    // Trouver la variation correspondante
    const variation = variations.find(v => v.id === id)
    if (!variation) return

    try {
      const response = await fetch(`${apiUrl}/api/generate-logos`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          variations: [variation],
          logo_descriptions: {
            [id]: logoDescriptions[id]
          }
        }),
      })

      if (!response.ok) {
        throw new Error(`Erreur: ${response.status}`)
      }

      const data = await response.json()
      
      if (data.logos && data.logos.length > 0) {
        // Mettre à jour le logo
        const newLogos = {...logos}
        newLogos[id] = data.logos[0].logo_url
        setLogos(newLogos)
        
        // Mettre à jour la session
        const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
        if (!sessionData.logos) {
          sessionData.logos = {}
        }
        sessionData.logos[id] = data.logos[0].logo_url
        localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
      }
    } catch (err) {
      setError(`Une erreur s'est produite: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsGeneratingLogo(prev => ({
        ...prev,
        [id]: false
      }))
    }
  }

  const navigateToContent = () => {
    if (!sessionId) return
    
    // Vérifier si tous les logos ont été générés
    const allLogosGenerated = variations.every(variation => logos[variation.id])
    
    if (!allLogosGenerated) {
      if (!confirm("Certains logos n'ont pas été générés. Voulez-vous continuer quand même?")) {
        return
      }
    }
    
    router.push("/content")
  }

  // Ajoutez cette fonction pour naviguer vers la page de contenu spécifique à une variation
  const navigateToSiteContent = (variationId: string) => {
    try {
      if (!sessionId) {
        console.error("Pas de sessionId disponible");
        return;
      }
      
      // Sauvegarder la variation sélectionnée dans la session
      const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}");
      sessionData.selectedVariation = variationId;
      localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData));
      
      console.log("Navigation vers /articles avec variationId:", variationId);
      
      // Forcer la navigation avec window.location comme solution de contournement
      window.location.href = "/articles";
      
      // Si le routeur Next.js fonctionne, utilisez-le
      // router.push("/articles");
    } catch (error) {
      console.error("Erreur lors de la navigation:", error);
      // Afficher l'erreur à l'utilisateur
      setError(`Une erreur s'est produite: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  const generateAllContent = async () => {
    if (!sessionId) return
    
    setIsGeneratingAllContent(true)
    setError(null)
    setGenerationProgress(0)
    setGenerationStatus("Initialisation...")

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const totalVariations = variations.length;

    try {
      // Simuler la progression pendant la génération
      const progressInterval = setInterval(() => {
        setGenerationProgress(prev => {
          if (prev >= 95) {
            clearInterval(progressInterval);
            return 95;
          }
          const newProgress = prev + (5 / totalVariations);
          
          // Mettre à jour le statut en fonction de la progression
          if (newProgress < 30) {
            setGenerationStatus("Génération des titres d'articles...");
          } else if (newProgress < 60) {
            setGenerationStatus("Rédaction des articles...");
          } else if (newProgress < 90) {
            setGenerationStatus("Finalisation du contenu...");
          }
          
          return Math.min(newProgress, 95);
        });
      }, 1000);

      // Récupérer les données de la session pour obtenir les logos
      const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
      
      // Préparer les variations avec les logos mais sans le contenu existant
      const variationsForRegeneration = variations.map(variation => {
        // Créer une copie de la variation sans le contenu existant
        const { content, ...variationWithoutContent } = variation;
        
        return {
          ...variationWithoutContent,
          // Conserver uniquement le logo
          logo: sessionData.logos && sessionData.logos[variation.id] ? sessionData.logos[variation.id] : null
        }
      });

      const response = await fetch(`${apiUrl}/api/generate-all-content`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          variations: variationsForRegeneration,
          forceRegenerate: true  // Indiquer au backend de régénérer le contenu
        }),
      });

      // Arrêter l'intervalle une fois la réponse reçue
      clearInterval(progressInterval);
      
      if (!response.ok) {
        throw new Error(`Erreur: ${response.status}`)
      }

      const data = await response.json()
      
      if (data.error) {
        throw new Error(data.error)
      }
      
      // Mettre à jour les variations avec le contenu généré
      if (data.variations) {
        // Compléter la progression à 100%
        setGenerationProgress(100);
        setGenerationStatus("Contenu régénéré avec succès!");
        
        // Mettre à jour la session en conservant les logos
        const updatedSessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
        updatedSessionData.variations = data.variations
        
        // S'assurer que les logos sont conservés
        if (!updatedSessionData.logos && sessionData.logos) {
          updatedSessionData.logos = sessionData.logos
        }
        
        localStorage.setItem(`session_${sessionId}`, JSON.stringify(updatedSessionData))
        
        // Attendre un court instant pour montrer le 100% avant de rediriger
        setTimeout(() => {
          window.location.href = "/content"
        }, 1000);
      }
    } catch (err) {
      setError(`Une erreur s'est produite: ${err instanceof Error ? err.message : String(err)}`)
      setGenerationStatus("Échec de la génération");
    } finally {
      if (generationProgress < 100) {
        setGenerationProgress(0);
      }
      setIsGeneratingAllContent(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container max-w-6xl mx-auto px-4 py-12">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push('/')}
              className="flex items-center gap-1"
            >
              <ArrowLeft className="h-4 w-4" />
              Retour à l'accueil
            </Button>
            <h1 className="text-2xl md:text-3xl font-bold ml-2">Création des Logos</h1>
          </div>
          
          <div>
            <span className="text-sm text-slate-500 dark:text-slate-400">Étape 2/3</span>
          </div>
        </div>
        
        <Card className="border-none shadow-xl bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm">
          <CardHeader className="p-6 border-b">
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-2">
                <Link
                  href="/"
                  className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
                >
                  <ArrowLeft className="h-5 w-5" />
                  <span className="sr-only">Retour à l'étape 1</span>
                </Link>
                <h1 className="text-2xl md:text-3xl font-bold">Création des Logos</h1>
              </div>
              
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-500 dark:text-slate-400">Étape 2/3</span>
                {contentExists && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => router.push('/content')}
                    className="flex items-center gap-1"
                  >
                    Voir le contenu généré
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>
          
          <CardContent className="p-6">
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg text-red-600 dark:text-red-400 mb-6">
                {error}
              </div>
            )}
            
            <div className="space-y-8">
              {variations.map((variation) => (
                <div key={variation.id} className="border rounded-lg p-4 bg-slate-50 dark:bg-slate-800/50">
                  <h2 className="text-xl font-semibold mb-2">{variation.title}</h2>
                  <p className="text-slate-600 dark:text-slate-400 mb-4">{variation.description}</p>
                  
                  <div className="grid md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium mb-2">Description du logo</label>
                      <Textarea
                        value={logoDescriptions[variation.id] || ""}
                        onChange={(e) => handleDescriptionChange(variation.id, e.target.value)}
                        placeholder="Décrivez le logo que vous souhaitez..."
                        className="min-h-[100px]"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium mb-2">Aperçu du logo</label>
                      {logos[variation.id] ? (
                        <div className="relative bg-white dark:bg-slate-700 rounded-lg p-4 flex items-center justify-center h-[150px]">
                          <img 
                            src={logos[variation.id]} 
                            alt={`Logo pour ${variation.title}`} 
                            className="max-h-full max-w-full object-contain"
                          />
                          <div className="absolute top-2 right-2 flex gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => generateSingleLogo(variation.id)}
                              disabled={isGeneratingLogo[variation.id]}
                            >
                              {isGeneratingLogo[variation.id] ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <RefreshCw className="h-4 w-4" />
                              )}
                            </Button>
                            
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => document.getElementById(`logo-upload-${variation.id}`)?.click()}
                            >
                              <ImageIcon className="h-4 w-4" />
                            </Button>
                            <input
                              id={`logo-upload-${variation.id}`}
                              type="file"
                              accept="image/*"
                              className="hidden"
                              onChange={(e) => handleLogoUpload(variation.id, e)}
                            />
                          </div>
                        </div>
                      ) : (
                        <div className="bg-white dark:bg-slate-700 rounded-lg p-4 flex flex-col items-center justify-center h-[150px] gap-3">
                          <Button
                            onClick={() => generateSingleLogo(variation.id)}
                            disabled={isGeneratingLogo[variation.id]}
                          >
                            {isGeneratingLogo[variation.id] ? (
                              <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Génération...
                              </>
                            ) : (
                              <>
                                Générer un logo
                              </>
                            )}
                          </Button>
                          
                          <div className="text-center text-xs text-slate-500 dark:text-slate-400">
                            ou
                          </div>
                          
                          <div>
                            <label htmlFor={`logo-upload-${variation.id}`} className="cursor-pointer text-sm text-blue-600 dark:text-blue-400 hover:underline">
                              Télécharger un logo
                            </label>
                            <input
                              id={`logo-upload-${variation.id}`}
                              type="file"
                              accept="image/*"
                              className="hidden"
                              onChange={(e) => handleLogoUpload(variation.id, e)}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
          
          <CardFooter className="p-6 border-t">
            <div className="mt-8 flex flex-col items-center w-full">
              {isGeneratingAllContent ? (
                <div className="w-full flex flex-col items-center gap-4 mb-4">
                  <div className="relative h-24 w-24">
                    <svg className="h-24 w-24" viewBox="0 0 100 100">
                      <circle 
                        className="text-slate-200 dark:text-slate-700" 
                        strokeWidth="8" 
                        stroke="currentColor" 
                        fill="transparent" 
                        r="42" 
                        cx="50" 
                        cy="50" 
                      />
                      <circle 
                        className="text-indigo-600 dark:text-indigo-400" 
                        strokeWidth="8" 
                        strokeLinecap="round" 
                        stroke="currentColor" 
                        fill="transparent" 
                        r="42" 
                        cx="50" 
                        cy="50" 
                        strokeDasharray={`${2 * Math.PI * 42}`}
                        strokeDashoffset={`${2 * Math.PI * 42 * (1 - generationProgress / 100)}`}
                        style={{ transition: "stroke-dashoffset 0.5s ease" }}
                      />
                      <text 
                        x="50" 
                        y="50" 
                        textAnchor="middle" 
                        dominantBaseline="middle" 
                        className="text-2xl font-bold text-slate-700 dark:text-slate-200"
                      >
                        {Math.round(generationProgress)}%
                      </text>
                    </svg>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-medium text-slate-700 dark:text-slate-300">{generationStatus}</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Veuillez patienter pendant la génération du contenu...</p>
                  </div>
                </div>
              ) : (
                <Button
                  onClick={generateAllContent}
                  className="w-full md:w-auto bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700"
                >
                  Générer le contenu pour tous les sites
                </Button>
              )}
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
} 