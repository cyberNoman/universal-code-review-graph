import { useRef, useLayoutEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const features = [
  {
    number: '01',
    title: 'Build the graph once',
    description: 'Index functions, classes, imports, and calls into a queryable structure—stored locally, owned by you.',
    image: '/feature_typing.jpg'
  },
  {
    number: '02',
    title: 'Review with context',
    description: 'Ask the graph for impacted symbols. Get a minimal, precise context window instead of whole files.',
    image: '/feature_planning.jpg'
  },
  {
    number: '03',
    title: 'Stay in sync',
    description: 'Rebuild in seconds after merges. Keep the graph fresh without manual bookkeeping.',
    image: '/feature_collab.jpg'
  }
];

export default function Features() {
  const sectionRef = useRef<HTMLElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);
  const panelsRef = useRef<(HTMLDivElement | null)[]>([]);
  const numbersRef = useRef<(HTMLSpanElement | null)[]>([]);
  const textsRef = useRef<(HTMLDivElement | null)[]>([]);
  const dividersRef = useRef<(HTMLDivElement | null)[]>([]);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    if (!section) return;

    const ctx = gsap.context(() => {
      const panels = panelsRef.current.filter(Boolean);
      const numbers = numbersRef.current.filter(Boolean);
      const texts = textsRef.current.filter(Boolean);
      const dividers = dividersRef.current.filter(Boolean);

      // Scroll-driven animation
      const scrollTl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: 'top top',
          end: '+=130%',
          pin: true,
          scrub: 0.6,
        }
      });

      // ENTRANCE (0-30%)
      scrollTl
        .fromTo(headerRef.current,
          { opacity: 0, y: -20 },
          { opacity: 1, y: 0, ease: 'none' },
          0
        )
        .fromTo(panels[0],
          { y: '-40vh', opacity: 0 },
          { y: 0, opacity: 1, ease: 'power2.out' },
          0
        )
        .fromTo(panels[1],
          { y: '40vh', opacity: 0 },
          { y: 0, opacity: 1, ease: 'power2.out' },
          0.06
        )
        .fromTo(panels[2],
          { y: '-40vh', opacity: 0 },
          { y: 0, opacity: 1, ease: 'power2.out' },
          0.1
        )
        .fromTo(numbers,
          { x: '-3vw', opacity: 0 },
          { x: 0, opacity: 1, stagger: 0.03, ease: 'power2.out' },
          0.15
        )
        .fromTo(texts,
          { y: '6vh', opacity: 0 },
          { y: 0, opacity: 1, stagger: 0.03, ease: 'power2.out' },
          0.18
        )
        .fromTo(dividers,
          { scaleX: 0, scaleY: 0 },
          { scaleX: 1, scaleY: 1, stagger: 0.02, ease: 'power2.out' },
          0.1
        );

      // SETTLE (30-70%): Hold position

      // EXIT (70-100%)
      scrollTl
        .fromTo(panels[0],
          { x: 0, opacity: 1 },
          { x: '-12vw', opacity: 0.25, ease: 'power2.in' },
          0.7
        )
        .fromTo(panels[1],
          { y: 0, opacity: 1 },
          { y: '-10vh', opacity: 0.25, ease: 'power2.in' },
          0.72
        )
        .fromTo(panels[2],
          { x: 0, opacity: 1 },
          { x: '12vw', opacity: 0.25, ease: 'power2.in' },
          0.74
        )
        .fromTo(headerRef.current,
          { opacity: 1 },
          { opacity: 0, ease: 'power2.in' },
          0.75
        );

    }, section);

    return () => ctx.revert();
  }, []);

  return (
    <section 
      ref={sectionRef} 
      className="section-pinned bg-[#0B0F17] z-20"
    >
      {/* Micro header */}
      <div 
        ref={headerRef}
        className="absolute top-[6vh] left-1/2 -translate-x-1/2"
      >
        <span className="mono text-xs text-[#A7B1C6] tracking-[0.12em] uppercase">
          Why It Works
        </span>
      </div>

      {/* Three panels */}
      <div className="absolute top-[12vh] left-0 w-full h-[88vh] flex">
        {features.map((feature, index) => (
          <div
            key={feature.number}
            ref={el => { panelsRef.current[index] = el; }}
            className="relative h-full flex flex-col"
            style={{ 
              width: index === 0 ? '34vw' : index === 1 ? '33vw' : '33vw',
              left: index === 0 ? 0 : index === 1 ? '34vw' : '67vw'
            }}
          >
            {/* Divider line (right border for first two) */}
            {index < 2 && (
              <div 
                ref={el => { dividersRef.current[index] = el; }}
                className="absolute right-0 top-0 w-px h-full bg-white/20"
              />
            )}
            
            {/* Top border */}
            <div 
              ref={el => { dividersRef.current[index + 2] = el; }}
              className="absolute top-0 left-0 right-0 h-px bg-white/20"
            />

            {/* Photo */}
            <div className="relative h-[55%] overflow-hidden">
              <img 
                src={feature.image}
                alt={feature.title}
                className="w-full h-full object-cover"
                loading="lazy"
                decoding="async"
              />
              <div className="scanline" />
            </div>

            {/* Number */}
            <span 
              ref={el => { numbersRef.current[index] = el; }}
              className="absolute top-[6vh] left-[2.2vw] text-[clamp(48px,6vw,80px)] font-bold text-[#4B6BFF]/30 font-['Space_Grotesk']"
            >
              {feature.number}
            </span>

            {/* Text content */}
            <div 
              ref={el => { textsRef.current[index] = el; }}
              className="flex-1 px-[2.2vw] pt-8 pb-8 flex flex-col justify-center"
            >
              <h3 className="text-[clamp(20px,2vw,28px)] font-semibold text-[#F2F5FA] mb-4">
                {feature.title}
              </h3>
              <p className="text-[#A7B1C6] text-base leading-relaxed max-w-[28vw]">
                {feature.description}
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
