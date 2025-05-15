import { useToast as useToastOriginal } from "@/components/ui/toast"

// Re-export le hook useToast
export const useToast = useToastOriginal

// Exporter également le composant toast pour une utilisation plus simple
export const toast = {
  error: (message: string) => useToastOriginal().toast({ 
    title: "Erreur", 
    // Remplacer description par children ou une autre propriété valide
    children: message,
    variant: "destructive" 
  }),
  success: (message: string) => useToastOriginal().toast({ 
    title: "Succès", 
    children: message 
  }),
  info: (message: string) => useToastOriginal().toast({ 
    children: message 
  })
} 