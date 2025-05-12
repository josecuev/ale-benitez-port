// src/components/PhotoGallery.tsx
import React, { useState, useEffect } from 'react'
import { motion, LayoutGroup, AnimatePresence } from 'framer-motion'

interface PhotosJSON { photos: string[] }
const PAGE_SIZE = 30

const photoVariants = {
  hidden: { opacity: 0, y: 80 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: 'easeOut' } }
}

export default function PhotoGallery() {
  const [photos, setPhotos] = useState<string[]>([])
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const [expandedSrc, setExpandedSrc] = useState<string | null>(null)

  useEffect(() => {
    fetch('/assets/photos.json')
      .then(r => r.json())
      .then((data: PhotosJSON) => setPhotos(data.photos))
      .catch(console.error)
  }, [])

  const loadMore = () =>
    setVisibleCount(n => Math.min(photos.length, n + PAGE_SIZE))

  return (
    <LayoutGroup>
      <div className="min-h-screen bg-black text-white flex flex-col">
        {/* Barra superior amarilla, más alta y con nombre alineado a la derecha */}
        <header
          className="w-full h-16 bg-[#FFF500] flex items-center px-8"
        >
          {/* Espacio flexible para empujar el texto al final */}
          <div className="flex-grow" />
          <span
            className="font-sans text-2xl text-black uppercase tracking-wide"
            style={{ fontFamily: 'Roboto, sans-serif' }}
          >
            Alejandro Benítez
          </span>
        </header>

        {/* Galería */}
        <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 p-2">
          {photos.slice(0, visibleCount).map(src => (
            <motion.div
              key={src}
              layoutId={src}
              className="relative w-full h-0 pb-[150%] overflow-hidden cursor-pointer"
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
                className="absolute inset-0 w-full h-full object-cover"
                layout
                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
              />
            </motion.div>
          ))}
        </div>

        {/* Botón "Cargar más" */}
        {visibleCount < photos.length && (
          <div className="py-6 flex justify-center">
            <button
              onClick={loadMore}
              style={{ backgroundColor: '#FFF500' }}
              className="px-8 py-3 text-black rounded-full font-sans shadow-md hover:bg-yellow-300 transition"
            >
              Cargar más
            </button>
          </div>
        )}

        {/* Overlay expandido */}
        <AnimatePresence>
          {expandedSrc && (
            <motion.div
              className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setExpandedSrc(null)}
            >
              <motion.img
                src={`/assets/${expandedSrc}`}
                alt=""
                className="max-w-full max-h-full object-contain"
                layoutId={expandedSrc}
                layout
                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </LayoutGroup>
  )
}
