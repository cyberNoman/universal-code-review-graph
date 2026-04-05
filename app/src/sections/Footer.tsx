import { useRef, useLayoutEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Github, Mail, MessageCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

gsap.registerPlugin(ScrollTrigger);

export default function Footer() {
  const sectionRef = useRef<HTMLElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    if (!section) return;

    const ctx = gsap.context(() => {
      gsap.fromTo(contentRef.current,
        { opacity: 0, y: 18 },
        {
          opacity: 1,
          y: 0,
          duration: 0.8,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: contentRef.current,
            start: 'top 85%',
          }
        }
      );
    }, section);

    return () => ctx.revert();
  }, []);

  return (
    <footer 
      ref={sectionRef} 
      className="relative bg-[#121A26] z-50 py-20"
    >
      <div 
        ref={contentRef}
        className="max-w-3xl mx-auto px-6 text-center"
      >
        <h2 className="text-[clamp(28px,3vw,40px)] font-semibold text-[#F2F5FA] mb-4">
          Built for teams who review carefully.
        </h2>
        <p className="text-[#A7B1C6] text-lg mb-10">
          Questions? Feature requests? Reach out.
        </p>

        <div className="flex justify-center gap-4 flex-wrap mb-16">
          <Button 
            className="bg-[#4B6BFF] hover:bg-[#3d5ce6] text-white px-6 py-3 h-auto text-base font-medium rounded-md flex items-center gap-2"
          >
            <Mail className="w-4 h-4" />
            Contact us
          </Button>
          <Button 
            variant="outline"
            className="border-white/30 text-[#F2F5FA] hover:bg-white/10 px-6 py-3 h-auto text-base font-medium rounded-md flex items-center gap-2"
          >
            <Github className="w-4 h-4" />
            GitHub
          </Button>
        </div>

        {/* Divider */}
        <div className="w-full h-px bg-white/10 mb-8" />

        {/* Footer bottom */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-[#A7B1C6]">
          <span>© Universal Code Review Graph — MIT License</span>
          <div className="flex items-center gap-6">
            <a href="#" className="hover:text-[#F2F5FA] transition-colors">
              Privacy
            </a>
            <a href="#" className="hover:text-[#F2F5FA] transition-colors">
              Terms
            </a>
            <a href="#" className="hover:text-[#F2F5FA] transition-colors flex items-center gap-1">
              <MessageCircle className="w-4 h-4" />
              Discord
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
