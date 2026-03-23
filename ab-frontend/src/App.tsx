import { useEffect } from 'react'
import PhotoGallery from '@/components/PhotoGallery'

const API_BASE = import.meta.env.VITE_API_URL ?? 'https://links.alejandrobenitez.com'

function usePageTracking(page: string) {
  useEffect(() => {
    fetch(`${API_BASE}/api/analytics/track/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ page, referrer: document.referrer }),
    }).catch(() => {
      // silencioso — analytics nunca rompe la UI
    })
  }, [page])
}

export default function App() {
  usePageTracking('portfolio')

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <PhotoGallery />
    </div>
  )
}
