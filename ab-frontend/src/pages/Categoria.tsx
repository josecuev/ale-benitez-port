import { useRef, useEffect } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { FiArrowLeft } from 'react-icons/fi'
import { useNavigate } from 'react-router-dom'

gsap.registerPlugin(ScrollTrigger)

const IMAGES = [
  '/assets/1.jpg',
  '/assets/2.jpg',
  '/assets/3.jpg',
  // añade tus fotos aquí...
]

export default function Categoria() {
  const gallery = useRef<HTMLDivElement>(null)
  const nav = useNavigate()

  useEffect(() => {
    const totalScroll = gallery.current!.scrollWidth - window.innerWidth
    gsap.to(gallery.current, {
      x: -totalScroll,
      ease: 'none',
      scrollTrigger: {
        trigger: gallery.current,
        start: 'top top',
        end: () => `+=${totalScroll}`,
        scrub: true,
        pin: true,
      },
    })
  }, [])

  return (
    <div className="relative min-h-screen bg-white">
      <button
        onClick={() => nav(-1)}
        className="absolute top-4 left-4 p-2 rounded-full bg-white shadow"
      >
        <FiArrowLeft size={24} />
      </button>

      <div
        ref={gallery}
        className="flex space-x-4 py-20 px-8"
        style={{ willChange: 'transform' }}
      >
        {IMAGES.map((src) => (
          <img
            key={src}
            src={src}
            className="w-80 h-auto rounded-2xl shadow-lg"
            alt=""
          />
        ))}
      </div>
    </div>
  )
}
