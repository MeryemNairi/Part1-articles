"use client"

import React, { useState, useEffect, useRef } from "react"
import Link from "next/link"
import { useRouter, useParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardContent, CardFooter } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { ArrowLeft, Check, ImageIcon, RefreshCw, X, Loader2, Download, Share, Wand2, Globe, Upload } from "lucide-react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import ReactMarkdown from 'react-markdown'
import { jsPDF } from "jspdf"

export default function ArticleDetailPage() {
  const router = useRouter()
  const params = useParams()
  const id = params?.id as string
  
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [title, setTitle] = useState("")
  const [content, setContent] = useState("")
  const [topic, setTopic] = useState("")
  const [tone, setTone] = useState("")
  const [additionalContext, setAdditionalContext] = useState("")
  const [avoidContext, setAvoidContext] = useState("")
  const [isEditing, setIsEditing] = useState(false)
  const [editedContent, setEditedContent] = useState("")
  const [isValidated, setIsValidated] = useState(false)
  const [image, setImage] = useState<string | null>(null)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [isGeneratingImage, setIsGeneratingImage] = useState(false)
  const [imagePrompt, setImagePrompt] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState("content")
  const [currentLanguage, setCurrentLanguage] = useState("fr")
  const [isTranslating, setIsTranslating] = useState(false)
  const [sources, setSources] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [articleImage, setArticleImage] = useState<string | null>(null)
  
  const articleContentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!id) return
    
    console.log(`Page article chargée avec ID: ${id}`)
    
    // Récupérer l'ID de la session actuelle
    const currentSessionId = localStorage.getItem("currentSession")
    
    if (!currentSessionId) {
      console.log("Pas de session trouvée, redirection vers la page d'accueil")
      router.push("/")
      return
    }
    
    // Récupérer les données de la session
    const sessionData = JSON.parse(localStorage.getItem(`session_${currentSessionId}`) || "{}")
    
    if (!sessionData) {
      console.log("Pas de données de session trouvées, redirection vers la page d'accueil")
      router.push("/")
      return
    }
    
    // Vérifier si des articles existent
    if (!sessionData.articles) {
      console.log("Pas d'articles trouvés, redirection vers la page de contenu")
      router.push("/content")
      return
    }
    
    const articleIndex = Number(id)
    
    if (!sessionData.articles[articleIndex]) {
      console.log(`Article avec l'index ${articleIndex} non trouvé, redirection vers la page d'articles`)
      router.push("/articles")
      return
    }
    
    setSessionId(currentSessionId)
    setTitle(sessionData.articles[articleIndex].title || "")
    setContent(sessionData.articles[articleIndex].content || "")
    setEditedContent(sessionData.articles[articleIndex].content || "")
    setIsValidated(sessionData.articles[articleIndex].isValidated || false)
    
    // Récupérer l'image de l'article si elle existe
    if (sessionData.articles[articleIndex].image) {
      setArticleImage(sessionData.articles[articleIndex].image)
      console.log("Image d'article chargée:", sessionData.articles[articleIndex].image)
    }
    
    // Récupérer les sources si elles existent
    if (sessionData.articles[articleIndex].sources) {
      setSources(sessionData.articles[articleIndex].sources)
    }
    
    // Récupérer les informations de la session
    if (sessionData.topic) {
      setTopic(sessionData.topic)
    }
    
    if (sessionData.tone) {
      setTone(sessionData.tone)
    }
    
    if (sessionData.additionalContext) {
      setAdditionalContext(sessionData.additionalContext)
    }
    
    if (sessionData.avoidContext) {
      setAvoidContext(sessionData.avoidContext)
    }
    
    setIsLoading(false)
  }, [id, router])

  const generateArticleImage = async () => {
    if (!sessionId || !title) return
    setIsGeneratingImage(true)
    setError(null)
    
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    
    try {
      // Générer un prompt pour l'image basé sur le titre de l'article
      const defaultPrompt = `Illustration pour un article intitulé "${title}"`
      const prompt = imagePrompt || defaultPrompt
      
      console.log("Envoi de la requête pour générer une image avec le prompt:", prompt)
      
      // Envoyer aussi sessionId et articleIndex pour la persistance côté backend
      const response = await fetch(`${apiUrl}/api/generate-article-image`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: prompt,
          title: title,
          session_id: sessionId,
          article_index: id
        }),
      })
      
      console.log("Statut de la réponse:", response.status)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error("Erreur de l'API:", errorText)
        throw new Error(`Erreur: ${response.status}`)
      }
      
      // Convertir la réponse en texte d'abord pour le débogage
      const responseText = await response.text()
      console.log("Réponse brute:", responseText.substring(0, 100) + "...")
      
      // Puis parser en JSON
      const data = JSON.parse(responseText)
      
      // Vérifier si l'image a été générée avec succès
      if (data.image_url) {
        console.log("Image URL reçue, longueur:", data.image_url.length)
        setArticleImage(data.image_url)
        
        // Mettre à jour la session
        if (sessionId) {
          const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
          
          if (!sessionData.articles) {
            sessionData.articles = []
          }
          
          const articleIndex = Number(id)
          
          if (!sessionData.articles[articleIndex]) {
            sessionData.articles[articleIndex] = {
              title: title,
              content: content,
              isValidated: isValidated
            }
          }
          
          sessionData.articles[articleIndex].image = data.image_url
          localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
          console.log("Image sauvegardée dans la session")
        }
      } else if (data.error) {
        console.error("Erreur retournée par l'API:", data.error)
        setError(data.error)
      } else {
        console.error("Pas d'URL d'image dans la réponse")
        setError("Pas d'URL d'image dans la réponse")
      }
    } catch (err) {
      console.error("Erreur lors de la génération de l'image:", err)
      setError(`Erreur lors de la génération de l'image: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsGeneratingImage(false)
    }
  }

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return
    
    const file = e.target.files[0]
    const reader = new FileReader()
    
    reader.onloadend = () => {
      const base64String = reader.result as string
      setArticleImage(base64String)
      
      // Mettre à jour la session
      if (sessionId) {
        const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
        
        if (!sessionData.articles) {
          sessionData.articles = []
        }
        
        const articleIndex = Number(id)
        
        if (sessionData.articles[articleIndex]) {
          sessionData.articles[articleIndex].image = base64String
          localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
        }
      }
    }
    
    reader.readAsDataURL(file)
  }

  const handleEdit = () => {
    setIsEditing(true)
    setIsValidated(false)
  }

  const handleSave = () => {
    if (!sessionId) return
    
    setContent(editedContent)
    setIsEditing(false)
    
    // Mettre à jour dans la session
    const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
    if (sessionData.articles && sessionData.articles[id]) {
      sessionData.articles[id].content = editedContent
      localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
    }
  }

  const handleCancel = () => {
    setEditedContent(content)
    setIsEditing(false)
  }

  const handleRegenerate = async () => {
    if (!sessionId) return
    
    setIsRegenerating(true)
    setError(null)
    
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    
    try {
      const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
      
      const response = await fetch(`${apiUrl}/api/article`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          titre: title,
          sujet: topic,
          additional_context: additionalContext,
          avoid_context: avoidContext,
          article_length: sessionData.articleLength || 1500,
          detail_level: sessionData.detailLevel || 3
        }),
      })

      if (!response.ok) {
        throw new Error(`Erreur: ${response.status}`)
      }

      const data = await response.json()
      
      // Mettre à jour le contenu
      setContent(data.content)
      setEditedContent(data.content)
      
      // Mettre à jour les sources si elles existent
      if (data.sources && Array.isArray(data.sources)) {
        setSources(data.sources)
      }
      
      // Mettre à jour dans la session
      if (sessionData.articles && sessionData.articles[id]) {
        sessionData.articles[id].content = data.content
        // Sauvegarder également les sources
        if (data.sources) {
          sessionData.articles[id].sources = data.sources
        }
        localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
      }
    } catch (err) {
      setError(`Une erreur s'est produite: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsRegenerating(false)
    }
  }

  const handleValidate = () => {
    if (!sessionId) return
    
    setIsValidated(true)
    setIsEditing(false)
    
    // Mettre à jour dans la session
    const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
    if (sessionData.articles && sessionData.articles[id]) {
      sessionData.articles[id].isValidated = true
      localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
    }
  }

  const handleExportPDF = () => {
    const doc = new jsPDF();
    
    // Ajouter le titre
    doc.setFontSize(20);
    doc.text(title, 20, 20);
    
    // Ajouter l'image si elle existe
    if (image) {
      doc.addImage(image, 'JPEG', 20, 30, 170, 100);
      
      // Ajouter le contenu après l'image
      doc.setFontSize(12);
      const contentLines = doc.splitTextToSize(content.replace(/\n/g, ' '), 170);
      doc.text(contentLines, 20, 140);
    } else {
      // Ajouter le contenu sans image
      doc.setFontSize(12);
      const contentLines = doc.splitTextToSize(content.replace(/\n/g, ' '), 170);
      doc.text(contentLines, 20, 30);
    }
    
    // Télécharger le PDF
    doc.save(`${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.pdf`);
  }

  const handleExportJSON = () => {
    if (!sessionId) return
    
    const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
    const articleData = {
      title: title,
      content: content,
      topic: topic,
      tone: tone,
      image: image,
      additionalContext: additionalContext,
      avoidContext: avoidContext,
      createdAt: new Date().toISOString()
    }
    
    // Créer un objet Blob avec les données JSON
    const blob = new Blob([JSON.stringify(articleData, null, 2)], { type: 'application/json' });
    
    // Créer une URL pour le Blob
    const url = URL.createObjectURL(blob);
    
    // Créer un lien de téléchargement
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.json`;
    
    // Ajouter le lien au document, cliquer dessus, puis le supprimer
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    // Libérer l'URL
    URL.revokeObjectURL(url);
  }

  const handleTranslate = async (targetLanguage: string) => {
    if (!sessionId || isTranslating) return
    
    setIsTranslating(true)
    setError(null)
    
    try {
      console.log(`Traduction du contenu en ${targetLanguage}`)
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      
      const response = await fetch(`${apiUrl}/api/translate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: content,
          target_language: targetLanguage
        }),
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error("Erreur de l'API de traduction:", errorText)
        throw new Error(`Erreur ${response.status}: ${errorText}`)
      }
      
      const data = await response.json()
      
      if (data.translated_content) {
        setContent(data.translated_content)
        setEditedContent(data.translated_content)
        setCurrentLanguage(targetLanguage)
        
        // Sauvegarder la traduction dans la session
        const sessionData = JSON.parse(localStorage.getItem(`session_${sessionId}`) || "{}")
        if (sessionData.articles && sessionData.articles[id]) {
          if (!sessionData.articles[id].translations) {
            sessionData.articles[id].translations = {}
          }
          sessionData.articles[id].translations[targetLanguage] = data.translated_content
          sessionData.articles[id].currentLanguage = targetLanguage
          localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
        }
      } else {
        throw new Error("Aucun contenu traduit reçu")
      }
    } catch (err) {
      console.error("Erreur complète:", err)
      setError(`Erreur lors de la traduction: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsTranslating(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg text-red-600 dark:text-red-400">
          {error}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container max-w-4xl mx-auto px-4 py-12">
        <Card className="border-none shadow-xl bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm">
          <CardHeader className="p-6 border-b">
            <div className="flex items-center gap-4">
              <Link
                href="/articles"
                className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
              >
                <ArrowLeft className="h-5 w-5" />
                <span className="sr-only">Retour aux articles</span>
              </Link>
              <h1 className="text-2xl md:text-3xl font-bold">{title}</h1>
            </div>
            <div className="flex items-center gap-2 mb-4">
              <Globe className="h-4 w-4 text-muted-foreground" />
              <div className="flex items-center gap-1">
                <Button
                  variant={currentLanguage === "fr" ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleTranslate("fr")}
                  disabled={isTranslating || currentLanguage === "fr"}
                  className="px-3"
                >
                  FR
                </Button>
                <Button
                  variant={currentLanguage === "en" ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleTranslate("en")}
                  disabled={isTranslating || currentLanguage === "en"}
                  className="px-3"
                >
                  EN
                </Button>
                <Button
                  variant={currentLanguage === "ar" ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleTranslate("ar")}
                  disabled={isTranslating || currentLanguage === "ar"}
                  className="px-3"
                >
                  AR
                </Button>
              </div>
            </div>
          </CardHeader>

          {isTranslating && (
            <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg text-blue-600 dark:text-blue-400 flex items-center mb-4">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Traduction en cours...
            </div>
          )}

          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 p-4 m-6 rounded-lg text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <div className="px-6 pt-6">
              <TabsList className="grid grid-cols-3 mb-6">
                <TabsTrigger value="content">Contenu</TabsTrigger>
                <TabsTrigger value="preview">Aperçu</TabsTrigger>
                <TabsTrigger value="resources">Ressources</TabsTrigger>
              </TabsList>
            </div>

            <CardContent className="p-6">
              <TabsContent value="content" className="mt-0">
                {isEditing ? (
                  <div className="space-y-4">
                    <Textarea
                      value={editedContent}
                      onChange={(e) => setEditedContent(e.target.value)}
                      className="min-h-[500px] font-mono text-sm"
                    />
                    <div className="flex justify-end gap-2">
                      <Button variant="outline" onClick={handleCancel}>
                        Annuler
                      </Button>
                      <Button onClick={handleSave}>
                        Enregistrer
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-6">
                    <div className="flex justify-end">
                      <Button variant="outline" onClick={handleEdit}>
                        Modifier
                      </Button>
                    </div>
                    <div className="prose dark:prose-invert max-w-none">
                      <ReactMarkdown>{content}</ReactMarkdown>
                    </div>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="preview" className="mt-0">
                <div className="space-y-6">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h2 className="text-lg font-medium">Image de l'article</h2>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={generateArticleImage}
                          disabled={isGeneratingImage}
                        >
                          {isGeneratingImage ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Génération...
                            </>
                          ) : (
                            <>
                              <RefreshCw className="mr-2 h-4 w-4" />
                              Régénérer
                            </>
                          )}
                        </Button>
                        <label htmlFor="image-upload" className="cursor-pointer">
                          <div className="flex items-center gap-1 text-sm px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
                            <Upload className="h-4 w-4" />
                            Importer
                          </div>
                          <input
                            id="image-upload"
                            type="file"
                            accept="image/*"
                            className="hidden"
                            onChange={handleImageUpload}
                          />
                        </label>
                      </div>
                    </div>
                    
                    <div className="aspect-video rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-800">
                      {articleImage ? (
                        <img 
                          src={articleImage} 
                          alt={title} 
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            console.error("Erreur de chargement de l'image:", e)
                            e.currentTarget.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='3' width='18' height='18' rx='2' ry='2'/%3E%3Ccircle cx='8.5' cy='8.5' r='1.5'/%3E%3Cpolyline points='21 15 16 10 5 21'/%3E%3C/svg%3E"
                            e.currentTarget.className = "w-full h-full object-contain p-8 opacity-30"
                          }}
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <ImageIcon className="h-12 w-12 text-slate-400" />
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="prose dark:prose-invert max-w-none">
                    <ReactMarkdown>{content}</ReactMarkdown>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="resources" className="mt-0">
                <div className="space-y-6">
                  <h3 className="text-xl font-semibold mb-4">Sources et Ressources</h3>
                  
                  {sources && sources.length > 0 ? (
                    <div className="grid gap-4">
                      {sources.map((source, index) => (
                        <Card key={index} className="overflow-hidden">
                          <CardHeader className="p-4 bg-slate-50 dark:bg-slate-800">
                            <h4 className="font-medium">Source {index + 1}</h4>
                          </CardHeader>
                          <CardContent className="p-4">
                            <p className="text-sm break-words">{source}</p>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <div className="bg-slate-100 dark:bg-slate-800 rounded-lg p-6 text-center">
                      <p className="text-slate-500 dark:text-slate-400">
                        Aucune source n'est disponible pour cet article.
                      </p>
                    </div>
                  )}
                  
                  <div className="mt-4">
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      Les sources sont automatiquement collectées lors de la génération de l'article.
                      Si aucune source n'est affichée, c'est que l'article a été généré sans références spécifiques.
                    </p>
                  </div>
                </div>
              </TabsContent>
            </CardContent>
          </Tabs>

          <CardFooter className="p-6 border-t flex justify-between">
            <Button variant="outline" onClick={() => router.push("/articles")}>
              Retour à mes articles
            </Button>
            <div className="flex gap-2">
              {!isValidated ? (
                <>
                  <Button
                    variant="outline"
                    onClick={handleRegenerate}
                    disabled={isRegenerating}
                    className="flex items-center gap-2"
                  >
                    {isRegenerating ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Amélioration...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="h-4 w-4" />
                        Améliorer l'article
                      </>
                    )}
                  </Button>
                  <Button
                    onClick={handleValidate}
                    className="bg-gradient-to-r from-green-600 to-emerald-500 hover:from-green-700 hover:to-emerald-600"
                  >
                    <Check className="h-4 w-4 mr-2" />
                    Finaliser l'article
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    variant="outline"
                    onClick={() => setIsValidated(false)}
                    className="flex items-center gap-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    <X className="h-4 w-4" />
                    Reprendre l'édition
                  </Button>
                </>
              )}
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
