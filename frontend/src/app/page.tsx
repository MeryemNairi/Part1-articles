"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2 } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"

export default function HomePage() {
  const router = useRouter()
  const [topic, setTopic] = useState("")
  const [tone, setTone] = useState("standard")
  const [isGenerating, setIsGenerating] = useState(false)
  const [titles, setTitles] = useState<string[]>([])
  const [titleIds, setTitleIds] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [step, setStep] = useState(1) // 1: Saisie, 2: Titres générés
  const [additionalContext, setAdditionalContext] = useState("")
  const [avoidContext, setAvoidContext] = useState("")

  // Effacer les données précédentes au chargement de la page
  useEffect(() => {
    // Effacer complètement les données précédentes
    localStorage.removeItem("currentSession")
    localStorage.removeItem("generatedTitles")
    localStorage.removeItem("generatedTitleIds")
    localStorage.removeItem("generatedTopic")
    localStorage.removeItem("generatedTone")
    localStorage.removeItem("generatedArticles")
    
    // Effacer également toutes les sessions précédentes
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith("session_")) {
        localStorage.removeItem(key)
      }
    })
    
    // Réinitialiser l'état
    setTitles([])
    setTitleIds({})
    setStep(1)
  }, [])

  const generateTitles = async () => {
    if (!topic) return

    setIsGenerating(true)
    setError(null)

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

    try {
      const response = await fetch(`${apiUrl}/api/titles`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ sujet: topic, tone }),
      })

      if (!response.ok) {
        throw new Error(`Erreur: ${response.status}`)
      }

      const data = await response.json()
      setTitles(data.titles)
      setTitleIds(data.title_ids)
      
      // Créer une nouvelle session avec un ID unique
      const sessionId = Date.now().toString()
      
      // Stocker les données pour les autres pages
      const sessionData = {
        id: sessionId,
        topic: topic,
        tone: tone,
        titles: data.titles,
        titleIds: data.title_ids,
        articles: {},
        additionalContext,
        avoidContext,
        createdAt: new Date().toISOString()
      }
      
      // Sauvegarder la session actuelle
      localStorage.setItem("currentSession", sessionId)
      localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
      
      // Stocker également dans les variables globales pour la compatibilité
      localStorage.setItem("generatedTitles", JSON.stringify(data.titles))
      localStorage.setItem("generatedTitleIds", JSON.stringify(data.title_ids))
      localStorage.setItem("generatedTopic", topic)
      localStorage.setItem("generatedTone", tone)
      localStorage.setItem("generatedArticles", JSON.stringify({}))
      
      // Passer à l'étape 2
      setStep(2)
    } catch (err) {
      setError(`Une erreur s'est produite: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const regenerateTitle = async (index: number) => {
    setIsGenerating(true)
    setError(null)

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

    try {
      const response = await fetch(`${apiUrl}/api/regenerate-title`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          index,
          sujet: topic,
          tone,
          titres: titles,
        }),
      })

      if (!response.ok) {
        throw new Error(`Erreur: ${response.status}`)
      }

      const data = await response.json()
      
      // Mettre à jour le titre
      const newTitles = [...titles]
      newTitles[index] = data.title
      setTitles(newTitles)
      
      // Mettre à jour l'ID
      const newTitleIds = { ...titleIds }
      newTitleIds[data.title] = data.id
      setTitleIds(newTitleIds)
      
      // Mettre à jour la session
      const sessionId = localStorage.getItem("currentSession")
      if (sessionId) {
        const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
        sessionData.titles = newTitles
        sessionData.titleIds = newTitleIds
        localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
        
        // Mettre à jour également les variables globales
        localStorage.setItem("generatedTitles", JSON.stringify(newTitles))
        localStorage.setItem("generatedTitleIds", JSON.stringify(newTitleIds))
      }
    } catch (err) {
      setError(`Une erreur s'est produite: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleEditTitle = (index: number, newTitle: string) => {
    const newTitles = [...titles]
    newTitles[index] = newTitle
    setTitles(newTitles)
    
    // Mettre à jour la session
    const sessionId = localStorage.getItem("currentSession")
    if (sessionId) {
      const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
      sessionData.titles = newTitles
      localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
      
      // Mettre à jour également les variables globales
      localStorage.setItem("generatedTitles", JSON.stringify(newTitles))
    }
  }

  const resetForm = () => {
    // Effacer complètement les données précédentes
    localStorage.removeItem("currentSession")
    localStorage.removeItem("generatedTitles")
    localStorage.removeItem("generatedTitleIds")
    localStorage.removeItem("generatedTopic")
    localStorage.removeItem("generatedTone")
    localStorage.removeItem("generatedArticles")
    
    // Effacer également toutes les sessions précédentes
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith("session_")) {
        localStorage.removeItem(key)
      }
    })
    
    // Réinitialiser l'état
    setTitles([])
    setTitleIds({})
    setTopic("")
    setTone("standard")
    setStep(1)
    setError(null)
  }

  const navigateToArticles = () => {
    router.push("/articles")
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container max-w-4xl mx-auto px-4 py-12">
        <Card className="border-none shadow-xl bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm">
          <CardHeader className="text-center">
            <h1 className="text-3xl font-bold text-purple-600 dark:text-purple-400">
              Générateur d'Articles Complets avec IA
            </h1>
            <p className="text-slate-600 dark:text-slate-400">
              Créez des articles complets et professionnels en quelques clics
            </p>
          </CardHeader>
          
          <CardContent className="p-6 md:p-8">
            {step === 1 ? (
              <div className="space-y-6">
                <div className="space-y-4">
                  <label className="block text-sm font-medium">Thème de votre article</label>
                  <Input
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="Ex: l'intelligence artificielle, le marketing digital..."
                    className="h-12"
                  />
                </div>

                <div className="space-y-4">
                  <label className="block text-sm font-medium">Ton de l'article</label>
                  <Select value={tone} onValueChange={setTone}>
                    <SelectTrigger className="h-12">
                      <SelectValue placeholder="Choisir un ton" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="standard">Standard</SelectItem>
                      <SelectItem value="professionnel">Professionnel</SelectItem>
                      <SelectItem value="créatif">Créatif</SelectItem>
                      <SelectItem value="accrocheur">Accrocheur</SelectItem>
                      <SelectItem value="informatif">Informatif</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Éléments à inclure (facultatif)
                  </label>
                  <Textarea
                    placeholder="Points spécifiques, exemples ou informations à inclure dans l'article..."
                    value={additionalContext}
                    onChange={(e) => setAdditionalContext(e.target.value)}
                    className="min-h-[100px]"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Éléments à éviter (facultatif)
                  </label>
                  <Textarea
                    placeholder="Sujets, exemples ou informations à ne pas mentionner dans l'article..."
                    value={avoidContext}
                    onChange={(e) => setAvoidContext(e.target.value)}
                    className="min-h-[100px]"
                  />
                </div>

                <Button
                  onClick={generateTitles}
                  disabled={isGenerating || !topic}
                  className="w-full h-12 text-lg bg-gradient-to-r from-purple-600 to-blue-500 hover:from-purple-700 hover:to-blue-600"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Génération en cours...
                    </>
                  ) : (
                    "Générer des titres"
                  )}
                </Button>

                {error && (
                  <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg text-red-600 dark:text-red-400">
                    {error}
                  </div>
                )}

                <div className="bg-blue-50 dark:bg-slate-800/50 p-4 rounded-lg space-y-2">
                  <h3 className="font-semibold text-blue-700 dark:text-blue-400">
                    Conseils pour un article de qualité
                  </h3>
                  <ul className="text-sm text-slate-700 dark:text-slate-300 space-y-1 list-disc pl-5">
                    <li>Choisissez un thème précis pour un contenu ciblé</li>
                    <li>Sélectionnez le ton qui correspond à votre audience</li>
                    <li>Les articles structurés sont plus faciles à lire</li>
                    <li>Incluez des exemples concrets pour illustrer vos propos</li>
                    <li>Définissez la longueur en fonction de la complexité du sujet</li>
                  </ul>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="flex justify-between items-center">
                  <h2 className="text-xl font-semibold">Titres proposés</h2>
                  <Button variant="outline" onClick={resetForm} size="sm">
                    Nouveau sujet
                  </Button>
                </div>
                
                <div className="space-y-4">
                  {titles.map((title, index) => (
                    <div key={index} className="p-4 border rounded-lg bg-slate-50 dark:bg-slate-800/50">
                      <div className="flex items-center gap-3">
                        <span className="font-bold text-slate-400 min-w-[24px]">{index + 1}.</span>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <input
                              type="text"
                              value={title}
                              onChange={(e) => handleEditTitle(index, e.target.value)}
                              className="w-full bg-transparent border-b border-transparent hover:border-slate-300 focus:border-blue-500 focus:outline-none py-1 px-2"
                            />
                          </div>
                        </div>
                        <Button
                          onClick={() => regenerateTitle(index)}
                          disabled={isGenerating}
                          variant="ghost"
                          size="sm"
                          className="text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-refresh-cw">
                            <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
                            <path d="M21 3v5h-5" />
                            <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
                            <path d="M3 21v-5h5" />
                          </svg>
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
                
                <Button
                  onClick={navigateToArticles}
                  className="w-full h-12 text-lg bg-gradient-to-r from-purple-600 to-blue-500 hover:from-purple-700 hover:to-blue-600"
                >
                  Générer les articles
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
