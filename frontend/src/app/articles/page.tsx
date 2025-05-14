"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { ArrowLeft, Loader2 } from "lucide-react"

export default function ArticlesPage() {
  const router = useRouter()
  const [titles, setTitles] = useState<string[]>([])
  const [topic, setTopic] = useState("")
  const [tone, setTone] = useState("")
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [generatedArticles, setGeneratedArticles] = useState<Record<number, boolean>>({})
  const [isGeneratingAll, setIsGeneratingAll] = useState(false)
  const [currentGeneratingIndex, setCurrentGeneratingIndex] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    // Récupérer l'ID de la session actuelle
    const currentSessionId = localStorage.getItem("currentSession")
    
    if (!currentSessionId) {
      router.push("/")
      return
    }
    
    // Récupérer les données de la session
    const sessionData = JSON.parse(localStorage.getItem(`session_${currentSessionId}`) || "{}")
    
    if (!sessionData || !sessionData.titles || !sessionData.topic) {
      router.push("/")
      return
    }
    
    setSessionId(currentSessionId)
    setTitles(sessionData.titles)
    setTopic(sessionData.topic)
    setTone(sessionData.tone)
    
    // Récupérer les articles déjà générés
    if (sessionData.articles) {
      const generatedStatus: Record<number, boolean> = {}
      
      Object.keys(sessionData.articles).forEach(index => {
        generatedStatus[Number(index)] = true
      })
      
      setGeneratedArticles(generatedStatus)
    }
  }, [router])

  const generateArticle = async (index: number) => {
    if (!sessionId) return
    
    setCurrentGeneratingIndex(index)
    setError(null)

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

    try {
      const response = await fetch(`${apiUrl}/api/article`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          titre: titles[index],
          sujet: topic,
        }),
      })

      if (!response.ok) {
        throw new Error(`Erreur: ${response.status}`)
      }

      const data = await response.json()
      
      // Stocker le contenu de l'article
      const articleContent = data.content
      
      // Mettre à jour l'état local
      setGeneratedArticles(prev => ({
        ...prev,
        [index]: true
      }))
      
      // Mettre à jour la session
      const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
      if (!sessionData.articles) {
        sessionData.articles = {}
      }
      
      sessionData.articles[index] = {
        title: titles[index],
        content: articleContent,
        isValidated: false
      }
      
      localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
      
      return true
    } catch (err) {
      setError(`Une erreur s'est produite: ${err instanceof Error ? err.message : String(err)}`)
      return false
    } finally {
      setCurrentGeneratingIndex(null)
    }
  }

  const generateAllArticles = async () => {
    if (!sessionId) return
    
    setIsGeneratingAll(true)
    setError(null)
    setProgress(0)
    
    const totalArticles = titles.length
    let successCount = 0
    
    for (let i = 0; i < totalArticles; i++) {
      // Ignorer les articles déjà générés
      if (generatedArticles[i]) {
        successCount++
        setProgress(Math.round((successCount / totalArticles) * 100))
        continue
      }
      
      const success = await generateArticle(i)
      
      if (success) {
        successCount++
      }
      
      setProgress(Math.round((successCount / totalArticles) * 100))
    }
    
    setIsGeneratingAll(false)
  }

  const viewArticle = (index: number) => {
    router.push(`/articles/${index}`)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container max-w-4xl mx-auto px-4 py-12">
        <Card className="border-none shadow-xl bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm">
          <CardHeader className="p-6 border-b">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Link
                  href="/"
                  className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
                >
                  <ArrowLeft className="h-5 w-5" />
                  <span className="sr-only">Retour aux titres</span>
                </Link>
                <h1 className="text-2xl md:text-3xl font-bold">Mes Articles</h1>
              </div>
              
              {!isGeneratingAll && Object.keys(generatedArticles).length < titles.length && (
                <Button 
                  onClick={generateAllArticles}
                  className="bg-gradient-to-r from-purple-600 to-blue-500 hover:from-purple-700 hover:to-blue-600"
                >
                  Générer tous les articles
                </Button>
              )}
            </div>
          </CardHeader>
          
          <CardContent className="p-6">
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg text-red-600 dark:text-red-400 mb-6">
                {error}
              </div>
            )}
            
            {isGeneratingAll && (
              <div className="mb-6">
                <div className="flex justify-between mb-2">
                  <span>Génération en cours...</span>
                  <span>{progress}%</span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2.5">
                  <div 
                    className="bg-blue-600 h-2.5 rounded-full" 
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
              </div>
            )}
            
            {titles.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-slate-500 dark:text-slate-400">
                  Aucun article n'a été généré. Veuillez retourner à la page d'accueil.
                </p>
                <Button onClick={() => router.push("/")} className="mt-4">
                  Créer un nouvel article
                </Button>
              </div>
            ) : (
              <div className="space-y-6">
                {titles.map((title, index) => (
                  <div
                    key={index}
                    className="p-4 border rounded-lg bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-400">{index + 1}.</span>
                          <h2 className="font-medium">{title}</h2>
                        </div>
                      </div>
                      <div>
                        {generatedArticles[index] ? (
                          <Button
                            onClick={() => viewArticle(index)}
                            variant="outline"
                            className="bg-white dark:bg-slate-800"
                          >
                            Voir l'article
                          </Button>
                        ) : currentGeneratingIndex === index ? (
                          <Button disabled className="bg-slate-300 dark:bg-slate-700">
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Génération...
                          </Button>
                        ) : (
                          <Button
                            onClick={() => generateArticle(index)}
                            className="bg-gradient-to-r from-purple-600 to-blue-500 hover:from-purple-700 hover:to-blue-600"
                          >
                            Générer
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
