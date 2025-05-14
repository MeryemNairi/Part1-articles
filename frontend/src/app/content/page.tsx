"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, ArrowLeft, ArrowRight, Edit2, RefreshCw } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"
import Link from "next/link"

export default function ContentPage() {
  const router = useRouter()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [variations, setVariations] = useState<any[]>([])
  const [logos, setLogos] = useState<Record<string, string>>({})
  const [selectedVariation, setSelectedVariation] = useState<string | null>(null)
  const [topic, setTopic] = useState("")
  const [tone, setTone] = useState("standard")
  const [isGenerating, setIsGenerating] = useState(false)
  const [titles, setTitles] = useState<Record<string, string[]>>({})
  const [error, setError] = useState<string | null>(null)
  const [additionalContext, setAdditionalContext] = useState("")
  const [avoidContext, setAvoidContext] = useState("")
  const [editingTitleIndex, setEditingTitleIndex] = useState<string | null>(null)
  const [editedTitle, setEditedTitle] = useState("")
  const [isRegeneratingTitle, setIsRegeneratingTitle] = useState<Record<string, boolean>>({})

  useEffect(() => {
    // Récupérer l'ID de la session actuelle
    const currentSessionId = localStorage.getItem("currentSession")
    
    if (!currentSessionId) {
      router.push("/")
      return
    }
    
    // Récupérer les données de la session
    const sessionData = JSON.parse(localStorage.getItem(`session_${currentSessionId}`) || "{}")
    
    if (!sessionData || !sessionData.variations || !sessionData.logos) {
      router.push("/logos")
      return
    }
    
    setSessionId(currentSessionId)
    setVariations(sessionData.variations)
    setLogos(sessionData.logos)
    
    // Sélectionner la variation par défaut (celle qui a été choisie dans la page des logos)
    if (sessionData.selectedVariation) {
      setSelectedVariation(sessionData.selectedVariation)
    } else if (sessionData.variations.length > 0) {
      setSelectedVariation(sessionData.variations[0].id)
    }
    
    // Récupérer les titres s'ils existent déjà
    if (sessionData.titles) {
      setTitles(sessionData.titles)
    }
    
    // Si une variation est sélectionnée mais n'a pas de titres, générer automatiquement des titres
    if (sessionData.selectedVariation && 
        (!sessionData.titles || !sessionData.titles[sessionData.selectedVariation])) {
      // Attendre que les états soient mis à jour avant de générer les titres
      setTimeout(() => {
        if (sessionData.selectedVariation) {
          setSelectedVariation(sessionData.selectedVariation)
          // Générer les titres automatiquement après un court délai
          setTimeout(() => generateTitles(), 500)
        }
      }, 100)
    }
  }, [router])

  const generateTitles = async () => {
    if (!sessionId || !selectedVariation) return

    setIsGenerating(true)
    setError(null)

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    
    // Trouver la variation sélectionnée
    const variation = variations.find(v => v.id === selectedVariation)
    if (!variation) {
      setError("Variation non trouvée")
      setIsGenerating(false)
      return
    }

    try {
      const response = await fetch(`${apiUrl}/api/titles`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          sujet: variation.title, 
          tone,
          additional_context: additionalContext,
          avoid_context: avoidContext
        }),
      })

      if (!response.ok) {
        throw new Error(`Erreur: ${response.status}`)
      }

      const data = await response.json()
      
      // Mettre à jour les titres
      setTitles(prev => ({
        ...prev,
        [selectedVariation]: data.titles
      }))
      
      // Mettre à jour la session
      const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
      if (!sessionData.titles) {
        sessionData.titles = {}
      }
      sessionData.titles[selectedVariation] = data.titles
      localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
    } catch (err) {
      setError(`Une erreur s'est produite: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const navigateToArticles = () => {
    if (!sessionId || !selectedVariation) return
    
    // Vérifier si des titres ont été générés pour la variation sélectionnée
    if (!titles[selectedVariation] || titles[selectedVariation].length === 0) {
      setError("Veuillez générer des titres avant de continuer")
      return
    }
    
    // Mettre à jour la session avec les informations supplémentaires
    const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
    sessionData.selectedVariation = selectedVariation
    sessionData.topic = variations.find(v => v.id === selectedVariation)?.title || ""
    sessionData.tone = tone
    sessionData.additionalContext = additionalContext
    sessionData.avoidContext = avoidContext
    localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
    
    // Rediriger vers la page des articles
    router.push("/articles")
  }

  const startEditingTitle = (variationId: string, index: number) => {
    const titleKey = `${variationId}_${index}`;
    setEditingTitleIndex(titleKey);
    setEditedTitle(titles[variationId]?.[index] || "");
  };

  const saveEditedTitle = () => {
    if (!editingTitleIndex || !selectedVariation) return;
    
    const [variationId, indexStr] = editingTitleIndex.split('_');
    const index = parseInt(indexStr);
    
    if (isNaN(index) || !titles[variationId]) return;
    
    // Créer une copie des titres actuels
    const newTitles = { ...titles };
    const variationTitles = [...newTitles[variationId]];
    variationTitles[index] = editedTitle;
    newTitles[variationId] = variationTitles;
    
    // Mettre à jour l'état
    setTitles(newTitles);
    
    // Mettre à jour la session
    if (sessionId) {
      const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}");
      if (!sessionData.titles) {
        sessionData.titles = {};
      }
      sessionData.titles[variationId] = variationTitles;
      localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData));
    }
    
    // Réinitialiser l'état d'édition
    setEditingTitleIndex(null);
  };

  const regenerateTitle = async (variationId: string, index: number) => {
    if (!sessionId || !selectedVariation) return;
    
    const titleKey = `${variationId}_${index}`;
    
    // Mettre à jour l'état pour afficher l'indicateur de chargement
    setIsRegeneratingTitle(prev => ({
      ...prev,
      [titleKey]: true
    }));
    
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    try {
      // Trouver la variation correspondante
      const variation = variations.find(v => v.id === variationId);
      if (!variation) return;
      
      // Utiliser l'API existante pour générer un nouveau titre
      const response = await fetch(`${apiUrl}/api/titles`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sujet: topic,
          tone: tone,
          additional_context: additionalContext,
          avoid_context: avoidContext,
          single_title: true  // Indiquer que nous voulons un seul titre
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Erreur: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Extraire le titre généré (prendre le premier si l'API renvoie plusieurs titres)
      const newTitle = data.titles && data.titles.length > 0 ? data.titles[0] : null;
      
      if (newTitle) {
        // Mettre à jour le titre spécifique
        const newTitles = { ...titles };
        const variationTitles = [...(newTitles[variationId] || [])];
        variationTitles[index] = newTitle;
        newTitles[variationId] = variationTitles;
        
        setTitles(newTitles);
        
        // Mettre à jour la session
        const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}");
        if (!sessionData.titles) {
          sessionData.titles = {};
        }
        sessionData.titles[variationId] = variationTitles;
        localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData));
      }
    } catch (error) {
      console.error("Erreur lors de la régénération du titre:", error);
      setError(`Une erreur s'est produite lors de la régénération du titre: ${error}`);
    } finally {
      // Réinitialiser l'état de chargement
      setIsRegeneratingTitle(prev => ({
        ...prev,
        [titleKey]: false
      }));
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container max-w-4xl mx-auto px-4 py-12">
        <Card className="border-none shadow-xl bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm">
          <CardHeader className="p-6 border-b">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Link
                  href="/logos"
                  className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
                >
                  <ArrowLeft className="h-5 w-5" />
                  <span className="sr-only">Retour aux logos</span>
                </Link>
                <h1 className="text-2xl md:text-3xl font-bold">Création du Contenu</h1>
              </div>
              
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-500 dark:text-slate-400">Étape 3/3</span>
              </div>
            </div>
          </CardHeader>
          
          <CardContent className="p-6">
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg text-red-600 dark:text-red-400 mb-6">
                {error}
              </div>
            )}
            
            <div className="space-y-6">
              <div className="space-y-4">
                <label className="block text-sm font-medium">Sélectionnez un site web</label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {variations.map((variation) => (
                    <div
                      key={variation.id}
                      className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                        selectedVariation === variation.id
                          ? "border-purple-500 bg-purple-50 dark:bg-purple-900/20"
                          : "bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800"
                      }`}
                      onClick={() => setSelectedVariation(variation.id)}
                    >
                      <div className="flex flex-col items-center">
                        {logos[variation.id] && (
                          <div className="w-16 h-16 mb-2">
                            <img
                              src={logos[variation.id]}
                              alt={`Logo pour ${variation.title}`}
                              className="w-full h-full object-contain"
                            />
                          </div>
                        )}
                        <h3 className="font-medium text-center">{variation.title}</h3>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              
              {selectedVariation && (
                <div className="space-y-6 pt-4 border-t">
                  <h2 className="text-xl font-semibold">
                    Paramètres de génération pour {variations.find(v => v.id === selectedVariation)?.title}
                  </h2>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <label className="block text-sm font-medium">Ton des articles</label>
                      <Select value={tone} onValueChange={setTone}>
                        <SelectTrigger>
                          <SelectValue placeholder="Choisir un ton" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="standard">Standard</SelectItem>
                          <SelectItem value="professionnel">Professionnel</SelectItem>
                          <SelectItem value="amical">Amical</SelectItem>
                          <SelectItem value="informatif">Informatif</SelectItem>
                          <SelectItem value="persuasif">Persuasif</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="space-y-4">
                      <label className="block text-sm font-medium">Contexte supplémentaire (optionnel)</label>
                      <Textarea
                        value={additionalContext}
                        onChange={(e) => setAdditionalContext(e.target.value)}
                        placeholder="Informations supplémentaires à inclure..."
                      />
                    </div>
                    
                    <div className="space-y-4">
                      <label className="block text-sm font-medium">Éléments à éviter (optionnel)</label>
                      <Textarea
                        value={avoidContext}
                        onChange={(e) => setAvoidContext(e.target.value)}
                        placeholder="Sujets ou éléments à éviter..."
                      />
                    </div>
                  </div>
                  
                  <div className="pt-4">
                    <Button
                      onClick={generateTitles}
                      disabled={isGenerating}
                      className="w-full bg-gradient-to-r from-purple-600 to-blue-500 hover:from-purple-700 hover:to-blue-600"
                    >
                      {isGenerating ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Génération des titres...
                        </>
                      ) : (
                        "Générer des titres d'articles"
                      )}
                    </Button>
                  </div>
                  
                  {selectedVariation && titles[selectedVariation] && titles[selectedVariation].length > 0 && (
                    <div className="pt-6 border-t mt-6">
                      <h3 className="text-lg font-medium mb-4">Titres générés</h3>
                      <div className="space-y-3">
                        {titles[selectedVariation].map((title, index) => {
                          const titleKey = `${selectedVariation}_${index}`;
                          return (
                            <div
                              key={index}
                              className="p-3 border rounded-lg bg-slate-50 dark:bg-slate-800/50"
                            >
                              {editingTitleIndex === titleKey ? (
                                <div className="flex items-center gap-2">
                                  <span className="font-bold text-slate-400">{index + 1}.</span>
                                  <Input
                                    value={editedTitle}
                                    onChange={(e) => setEditedTitle(e.target.value)}
                                    className="flex-1"
                                  />
                                  <Button size="sm" onClick={saveEditedTitle}>
                                    Enregistrer
                                  </Button>
                                </div>
                              ) : (
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <span className="font-bold text-slate-400">{index + 1}.</span>
                                    <p>{title}</p>
                                  </div>
                                  <div className="flex gap-2">
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => startEditingTitle(selectedVariation, index)}
                                    >
                                      <Edit2 className="h-4 w-4" />
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => regenerateTitle(selectedVariation, index)}
                                      disabled={isRegeneratingTitle[titleKey]}
                                    >
                                      {isRegeneratingTitle[titleKey] ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                      ) : (
                                        <RefreshCw className="h-4 w-4" />
                                      )}
                                    </Button>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </CardContent>
          
          <CardFooter className="p-6 border-t flex justify-between">
            <Button variant="outline" onClick={() => router.push("/logos")}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Retour aux logos
            </Button>
            
            <Button
              onClick={navigateToArticles}
              className="bg-gradient-to-r from-purple-600 to-blue-500 hover:from-purple-700 hover:to-blue-600"
              disabled={!selectedVariation || !titles[selectedVariation] || titles[selectedVariation].length === 0}
            >
              Continuer vers les articles
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  ) 
} 