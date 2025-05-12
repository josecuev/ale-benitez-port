// src/components/PhotoGallery.tsx
import React, { useState, useEffect } from 'react'
import { motion, LayoutGroup, AnimatePresence } from 'framer-motion'

interface PhotosJSON {
  photos: string[]
}

const PAGE_SIZE = 30

// Animación para entrada de cada foto
const photoVariants = {
  hidden: { opacity: 0, y: 80 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: 'easeOut' } }
}

export default function PhotoGallery() {
  const [photos, setPhotos] = useState<string[]>([])
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const [expandedSrc, setExpandedSrc] = useState<string | null>(null)

  // Carga fotos desde public/assets/photos.json
  useEffect(() => {
    fetch('/assets/photos.json')
      .then(r => r.json())
      .then((data: PhotosJSON) => setPhotos(data.photos))
      .catch(console.error)
  }, [])

  const loadMore = () =>
    setVisibleCount(count => Math.min(photos.length, count + PAGE_SIZE))

  return (
    <LayoutGroup>
      <div className="min-h-screen bg-gray-900 text-white">
        <h1 className="text-center text-4xl font-bold py-8">Mi Portafolio</h1>

        {/* Galería */}
        <div className="max-w-5xl mx-auto grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6 p-4">
          {photos.slice(0, visibleCount).map((src) => (
            <motion.div
              key={src}
              layoutId={src}                      // mismo ID para morphing
              className="rounded-lg overflow-hidden cursor-pointer"
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.4 }}
              variants={photoVariants}
              onClick={() => setExpandedSrc(src)}
            >
              <motion.img
                src={`/assets/${src}`}
                alt=""
                loading="lazy"
                className="w-full h-auto object-contain"
                layout                                // activa layout animation
                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
              />
            </motion.div>
          ))}
        </div>

        {/* Cargar más */}
        {visibleCount < photos.length && (
          <div className="text-center mt-12 mb-8">
            <button
              onClick={loadMore}
              className="px-6 py-3 bg-indigo-600 rounded-full hover:bg-indigo-500 transition"
            >
              Cargar más
            </button>
          </div>
        )}

        {/* Overlay expandido */}
        <AnimatePresence>
          {expandedSrc && (
            <motion.div
              className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setExpandedSrc(null)}
            >
              <motion.img
                src={`/assets/${expandedSrc}`}
                alt=""
                className="object-contain"
                layoutId={expandedSrc}             // coincide con la miniatura
                layout                              // morphing
                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                style={{ maxWidth: '90vw', maxHeight: '90vh' }}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </LayoutGroup>
  )
}
