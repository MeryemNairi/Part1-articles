"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { ArrowLeft, ArrowRight, Loader2, RefreshCw } from "lucide-react"
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
    }
  }, [router])

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
      
      console.log("Navigation vers /content avec variationId:", variationId);
      
      // Rediriger vers la page de contenu
      router.push("/content");
    } catch (error) {
      console.error("Erreur lors de la navigation:", error);
      setError(`Une erreur s'est produite: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container max-w-4xl mx-auto px-4 py-12">
        <Card className="border-none shadow-xl bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm">
          <CardHeader className="p-6 border-b">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
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
                      <div className="mt-2 flex justify-start">
                        <button
                          onClick={() => generateAutoPrompt(variation.id)}
                          className="relative px-6 py-2 text-sm font-medium text-black bg-gradient-to-r from-purple-400 via-blue-300 to-purple-400 rounded-full shadow-lg hover:shadow-xl transition-all duration-300 overflow-hidden group"
                        >
                          <span className="absolute inset-0 w-full h-full bg-gradient-to-r from-blue-300 to-purple-400 opacity-0 group-hover:opacity-100 transition-opacity duration-300 blur-xl"></span>
                          <span className="relative flex items-center justify-center">
                            <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                              <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="currentColor" />
                            </svg>
                            Prompt créatif
                          </span>
                        </button>
                      </div>
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
                            <label className="cursor-pointer">
                              <Input 
                                type="file" 
                                accept="image/*" 
                                className="hidden"
                                onChange={(e) => handleLogoUpload(variation.id, e)}
                              />
                              <div className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3 py-2">
                                Remplacer
                              </div>
                            </label>
                          </div>
                        </div>
                      ) : (
                        <div className="bg-slate-200 dark:bg-slate-700 rounded-lg p-4 flex items-center justify-center h-[150px] flex-col gap-2">
                          <p className="text-slate-500 dark:text-slate-400 text-center">
                            Aucun logo généré
                          </p>
                          <div className="flex gap-2">
                            <Button
                              onClick={() => generateSingleLogo(variation.id)}
                              disabled={isGeneratingLogo[variation.id]}
                              variant="outline"
                              size="sm"
                            >
                              {isGeneratingLogo[variation.id] ? (
                                <>
                                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                  Génération...
                                </>
                              ) : (
                                <>
                                  <RefreshCw className="mr-2 h-4 w-4" />
                                  Générer
                                </>
                              )}
                            </Button>
                            <label className="cursor-pointer">
                              <Input 
                                type="file" 
                                accept="image/*" 
                                className="hidden"
                                onChange={(e) => handleLogoUpload(variation.id, e)}
                              />
                              <div className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3 py-2">
                                Télécharger
                              </div>
                            </label>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Ajouter un bouton "Continuer" pour chaque variation */}
                  <div className="mt-4 flex justify-end">
                    <Button
                      onClick={() => navigateToSiteContent(variation.id)}
                      className="bg-gradient-to-r from-purple-600 to-blue-500 hover:from-purple-700 hover:to-blue-600"
                    >
                      Générer du contenu pour ce site
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </div>
                </div>
              ))}
              
              <div className="flex justify-between">
                <Button variant="outline" onClick={() => router.push("/")}>
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Retour
                </Button>
                
                <Button
                  onClick={generateLogos}
                  disabled={isGenerating}
                  className="bg-gradient-to-r from-purple-600 to-blue-500 hover:from-purple-700 hover:to-blue-600"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Génération...
                    </>
                  ) : (
                    "Générer tous les logos"
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
} 