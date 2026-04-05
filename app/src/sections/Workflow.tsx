import { useRef, useLayoutEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

gsap.registerPlugin(ScrollTrigger);

const steps = [
  {
    number: '1',
    title: 'Add the MCP server.',
    subtitle: 'stdio, HTTP, or SSE—your choice.'
  },
  {
    number: '2',
    title: 'Build the graph.',
    subtitle: 'One command indexes your codebase.'
  },
  {
    number: '3',
    title: 'Query on demand.',
    subtitle: 'Review, impact, navigate—minimal context.'
  },
  {
    number: '4',
    title: 'Keep it fresh.',
    subtitle: 'Rebuild after big merges. Takes seconds.'
  }
];

export default function Workflow() {
  const sectionRef = useRef<HTMLElement>(null);
  const portraitCardRef = useRef<HTMLDivElement>(null);
  const stepsCardRef = useRef<HTMLDivElement>(null);
  const stepNumbersRef = useRef<(HTMLDivElement | null)[]>([]);
  const connectorRef = useRef<HTMLDivElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    if (!section) return;

    const ctx = gsap.context(() => {
      const stepNumbers = stepNumbersRef.current.filter(Boolean);

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
        .fromTo(portraitCardRef.current,
          { x: '-40vw', opacity: 0 },
          { x: 0, opacity: 1, ease: 'power2.out' },
          0
        )
        .fromTo(stepsCardRef.current,
          { x: '40vw', opacity: 0 },
          { x: 0, opacity: 1, ease: 'power2.out' },
          0.08
        )
        .fromTo(stepNumbers,
          { scale: 0.8, opacity: 0 },
          { scale: 1, opacity: 1, stagger: 0.03, ease: 'power2.out' },
          0.15
        )
        .fromTo(connectorRef.current,
          { scaleY: 0 },
          { scaleY: 1, ease: 'power2.out' },
          0.12
        )
        .fromTo(ctaRef.current,
          { opacity: 0, y: 15 },
          { opacity: 1, y: 0, ease: 'power2.out' },
          0.25
        );

      // SETTLE (30-70%): Hold with subtle number pulse (handled by CSS)

      // EXIT (70-100%)
      scrollTl
        .fromTo([portraitCardRef.current, stepsCardRef.current],
          { y: 0, opacity: 1 },
          { y: '16vh', opacity: 0, stagger: 0.02, ease: 'power2.in' },
          0.7
        )
        .fromTo(connectorRef.current,
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
      className="section-pinned bg-[#0B0F17] z-40 flex items-center justify-center"
    >
      {/* Portrait Card */}
      <div 
        ref={portraitCardRef}
        className="blueprint-card absolute left-[6vw] top-[16vh] w-[40vw] h-[68vh] overflow-hidden"
      >
        <img 
          src="/workflow_portrait.jpg"
          alt="Developer with notebook"
          className="w-full h-full object-cover"
          loading="lazy"
          decoding="async"
        />
        <div className="scanline" />
      </div>

      {/* Steps Card */}
      <div 
        ref={stepsCardRef}
        className="blueprint-card absolute left-[54vw] top-[16vh] w-[40vw] h-[68vh] p-8 flex flex-col"
      >
        <h2 className="text-[clamp(24px,2.5vw,36px)] font-semibold text-[#F2F5FA] mb-8">
          How to run it
        </h2>

        {/* Connector line */}
        <div 
          ref={connectorRef}
          className="absolute left-12 top-[100px] w-px h-[calc(100%-180px)] bg-[#4B6BFF]/30"
          style={{ transformOrigin: 'top' }}
        />

        {/* Steps */}
        <div className="flex-1 flex flex-col justify-center gap-6">
          {steps.map((step, index) => (
            <div key={step.number} className="flex items-start gap-5">
              <div 
                ref={el => { stepNumbersRef.current[index] = el; }}
                className="w-10 h-10 rounded-full bg-[#4B6BFF]/20 border border-[#4B6BFF]/40 flex items-center justify-center flex-shrink-0"
              >
                <span className="text-[#4B6BFF] font-semibold text-sm">
                  {step.number}
                </span>
              </div>
              <div>
                <h3 className="text-[#F2F5FA] font-medium text-base mb-1">
                  {step.title}
                </h3>
                <p className="text-[#A7B1C6] text-sm">
                  {step.subtitle}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div ref={ctaRef} className="mt-auto">
          <Button 
            variant="outline"
            className="border-[#4B6BFF]/50 text-[#4B6BFF] hover:bg-[#4B6BFF]/10 px-5 py-2.5 h-auto text-sm font-medium rounded-md flex items-center gap-2"
          >
            View Installation Guide
            <ArrowRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </section>
  );
}
