"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Loader2 } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select"

export default function HomePage() {
  const router = useRouter()
  const [theme, setTheme] = useState("")
  const [variations, setVariations] = useState("3")
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [colorScheme, setColorScheme] = useState("default")

  const generateWebsiteThemes = async () => {
    if (!theme) return

    setIsGenerating(true)
    setError(null)

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

    try {
      const response = await fetch(`${apiUrl}/api/generate-website-theme`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          theme: theme, 
          variations: parseInt(variations) 
        }),
      })

      if (!response.ok) {
        throw new Error(`Erreur: ${response.status}`)
      }

      const data = await response.json()
      
      // Créer une nouvelle session avec un ID unique
      const sessionId = Date.now().toString()
      
      // Stocker les données pour les autres pages
      const sessionData = {
        id: sessionId,
        theme: theme,
        variations: data.variations,
        createdAt: new Date().toISOString()
      }
      
      // Sauvegarder la session actuelle
      localStorage.setItem("currentSession", sessionId)
      localStorage.setItem(`session_${sessionId}`, JSON.stringify(sessionData))
      
      // Rediriger vers la page des logos
      router.push("/logos")
    } catch (err) {
      setError(`Une erreur s'est produite: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container max-w-4xl mx-auto px-4 py-12">
        <Card className="border-none shadow-xl bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm">
          <CardHeader className="text-center">
            <h1 className="text-3xl font-bold text-purple-600 dark:text-purple-400">
              Générateur de Sites Web avec IA
            </h1>
            <p className="text-slate-600 dark:text-slate-400">
              Créez plusieurs sites web uniques à partir d'un seul thème
            </p>
          </CardHeader>
          
          <CardContent className="p-6 md:p-8">
            <div className="space-y-6">
              <div className="space-y-4">
                <label className="block text-sm font-medium">Thème principal de vos sites web</label>
                <Input
                  value={theme}
                  onChange={(e) => setTheme(e.target.value)}
                  placeholder="Ex: café bio, agence de voyage, cours de yoga..."
                  className="h-12"
                />
              </div>

              <div className="space-y-4">
                <label className="block text-sm font-medium">Nombre de variations</label>
                <Select value={variations} onValueChange={setVariations}>
                  <SelectTrigger className="h-12">
                    <SelectValue placeholder="Choisir un nombre" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1 site</SelectItem>
                    <SelectItem value="2">2 sites</SelectItem>
                    <SelectItem value="3">3 sites</SelectItem>
                    <SelectItem value="4">4 sites</SelectItem>
                    <SelectItem value="5">5 sites</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-4">
                <label className="block text-sm font-medium">Palette de couleurs</label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  <div 
                    className={`border rounded-lg p-3 cursor-pointer transition-all ${
                      colorScheme === "default" ? "ring-2 ring-purple-500" : ""
                    }`}
                    onClick={() => setColorScheme("default")}
                  >
                    <div className="flex items-center gap-2">
                      <div className="flex">
                        <div className="w-6 h-6 bg-gradient-to-r from-blue-500 to-purple-500 rounded-l-sm"></div>
                        <div className="w-6 h-6 bg-gradient-to-r from-purple-500 to-pink-500 rounded-r-sm"></div>
                      </div>
                      <span>Automatique</span>
                    </div>
                  </div>
                  
                  <div 
                    className={`border rounded-lg p-3 cursor-pointer transition-all ${
                      colorScheme === "bleu" ? "ring-2 ring-purple-500" : ""
                    }`}
                    onClick={() => setColorScheme("bleu")}
                  >
                    <div className="flex items-center gap-2">
                      <div className="flex">
                        <div className="w-6 h-6 bg-blue-300 rounded-l-sm"></div>
                        <div className="w-6 h-6 bg-blue-500 rounded-r-sm"></div>
                      </div>
                      <span>Tons bleus</span>
                    </div>
                  </div>
                  
                  <div 
                    className={`border rounded-lg p-3 cursor-pointer transition-all ${
                      colorScheme === "vert" ? "ring-2 ring-purple-500" : ""
                    }`}
                    onClick={() => setColorScheme("vert")}
                  >
                    <div className="flex items-center gap-2">
                      <div className="flex">
                        <div className="w-6 h-6 bg-green-300 rounded-l-sm"></div>
                        <div className="w-6 h-6 bg-green-600 rounded-r-sm"></div>
                      </div>
                      <span>Tons verts</span>
                    </div>
                  </div>
                  
                  <div 
                    className={`border rounded-lg p-3 cursor-pointer transition-all ${
                      colorScheme === "rouge" ? "ring-2 ring-purple-500" : ""
                    }`}
                    onClick={() => setColorScheme("rouge")}
                  >
                    <div className="flex items-center gap-2">
                      <div className="flex">
                        <div className="w-6 h-6 bg-red-300 rounded-l-sm"></div>
                        <div className="w-6 h-6 bg-red-600 rounded-r-sm"></div>
                      </div>
                      <span>Tons rouges</span>
                    </div>
                  </div>
                  
                  <div 
                    className={`border rounded-lg p-3 cursor-pointer transition-all ${
                      colorScheme === "violet" ? "ring-2 ring-purple-500" : ""
                    }`}
                    onClick={() => setColorScheme("violet")}
                  >
                    <div className="flex items-center gap-2">
                      <div className="flex">
                        <div className="w-6 h-6 bg-purple-300 rounded-l-sm"></div>
                        <div className="w-6 h-6 bg-purple-600 rounded-r-sm"></div>
                      </div>
                      <span>Tons violets</span>
                    </div>
                  </div>
                  
                  <div 
                    className={`border rounded-lg p-3 cursor-pointer transition-all ${
                      colorScheme === "neutre" ? "ring-2 ring-purple-500" : ""
                    }`}
                    onClick={() => setColorScheme("neutre")}
                  >
                    <div className="flex items-center gap-2">
                      <div className="flex">
                        <div className="w-6 h-6 bg-gray-300 rounded-l-sm"></div>
                        <div className="w-6 h-6 bg-gray-600 rounded-r-sm"></div>
                      </div>
                      <span>Tons neutres</span>
                    </div>
                  </div>
                </div>
              </div>

              <Button
                onClick={generateWebsiteThemes}
                disabled={isGenerating || !theme}
                className="w-full h-12 text-lg bg-gradient-to-r from-purple-600 to-blue-500 hover:from-purple-700 hover:to-blue-600"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Génération en cours...
                  </>
                ) : (
                  "Générer les thèmes de sites"
                )}
              </Button>

              {error && (
                <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg text-red-600 dark:text-red-400">
                  {error}
                </div>
              )}

              <div className="bg-blue-50 dark:bg-slate-800/50 p-4 rounded-lg space-y-2">
                <h3 className="font-semibold text-blue-700 dark:text-blue-400">
                  Comment ça fonctionne
                </h3>
                <ul className="text-sm text-slate-700 dark:text-slate-300 space-y-1 list-disc pl-5">
                  <li>Entrez un thème général pour vos sites web</li>
                  <li>Choisissez le nombre de variations à générer</li>
                  <li>L'IA créera différentes approches du même thème</li>
                  <li>Vous pourrez ensuite personnaliser les logos</li>
                  <li>Enfin, générez le contenu complet pour chaque site</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
