import { useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import gsap from 'gsap'

export default function Home() {
  const container = useRef<HTMLDivElement>(null)
  const nav = useNavigate()

  useEffect(() => {
    const tl = gsap.timeline({ defaults: { duration: 1.2, ease: 'power2.out' } })
    tl.from(container.current, { backgroundColor: '#fde68a' })
      .to(container.current, { backgroundColor: '#fff' })
      .from('.hero-img', { opacity: 0, scale: 1.1 }, '-=1')

    // Al final, habilita el click para navegar
    tl.call(() => container.current?.addEventListener('click', () => nav('/categoria')))
  }, [nav])

  return (
    <div
      ref={container}
      className="min-h-screen flex items-center justify-center cursor-pointer"
    >
      <img
        className="hero-img w-full max-w-md object-cover rounded-2xl shadow-lg"
        src="/assets/hero.jpg"
        alt="Portada"
      />
    </div>
  )
}
