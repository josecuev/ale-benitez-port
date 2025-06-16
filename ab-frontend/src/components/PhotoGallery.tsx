// src/components/PhotoGallery.tsx
import React, { useState, useEffect, useCallback } from 'react'
import { motion, LayoutGroup, AnimatePresence } from 'framer-motion'

interface PhotosJSON { photos: string[] }
const PAGE_SIZE = 30

const photoVariants = {
  hidden: { opacity: 0, y: 80 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: 'easeOut' } }
}

const nameVariants = {
  normal: { color: '#000', fontSize: '1.5rem' },
  expanded: { color: '#fff', fontSize: '2rem' },
}

export default function PhotoGallery() {
  const [photos, setPhotos] = useState<string[]>([])
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const [expandedSrc, setExpandedSrc] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    fetch('/assets/photos.json')
      .then(r => r.json())
      .then((data: PhotosJSON) => setPhotos(data.photos))
      .catch(console.error)
  }, [])

  const loadMore = useCallback(() => {
    if (isLoading || visibleCount >= photos.length) return
    setIsLoading(true)
    setTimeout(() => {
      setVisibleCount(n => Math.min(photos.length, n + PAGE_SIZE))
      setIsLoading(false)
    }, 100)
  }, [isLoading, visibleCount, photos.length])

  // Scroll infinito mejorado
  useEffect(() => {
    const handleScroll = () => {
      if (expandedSrc || isLoading || visibleCount >= photos.length) return
      
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop
      const windowHeight = window.innerHeight
      const documentHeight = document.documentElement.scrollHeight
      
      // Cargar más cuando estés a 300px del final
      if (scrollTop + windowHeight >= documentHeight - 300) {
        loadMore()
      }
    }

    const throttledScroll = throttle(handleScroll, 200)
    window.addEventListener('scroll', throttledScroll, { passive: true })
    
    return () => window.removeEventListener('scroll', throttledScroll)
  }, [expandedSrc, isLoading, visibleCount, photos.length, loadMore])

  return (
    <LayoutGroup>
      <div className="min-h-screen bg-black text-white flex flex-col overflow-x-hidden">
        {!expandedSrc && (
          <header className="fixed top-0 z-20 w-full h-16 bg-[#FFF500] flex items-center px-8">
            <div className="flex-grow" />
            <motion.span
              layoutId="profileName"
              variants={nameVariants}
              initial="normal"
              animate="normal"
              className="bebas-neue-regular uppercase tracking-wide select-none"
              style={{ 
                fontFamily: '"Bebas Neue", sans-serif',
                fontWeight: 400,
                fontStyle: 'normal'
              }}
            >
              Alejandro Benítez
            </motion.span>
          </header>
        )}

        {/* Grid principal con scrollbar oculto */}
        <div 
          className="flex-1 p-2 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2"
          style={{
            scrollbarWidth: 'none', // Firefox
            msOverflowStyle: 'none', // IE/Edge
          }}
        >
          <style jsx>{`
            div::-webkit-scrollbar {
              display: none; /* Chrome, Safari, Opera */
            }
          `}</style>
          
          {photos.slice(0, visibleCount).map((src, index) => (
            <motion.div
              key={src}
              layoutId={src}
              className="relative w-full h-0 pb-[150%] overflow-hidden cursor-pointer touch-manipulation"
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.3, margin: "100px" }}
              variants={photoVariants}
              onClick={() => setExpandedSrc(src)}
              whileTap={{ scale: 0.98 }}
            >
              <motion.img
                src={`/assets/${src}`}
                alt={`Foto ${index + 1}`}
                loading="lazy"
                className="absolute inset-0 w-full h-full object-cover select-none"
                layout
                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                draggable={false}
              />
            </motion.div>
          ))}
          
          {/* Indicador de carga */}
          {isLoading && (
            <div className="col-span-full flex justify-center py-8">
              <div className="w-8 h-8 border-2 border-[#FFF500] border-t-transparent rounded-full animate-spin"></div>
            </div>
          )}
        </div>

        {/* Botón manual (backup) */}
        {visibleCount < photos.length && !expandedSrc && !isLoading && (
          <div className="py-6 flex justify-center">
            <button
              onClick={loadMore}
              style={{ backgroundColor: '#FFF500' }}
              className="px-8 py-3 text-black rounded-full shadow-md hover:bg-yellow-300 transition touch-manipulation"
            >
              Cargar más
            </button>
          </div>
        )}

        <AnimatePresence>
          {expandedSrc && (
            <motion.div
              className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4 touch-manipulation"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.img
                src={`/assets/${expandedSrc}`}
                alt="Imagen expandida"
                className="max-w-full max-h-full object-contain select-none"
                layoutId={expandedSrc}
                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                draggable={false}
              />

              <motion.span
                layoutId="profileName"
                variants={nameVariants}
                initial="normal"
                animate="expanded"
                className="absolute bottom-6 right-6 bebas-neue-regular uppercase tracking-wide text-white select-none"
                style={{ 
                  fontFamily: '"Bebas Neue", sans-serif',
                  fontWeight: 400,
                  fontStyle: 'normal'
                }}
              >
                Alejandro Benítez
              </motion.span>

              <motion.div
                className="absolute bottom-2 right-6 text-white bebas-neue-regular text-lg select-none"
                style={{ 
                  fontFamily: '"Bebas Neue", sans-serif',
                  fontWeight: 400,
                  fontStyle: 'normal'
                }}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1, transition: { delay: 0.3 } }}
              >
                +595 986 966 064
              </motion.div>

              <div
                className="absolute inset-0 z-40 cursor-pointer"
                onClick={() => setExpandedSrc(null)}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </LayoutGroup>
  )
}

// Función throttle para optimizar el scroll
function throttle(func: Function, limit: number) {
  let inThrottle: boolean
  return function(this: any, ...args: any[]) {
    if (!inThrottle) {
      func.apply(this, args)
      inThrottle = true
      setTimeout(() => inThrottle = false, limit)
    }
  }
}