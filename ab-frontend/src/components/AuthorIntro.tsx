// src/components/AuthorIntro.tsx
import React from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'
import { useRef } from 'react'

export default function AuthorIntro() {
  const containerRef = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end start"]
  })
  
  // La imagen siempre mantiene opacidad 1, solo cambia la escala
  const imageScale = useTransform(scrollYProgress, [0, 0.7], [1, 1.1])
  
  // Overlay negro que se va intensificando para oscurecer la imagen
  const blackOverlayOpacity = useTransform(scrollYProgress, 
    [0, 0.15, 0.6], 
    [0, 0.3, 0.7]
  )
  
  // Nombre aparece primero
  const nameOpacity = useTransform(scrollYProgress, [0.12, 0.22], [0, 1])
  const nameY = useTransform(scrollYProgress, [0.12, 0.22], [30, 0])

  const bioText = `Bienvenido a mi galería.
Soy Alejandro Benítez. Fotógrafo con más de 12 años de experiencia, master en fotografía de moda (Buenos Aires). Con Licenciatura en Diseño Gráfico, carrera que complementa mi forma de pensar y construir imágenes. Me formé como fotógrafo retratista, y culminé mi carrera de grado con una tesis enfocada en esquemas de luz natural, explorando la riqueza y diversidad que ofrece este recurso en distintos contextos. Me interesa trabajar con personas reales, capturando expresiones genuinas y cuidando cada detalle estético. También fundé Fractalia, un espacio creativo donde desarrollo producciones visuales y colaboraciones con otros artistas, creando industria en el arte. Siempre estoy abierto a nuevas propuestas y proyectos con identidad.`

  // Dividir el texto en líneas para animación progresiva
  const lines = bioText.split('. ').map(line => line + (line.endsWith('.') ? '' : '.'))

  return (
    <>
      {/* Agregar estilos para Century Gothic */}
      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=Century+Gothic&display=swap');
        
        .century-gothic {
          font-family: 'Century Gothic', CenturyGothic, 'Segoe UI', sans-serif;
        }
        
        /* Ajustes responsivos para la imagen */
        .author-image {
          object-fit: cover;
          object-position: center center;
        }
        
        /* En pantallas móviles - mostrar más la cara */
        @media (max-width: 768px) {
          .author-image {
            object-position: center 20%;
          }
        }
        
        /* En pantallas medianas */
        @media (min-width: 769px) and (max-width: 1024px) {
          .author-image {
            object-position: center 30%;
          }
        }
        
        /* En pantallas anchas - ajustar para no cortar la frente */
        @media (min-width: 1025px) {
          .author-image {
            object-position: center 35%;
          }
        }
        
        /* En pantallas muy anchas - posiblemente usar contain */
        @media (min-width: 1920px) {
          .author-image {
            object-fit: contain;
            background-color: #000;
          }
        }
      `}</style>

      {/* Contenedor con más altura para espacio extra después del texto */}
      <div ref={containerRef} className="relative w-full h-[300vh]">
        {/* Contenido sticky */}
        <div className="sticky top-0 w-full h-screen overflow-hidden bg-black">
          
          {/* Contenedor de imagen con aspect ratio controlado */}
          <motion.div 
            className="absolute inset-0 w-full h-full flex items-center justify-center"
            style={{
              scale: imageScale,
            }}
          >
            {/* Opción 1: Imagen adaptativa con object-position */}
            <img
              src="/assets/photos/0-ale/ale.jpeg"
              alt="Alejandro Benítez"
              className="w-full h-full author-image"
            />
            
            {/* Opción 2 (alternativa): Contenedor con max-width para pantallas muy anchas */}
            {/* <div className="w-full h-full max-w-[1600px] mx-auto">
              <img
                src="/assets/photos/0-ale/ale.jpeg"
                alt="Alejandro Benítez"
                className="w-full h-full object-cover object-[center_30%]"
              />
            </div> */}
          </motion.div>

          {/* Overlay negro que oscurece gradualmente la imagen */}
          <motion.div 
            className="absolute inset-0 bg-black"
            style={{
              opacity: blackOverlayOpacity
            }}
          />
          
          {/* Gradiente adicional desde abajo para mejorar legibilidad */}
          <motion.div 
            className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent"
            style={{
              opacity: useTransform(scrollYProgress, [0.15, 0.35], [0, 0.8])
            }}
          />

          {/* Contenedor del contenido con más padding */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="max-w-5xl mx-auto px-8 md:px-12 lg:px-16 text-center">
              
              {/* Nombre del fotógrafo - Mantiene Bebas Neue */}
              <motion.h1
                className="bebas-neue-regular text-5xl md:text-7xl lg:text-8xl text-[#FFF500] mb-12 uppercase tracking-wider"
                style={{ 
                  fontFamily: '"Bebas Neue", sans-serif',
                  fontWeight: 400,
                  fontStyle: 'normal',
                  textShadow: '0 4px 30px rgba(0,0,0,0.9)',
                  opacity: nameOpacity,
                  y: nameY
                }}
              >
                ALEJANDRO BENÍTEZ
              </motion.h1>
              
              {/* Biografía con Century Gothic según manual de marca */}
              <div className="text-white/95 text-base md:text-lg lg:text-xl leading-relaxed space-y-3">
                {lines.map((line, index) => {
                  // Calcular cuándo debe aparecer cada línea
                  const startProgress = 0.22 + (index * 0.33 / lines.length)
                  const endProgress = Math.min(startProgress + 0.05, 0.55)
                  
                  const lineOpacity = useTransform(
                    scrollYProgress, 
                    [startProgress, endProgress], 
                    [0, 1]
                  )
                  
                  const lineY = useTransform(
                    scrollYProgress,
                    [startProgress, endProgress],
                    [20, 0]
                  )
                  
                  return (
                    <motion.p
                      key={index}
                      className="mb-2 century-gothic"
                      style={{
                        fontFamily: "'Century Gothic', CenturyGothic, sans-serif",
                        fontWeight: 400,
                        letterSpacing: '0.02em',
                        opacity: lineOpacity,
                        y: lineY,
                        textShadow: '0 2px 20px rgba(0,0,0,0.9)'
                      }}
                    >
                      {line.split(' ').map((word, wordIndex) => (
                        <span
                          key={wordIndex}
                          className="inline-block mr-2"
                          style={{
                            color: word === 'Fractalia' ? '#FFF500' : 'inherit',
                            fontWeight: word === 'Fractalia' ? 600 : 400,
                          }}
                        >
                          {word}
                        </span>
                      ))}
                    </motion.p>
                  )
                })}
              </div>

              {/* Información de contacto - También con Century Gothic */}
              <motion.p 
                className="text-[#FFF500] text-xl md:text-2xl mt-12 century-gothic"
                style={{
                  fontFamily: "'Century Gothic', CenturyGothic, sans-serif",
                  fontWeight: 500,
                  letterSpacing: '0.05em',
                  opacity: useTransform(scrollYProgress, [0.52, 0.57], [0, 1]),
                  y: useTransform(scrollYProgress, [0.52, 0.57], [20, 0]),
                  textShadow: '0 2px 20px rgba(0,0,0,0.9)'
                }}
              >
                +595 986 966 064
              </motion.p>
            </div>
          </div>

          {/* Indicador de scroll */}
          <motion.div
            className="absolute bottom-10 left-1/2 transform -translate-x-1/2"
            animate={{ 
              y: [0, 15, 0],
            }}
            transition={{ 
              y: { duration: 2, repeat: Infinity, ease: "easeInOut" },
            }}
            style={{
              opacity: useTransform(scrollYProgress, [0, 0.1, 0.55, 0.6], [1, 1, 1, 0])
            }}
          >
            <svg
              className="w-6 h-10 text-white/50"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 40"
            >
              <rect x="1" y="1" width="22" height="38" rx="11" strokeWidth="2"/>
              <circle cx="12" cy="10" r="2" fill="currentColor"/>
            </svg>
          </motion.div>
        </div>
      </div>
      
      {/* Separador limpio */}
      <div className="w-full h-px bg-black"></div>
    </>
  )
}