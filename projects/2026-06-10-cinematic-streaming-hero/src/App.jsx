import { useState } from 'react';
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  Clock,
  Menu,
  Play,
  Search,
  Star,
  User,
  X,
} from 'lucide-react';

const videoUrl =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260406_094145_4a271a6c-3869-4f1c-8aa7-aeb0cb227994.mp4';

const navLinks = ['Movies', 'TV Series', "Editor's Pick", 'Interviews', 'User Reviews'];

function animationDelay(ms) {
  return { animationDelay: `${ms}ms` };
}

function GlassButton({ children, className = '', delay = 0, ariaLabel, ...buttonProps }) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      {...buttonProps}
      className={`liquid-glass animate-blur-fade-up inline-flex items-center justify-center gap-2 rounded-full text-sm font-medium text-white transition-colors duration-300 hover:text-gray-200 ${className}`}
      style={animationDelay(delay)}
    >
      {children}
    </button>
  );
}

function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="relative z-50 px-4 py-4 text-white sm:px-6 md:px-12 md:py-6">
      <nav className="flex items-center justify-between">
        <div className="flex min-w-0 items-center gap-3 sm:gap-4">
          <a
            href="#top"
            className="animate-blur-fade-up block h-8 shrink-0 text-base font-semibold leading-8 text-white md:h-10 md:text-lg md:leading-10"
            style={animationDelay(0)}
          >
            CINEMATIC
          </a>
          <span
            className="animate-blur-fade-up whitespace-nowrap text-[11px] font-medium uppercase text-gray-300/90 sm:text-xs"
            style={animationDelay(80)}
          >
            Built By Nagadeepak
          </span>
        </div>

        <div className="hidden items-center gap-8 lg:flex">
          {navLinks.map((link, index) => (
            <a
              key={link}
              href={`#${link.toLowerCase().replaceAll(' ', '-')}`}
              className="animate-blur-fade-up text-sm text-white transition-colors hover:text-gray-300"
              style={animationDelay(100 + index * 50)}
            >
              {link}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <GlassButton className="hidden px-4 py-2 sm:inline-flex md:px-6" delay={350}>
            <span>Search</span>
            <Search size={18} />
          </GlassButton>

          <GlassButton className="hidden h-10 w-10 sm:inline-flex" delay={400} ariaLabel="Open profile">
            <User size={18} />
          </GlassButton>

          <GlassButton
            className="h-10 w-10 lg:hidden"
            delay={350}
            ariaLabel={menuOpen ? 'Close menu' : 'Open menu'}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span className="relative h-5 w-5">
              <Menu
                size={20}
                className={`absolute inset-0 transition duration-500 ease-out ${
                  menuOpen ? 'rotate-180 scale-50 opacity-0' : 'rotate-0 scale-100 opacity-100'
                }`}
              />
              <X
                size={20}
                className={`absolute inset-0 transition duration-500 ease-out ${
                  menuOpen ? 'rotate-0 scale-100 opacity-100' : '-rotate-180 scale-50 opacity-0'
                }`}
              />
            </span>
          </GlassButton>
        </div>
      </nav>

      <div
        aria-hidden={!menuOpen}
        inert={menuOpen ? undefined : ''}
        className={`fixed left-0 right-0 top-[72px] z-40 bg-gray-900/95 px-4 py-4 shadow-2xl backdrop-blur-lg transition duration-500 ease-out sm:px-6 lg:hidden ${
          menuOpen ? 'translate-y-0 opacity-100' : 'pointer-events-none -translate-y-4 opacity-0'
        } border-y border-gray-800`}
      >
        <div className="mx-auto flex max-w-3xl flex-col gap-1">
          {navLinks.map((link, index) => (
            <a
              key={link}
              href={`#${link.toLowerCase().replaceAll(' ', '-')}`}
              className={`rounded-lg px-3 py-3 text-sm text-white transition duration-500 ease-out hover:bg-gray-800/50 ${
                menuOpen ? 'translate-x-0 opacity-100' : '-translate-x-4 opacity-0'
              }`}
              style={{ transitionDelay: `${index * 50}ms` }}
              tabIndex={menuOpen ? 0 : -1}
              onClick={() => setMenuOpen(false)}
            >
              {link}
            </a>
          ))}

          <div className="mt-3 grid grid-cols-2 gap-3 border-t border-gray-800 pt-4 sm:hidden">
            <GlassButton className="px-4 py-2.5" delay={0} tabIndex={menuOpen ? 0 : -1}>
              <span>Search</span>
              <Search size={18} />
            </GlassButton>
            <GlassButton className="px-4 py-2.5" delay={0} tabIndex={menuOpen ? 0 : -1}>
              <User size={18} />
              <span>Profile</span>
            </GlassButton>
          </div>
        </div>
      </div>
    </header>
  );
}

function MetadataItem({ icon, label }) {
  return (
    <span className="inline-flex items-center gap-2">
      {icon}
      <span>{label}</span>
    </span>
  );
}

function HeroContent() {
  return (
    <section className="relative z-10 flex flex-1 flex-col justify-end px-4 pb-8 text-white sm:px-6 md:px-12 md:pb-16">
      <div className="flex flex-col items-start gap-8 md:flex-row md:items-end">
        <div className="flex-1">
          <div
            className="animate-blur-fade-up mb-6 flex flex-wrap items-center gap-3 text-xs font-medium text-white sm:gap-6 sm:text-sm md:mb-8"
            style={animationDelay(300)}
          >
            <MetadataItem
              icon={<Star size={16} className="fill-white sm:h-5 sm:w-5" />}
              label="8.7/10 IMDB"
            />
            <MetadataItem icon={<Clock size={16} className="sm:h-5 sm:w-5" />} label="132 min" />
            <MetadataItem
              icon={<Calendar size={16} className="sm:h-5 sm:w-5" />}
              label="April, 2025"
            />
          </div>

          <h1
            className="animate-blur-fade-up mb-4 max-w-5xl text-3xl font-normal leading-[0.95] sm:text-5xl md:mb-6 md:text-6xl lg:text-7xl"
            style={animationDelay(400)}
          >
            Step Through. Work Smarter.
          </h1>

          <p
            className="animate-blur-fade-up mb-6 max-w-2xl text-base leading-7 text-gray-400 sm:text-lg md:mb-12 md:text-xl md:leading-8"
            style={animationDelay(500)}
          >
            A voyage through forgotten realms, where past and future intertwine.
          </p>

          <div className="flex flex-wrap gap-3 sm:gap-4">
            <button
              type="button"
              className="animate-blur-fade-up inline-flex items-center justify-center gap-2 rounded-full bg-white px-6 py-2.5 text-sm font-medium text-black transition-colors hover:bg-gray-200 sm:px-8 sm:py-3"
              style={animationDelay(600)}
            >
              <Play size={18} className="fill-black" />
              <span>Watch Now</span>
            </button>
            <GlassButton className="px-6 py-2.5 sm:px-8 sm:py-3" delay={700}>
              Learn More
            </GlassButton>
          </div>
        </div>

        <div className="flex w-full justify-start gap-3 md:w-auto md:justify-end">
          <GlassButton className="px-4 py-2.5 sm:px-6 sm:py-3" delay={800}>
            <ChevronLeft size={18} />
            <span>Previous</span>
          </GlassButton>
          <GlassButton className="px-4 py-2.5 sm:px-6 sm:py-3" delay={900}>
            <span>Next</span>
            <ChevronRight size={18} />
          </GlassButton>
        </div>
      </div>
    </section>
  );
}

export default function App() {
  return (
    <div id="top" className="relative flex min-h-screen overflow-hidden bg-black font-inter">
      <video
        className="fixed inset-0 z-0 h-screen w-screen object-cover"
        src={videoUrl}
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        aria-hidden="true"
      />
      <div className="bottom-blur-overlay" aria-hidden="true" />
      <main className="relative z-10 flex min-h-screen w-full flex-col">
        <Navbar />
        <HeroContent />
      </main>
    </div>
  );
}
