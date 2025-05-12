import { useState, useEffect } from 'react'
import gsap from 'gsap'
import { FiX } from 'react-icons/fi'

const PAGE_SIZE = 30 // Ajusta este valor según tu preferencia

export default function PhotoGallery() {
  const [photos, setPhotos] = useState<string[]>([])
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    // Animación inicial cinemática
    gsap.from('.gallery', { opacity: 0, y: 30, duration: 1, ease: 'power3.out' })

    // Carga del JSON de fotos
    fetch('/assets/photos.json')
      .then((response) => response.json())
      .then((data) => setPhotos(data.photos))
      .catch((error) => console.error('Error cargando photos.json:', error))
  }, [])

  const loadMore = () => {
    setVisibleCount((count) => Math.min(photos.length, count + PAGE_SIZE))
  }

  return (
    <>
      {/* Galería de Miniaturas */}
      <div className="gallery grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 p-4">
        {photos.slice(0, visibleCount).map((path) => (
          <div
            key={path}
            className="relative overflow-hidden rounded-lg cursor-pointer"
            onClick={() => setSelected(path)}
          >
            <img
              src={`/assets/${path}`}
              loading="lazy"
              className="w-full h-auto object-contain transition-transform duration-300 hover:scale-105"
              alt=""
            />
          </div>
        ))}
      </div>

      {/* Botón "Cargar más" */}
      {visibleCount < photos.length && (
        <div className="text-center my-4">
          <button
            onClick={loadMore}
            className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition"
          >
            Cargar más
          </button>
        </div>
      )}

      {/* Overlay de Foto Seleccionada */}
      {selected && (
        <div
          className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50 p-4"
          onClick={() => setSelected(null)}
        >
          <button className="absolute top-6 right-6 text-white text-2xl">
            <FiX />
          </button>
          <img
            src={`/assets/${selected}`}
            loading="lazy"
            className="max-w-full max-h-full object-contain rounded-lg shadow-lg"
            alt="Selected photo"
          />
        </div>
      )}
    </>
  )
}
