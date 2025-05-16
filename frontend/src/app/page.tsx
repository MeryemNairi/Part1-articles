"use client"

import { useState, useEffect } from "react"
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
import { HexColorPicker } from "react-colorful"
import { ArrowRight } from "lucide-react"

export default function HomePage() {
  const router = useRouter()
  const [theme, setTheme] = useState("")
  const [variations, setVariations] = useState("3")
  const [customPrompt, setCustomPrompt] = useState("")
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [colorScheme, setColorScheme] = useState<string>("default")
  const [customColor, setCustomColor] = useState<string>("#6366f1")
  const [isAnalyzingTheme, setIsAnalyzingTheme] = useState(false)
  const [showColorPicker, setShowColorPicker] = useState(false)
  const [hasExistingSession, setHasExistingSession] = useState(false)

  // Analyser le thème avec LLM pour déterminer la palette de couleurs
  const analyzeThemeWithLLM = async (themeText: string) => {
    if (!themeText || themeText.length < 3) return "default";
    
    setIsAnalyzingTheme(true);
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      const response = await fetch(`${apiUrl}/api/analyze-theme-color`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ theme: themeText }),
      });
      
      if (!response.ok) {
        throw new Error(`Erreur: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Si une couleur hexadécimale est retournée, l'utiliser
      if (data.hexColor) {
        setCustomColor(data.hexColor);
        return "custom";
      }
      
      return data.colorScheme || "default";
    } catch (err) {
      console.error("Erreur lors de l'analyse du thème:", err);
      return "default";
    } finally {
      setIsAnalyzingTheme(false);
    }
  };

  // Utiliser un effet pour analyser le thème lorsqu'il change
  useEffect(() => {
    const debounceTimer = setTimeout(async () => {
      if (theme && theme.length >= 3) {
        const newColorScheme = await analyzeThemeWithLLM(theme);
        setColorScheme(newColorScheme);
      }
    }, 500); // Attendre 500ms après la dernière frappe
    
    return () => clearTimeout(debounceTimer);
  }, [theme]);

  // Fonction de secours si l'API n'est pas disponible
  const getAutomaticColorScheme = (theme: string) => {
    const themeLower = theme.toLowerCase();
    
    if (themeLower.includes("nourriture") || themeLower.includes("food") || themeLower.includes("restaurant")) {
      return "vert";
    } else if (themeLower.includes("voyage") || themeLower.includes("travel") || themeLower.includes("tourisme")) {
      return "bleu";
    } else if (themeLower.includes("tech") || themeLower.includes("digital")) {
      return "violet";
    } else if (themeLower.includes("santé") || themeLower.includes("health") || themeLower.includes("médical")) {
      return "bleu";
    } else if (themeLower.includes("mode") || themeLower.includes("fashion") || themeLower.includes("beauté")) {
      return "rouge";
    } else {
      return "default";
    }
  };

  // Dans le useEffect initial, ajoutez ce code pour charger les données sauvegardées
  useEffect(() => {
    // Récupérer l'ID de la session actuelle
    const currentSessionId = localStorage.getItem("currentSession");
    
    if (currentSessionId) {
      // Récupérer les données de la session
      const sessionData = JSON.parse(localStorage.getItem(`session_${currentSessionId}`) || "{}");
      
      if (sessionData) {
        // Restaurer les valeurs des champs
        if (sessionData.theme) setTheme(sessionData.theme);
        if (sessionData.variations) setVariations(sessionData.variations.toString());
        if (sessionData.customPrompt) setCustomPrompt(sessionData.customPrompt);
        if (sessionData.colorData) {
          if (sessionData.colorData.type === "preset") {
            setColorScheme(sessionData.colorData.value);
          } else if (sessionData.colorData.type === "hex") {
            setColorScheme("custom");
            setCustomColor(sessionData.colorData.value);
          }
        }
        
        // Vérifier si des logos ont été générés
        if (sessionData.variations && Array.isArray(sessionData.variations) && sessionData.variations.length > 0) {
          setHasExistingSession(true);
        }
      }
    }
  }, []);

  function cleanSessionDataForStorage(sessionData: any) {
    // Clean logos
    if (sessionData.logos) {
      Object.keys(sessionData.logos).forEach(key => {
        if (typeof sessionData.logos[key] === 'string' && sessionData.logos[key].startsWith('data:image/')) {
          delete sessionData.logos[key];
        }
      });
    }
    // Clean articles images if present
    if (sessionData.articles && Array.isArray(sessionData.articles)) {
      sessionData.articles.forEach((article: any) => {
        if (article.image && typeof article.image === 'string' && article.image.startsWith('data:image/')) {
          delete article.image;
        }
      });
    }
    return sessionData;
  }

  const generateWebsiteThemes = async () => {
    if (!theme) return

    setIsGenerating(true)
    setError(null)

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    
    // Utiliser la couleur personnalisée si disponible
    const colorData = colorScheme === "custom" 
      ? { type: "hex", value: customColor } 
      : { type: "preset", value: colorScheme === "default" ? getAutomaticColorScheme(theme) : colorScheme };

    try {
      const response = await fetch(`${apiUrl}/api/generate-website-theme`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          theme: theme, 
          variations: parseInt(variations),
          customPrompt: customPrompt,
          colorData: colorData
        }),
      })

      if (!response.ok) {
        throw new Error(`Erreur: ${response.status}`)
      }

      const data = await response.json()
      
      const sessionId = Date.now().toString()
      
      const sessionData = {
        id: sessionId,
        theme: theme,
        customPrompt: customPrompt,
        variations: data.variations,
        colorData: colorData,
        createdAt: new Date().toISOString()
      }
      
      // Créer la session côté backend
      try {
        await fetch(`${apiUrl}/api/create-session`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessionId,
            variations: data.variations
          })
        });
      } catch (e) {
        // Optionally handle backend session creation error
      }
      localStorage.setItem("currentSession", sessionId)
      localStorage.setItem(`session_${sessionId}`, JSON.stringify(cleanSessionDataForStorage(sessionData)))
      router.push("/logos")
    } catch (err) {
      setError(`Une erreur s'est produite: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsGenerating(false)
    }
  }

  // Fonction pour obtenir la couleur d'affichage
  const getColorDisplay = () => {
    if (colorScheme === "custom") {
      return customColor;
    }
    
    switch(colorScheme) {
      case "vert": return "#22c55e"; // green-500
      case "bleu": return "#3b82f6"; // blue-500
      case "violet": return "#8b5cf6"; // purple-500
      case "rouge": return "#ef4444"; // red-500
      case "orange": return "#f97316"; // orange-500
      case "jaune": return "#eab308"; // yellow-500
      default: return "#9ca3af"; // gray-400
    }
  };

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
                <div className="flex items-center justify-between">
                  <label className="block text-sm font-medium">Thème principal de vos sites web</label>
                  {theme && theme.length >= 3 && (
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-slate-500">Couleur:</span>
                      {isAnalyzingTheme ? (
                        <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
                      ) : (
                        <div className="relative">
                          <button
                            type="button"
                            className="h-6 w-6 rounded-full border border-slate-300 cursor-pointer hover:ring-2 hover:ring-offset-1 hover:ring-slate-300"
                            style={{ backgroundColor: getColorDisplay() }}
                            onClick={() => {
                              console.log("Ouverture du sélecteur de couleur");
                              setShowColorPicker(true);
                            }}
                            aria-label="Choisir une couleur"
                          />
                          
                          {showColorPicker && (
                            <div 
                              className="absolute right-0 mt-2 p-4 bg-white dark:bg-slate-800 rounded-lg shadow-xl z-50 border border-slate-200 dark:border-slate-700" 
                              style={{ width: "250px" }}
                            >
                              <div className="text-sm font-medium mb-3">Choisir une couleur</div>
                              
                              <div className="mb-4">
                                <HexColorPicker 
                                  color={customColor} 
                                  onChange={(color) => {
                                    console.log("Couleur changée:", color);
                                    setCustomColor(color);
                                    setColorScheme("custom");
                                  }} 
                                />
                              </div>
                              
                              <div className="mb-4">
                                <label className="block text-xs text-slate-500 mb-1">
                                  Luminosité:
                                </label>
                                <input
                                  type="range"
                                  min="0"
                                  max="100"
                                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                                  onChange={(e) => {
                                    // Ajuster la luminosité de la couleur actuelle
                                    console.log("Luminosité changée:", e.target.value);
                                    // Cette fonction est simplifiée - dans une implémentation réelle,
                                    // vous devriez convertir la couleur en HSL, ajuster la luminosité, puis reconvertir en HEX
                                  }}
                                />
                              </div>
                              
                              <div className="mb-4">
                                <label className="block text-xs text-slate-500 mb-1">
                                  Code hexadécimal:
                                </label>
                                <div className="flex gap-2">
                                  <Input
                                    type="text"
                                    value={customColor}
                                    onChange={(e) => {
                                      console.log("Input changé:", e.target.value);
                                      setCustomColor(e.target.value);
                                      setColorScheme("custom");
                                    }}
                                    className="h-8 text-sm"
                                  />
                                  <button
                                    type="button"
                                    className="h-8 w-8 rounded border border-slate-300"
                                    style={{ backgroundColor: customColor }}
                                    onClick={() => {
                                      console.log("Couleur personnalisée appliquée");
                                      setColorScheme("custom");
                                    }}
                                  />
                                </div>
                              </div>
                              
                              <div className="mb-4">
                                <div className="text-xs text-slate-500 mb-1">
                                  Aperçu de la couleur:
                                </div>
                                <div className="flex gap-2">
                                  <div className="h-10 w-full rounded bg-white border border-slate-300 flex items-center justify-center">
                                    <div 
                                      className="h-8 w-8 rounded"
                                      style={{ backgroundColor: customColor }}
                                    />
                                  </div>
                                </div>
                              </div>
                              
                              <div className="flex justify-between">
                                <Button 
                                  variant="outline" 
                                  size="sm"
                                  onClick={() => {
                                    console.log("Annulation");
                                    setShowColorPicker(false);
                                  }}
                                >
                                  Annuler
                                </Button>
                                
                                <Button 
                                  variant="default" 
                                  size="sm"
                                  onClick={() => {
                                    console.log("Confirmation de la couleur:", customColor);
                                    setColorScheme("custom");
                                    setShowColorPicker(false);
                                  }}
                                >
                                  OK
                                </Button>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
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
                <label className="block text-sm font-medium">Prompt personnalisé (optionnel)</label>
                <Textarea
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="Ajoutez des détails supplémentaires, inspirations ou spécificités..."
                  className="min-h-[100px]"
                />
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

              {hasExistingSession && (
                <Button
                  onClick={() => router.push('/logos')}
                  className="w-full h-12 text-lg bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600"
                >
                  Continuer avec les logos existants
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              )}

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
                  <li>Ajoutez un prompt personnalisé si vous le souhaitez</li>
                  <li>L'IA créera différentes approches du même thème</li>
                  <li>Les logos et le contenu seront générés automatiquement</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
