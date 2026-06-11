import { useState } from 'react';
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  Clock,
  Film,
  Info,
  Menu,
  MessageCircle,
  Play,
  Search,
  Star,
  Tv,
  User,
  X,
} from 'lucide-react';

const videoUrl =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260406_094145_4a271a6c-3869-4f1c-8aa7-aeb0cb227994.mp4';

const navLinks = [
  { label: 'Movies', id: 'movies' },
  { label: 'TV Series', id: 'tv-series' },
  { label: "Editor's Pick", id: 'editors-pick' },
  { label: 'Interviews', id: 'interviews' },
  { label: 'User Reviews', id: 'user-reviews' },
];

const movies = [
  { title: 'Shadow Gate', year: '2026', rating: '8.7', meta: 'Action thriller', style: 'from-red-500/70 via-zinc-900 to-black' },
  { title: 'Eclipse Run', year: '2025', rating: '8.4', meta: 'Sci-fi drama', style: 'from-amber-300/60 via-slate-700 to-black' },
  { title: 'Beyond the Line', year: '2026', rating: '8.1', meta: 'Survival story', style: 'from-sky-300/60 via-slate-800 to-black' },
  { title: 'Neon Dawn', year: '2025', rating: '8.3', meta: 'Cyber noir', style: 'from-fuchsia-500/60 via-indigo-900 to-black' },
  { title: 'Silent Oath', year: '2024', rating: '7.9', meta: 'Mystery', style: 'from-zinc-300/50 via-zinc-800 to-black' },
];

const series = [
  { title: 'Nightfall', episode: 'S1 - E1', runtime: '47m', summary: 'A detective follows impossible evidence through a city that never sleeps.' },
  { title: 'Black Harbor', episode: 'S1 - E6', runtime: '52m', summary: 'Old alliances collapse when a missing ship returns with no crew.' },
  { title: 'The Protocol', episode: 'S1 - E5', runtime: '46m', summary: 'Trust becomes a liability after a leaked file rewrites the mission.' },
];

const interviews = [
  { title: 'Inside the visual language', label: 'Director Spotlight', text: 'How lighting, pace, and quiet frames shape the world behind the story.' },
  { title: 'Building the impossible set', label: 'Behind the Scenes', text: 'A production crew breakdown of the practical locations and digital extensions.' },
];

const reviews = [
  { name: 'Aravind S.', text: 'A sharp, atmospheric watch with a clean interface that feels premium.', rating: '5.0' },
  { name: 'Meera K.', text: 'The details page makes the story feel organized without slowing the mood.', rating: '4.8' },
  { name: 'Rohan M.', text: 'Strong visual style, useful navigation, and a polished streaming feel.', rating: '4.7' },
];

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
              key={link.id}
              href={`#${link.id}`}
              className="animate-blur-fade-up text-sm text-white transition-colors hover:text-gray-300"
              style={animationDelay(100 + index * 50)}
            >
              {link.label}
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
              key={link.id}
              href={`#${link.id}`}
              className={`rounded-lg px-3 py-3 text-sm text-white transition duration-500 ease-out hover:bg-gray-800/50 ${
                menuOpen ? 'translate-x-0 opacity-100' : '-translate-x-4 opacity-0'
              }`}
              style={{ transitionDelay: `${index * 50}ms` }}
              tabIndex={menuOpen ? 0 : -1}
              onClick={() => setMenuOpen(false)}
            >
              {link.label}
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
              onClick={() => document.getElementById('movies')?.scrollIntoView({ behavior: 'smooth' })}
            >
              <Play size={18} className="fill-black" />
              <span>Watch Now</span>
            </button>
            <GlassButton
              className="px-6 py-2.5 sm:px-8 sm:py-3"
              delay={700}
              onClick={() => document.getElementById('editors-pick')?.scrollIntoView({ behavior: 'smooth' })}
            >
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

function SectionHeader({ icon, title, action = 'View All' }) {
  return (
    <div className="mb-5 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <span className="liquid-glass inline-flex h-9 w-9 items-center justify-center rounded-full text-white">
          {icon}
        </span>
        <h2 className="text-2xl font-semibold text-white sm:text-3xl">{title}</h2>
      </div>
      <button type="button" className="hidden text-sm font-medium text-gray-300 transition hover:text-white sm:inline">
        {action}
      </button>
    </div>
  );
}

function PosterCard({ item, index }) {
  return (
    <article className="group min-w-[168px] overflow-hidden rounded-lg border border-white/10 bg-white/[0.03] sm:min-w-[210px]">
      <div className={`relative flex aspect-[2/3] items-end bg-gradient-to-br ${item.style} p-4`}>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_35%_20%,rgba(255,255,255,0.22),transparent_26%),linear-gradient(to_top,rgba(0,0,0,0.88),transparent_58%)]" />
        <button
          type="button"
          aria-label={`Play ${item.title}`}
          className="liquid-glass !absolute left-4 top-4 flex h-11 w-11 items-center justify-center rounded-full transition group-hover:scale-105"
        >
          <Play size={18} className="fill-white" />
        </button>
        <div className="relative">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-300">Feature {index + 1}</p>
          <h3 className="mt-2 text-2xl font-semibold leading-none text-white">{item.title}</h3>
          <p className="mt-2 text-sm text-gray-300">{item.year} • {item.rating}</p>
        </div>
      </div>
      <div className="p-4">
        <p className="text-sm text-gray-300">{item.meta}</p>
      </div>
    </article>
  );
}

function MoviesSection() {
  return (
    <section id="movies" className="border-t border-white/10 bg-black/90 px-4 py-14 text-white sm:px-6 md:px-12">
      <SectionHeader icon={<Film size={18} />} title="Movies" />
      <div className="flex gap-4 overflow-x-auto pb-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {movies.map((movie, index) => (
          <PosterCard key={movie.title} item={movie} index={index} />
        ))}
      </div>
    </section>
  );
}

function SeriesSection() {
  return (
    <section id="tv-series" className="bg-zinc-950 px-4 py-14 text-white sm:px-6 md:px-12">
      <SectionHeader icon={<Tv size={18} />} title="TV Series" />
      <div className="grid gap-4 md:grid-cols-3">
        {series.map((show, index) => (
          <article key={show.title} className="overflow-hidden rounded-lg border border-white/10 bg-white/[0.04]">
            <div className={`h-36 bg-gradient-to-br ${movies[index + 1]?.style || movies[0].style}`}>
              <div className="flex h-full items-end bg-[linear-gradient(to_top,rgba(0,0,0,0.82),transparent)] p-4">
                <button type="button" className="liquid-glass flex h-10 w-10 items-center justify-center rounded-full">
                  <Play size={16} className="fill-white" />
                </button>
              </div>
            </div>
            <div className="p-5">
              <div className="flex items-center justify-between text-xs uppercase text-gray-400">
                <span>{show.episode}</span>
                <span>{show.runtime}</span>
              </div>
              <h3 className="mt-3 text-xl font-semibold text-white">{show.title}</h3>
              <p className="mt-2 text-sm leading-6 text-gray-300">{show.summary}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function EditorsPickSection() {
  return (
    <section id="editors-pick" className="bg-black/90 px-4 py-14 text-white sm:px-6 md:px-12">
      <SectionHeader icon={<Info size={18} />} title="Editor's Pick" action="Details" />
      <div className="grid overflow-hidden rounded-lg border border-white/10 bg-white/[0.04] md:grid-cols-[1.1fr_1fr]">
        <div className="min-h-[300px] bg-gradient-to-br from-sky-200/70 via-slate-700 to-black">
          <div className="flex h-full items-end bg-[linear-gradient(to_top,rgba(0,0,0,0.82),transparent_62%)] p-6">
            <p className="max-w-sm text-sm uppercase tracking-[0.28em] text-white/70">World Premiere</p>
          </div>
        </div>
        <div className="p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-red-300">Editor's Pick</p>
          <h3 className="mt-3 text-3xl font-semibold leading-tight text-white sm:text-4xl">The Last Frontier</h3>
          <p className="mt-3 text-sm font-medium text-gray-300">2026 • Adventure Drama • 2h 04m • 8.3</p>
          <p className="mt-5 max-w-xl text-base leading-8 text-gray-300">
            A traveler reaches the edge of a forgotten realm and has to choose between a promised future and the truth
            buried in the past.
          </p>
          <div className="mt-7 grid gap-4 text-sm text-gray-300 sm:grid-cols-2">
            <div>
              <p className="text-white">Director</p>
              <p>Martin Hale</p>
            </div>
            <div>
              <p className="text-white">Languages</p>
              <p>English, Hindi, Tamil</p>
            </div>
            <div>
              <p className="text-white">Available in</p>
              <p>4K • HDR • 5.1</p>
            </div>
            <div>
              <p className="text-white">Category</p>
              <p>Fantasy, Adventure</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function InterviewsSection() {
  return (
    <section id="interviews" className="bg-zinc-950 px-4 py-14 text-white sm:px-6 md:px-12">
      <SectionHeader icon={<MessageCircle size={18} />} title="Interviews" />
      <div className="grid gap-4 lg:grid-cols-2">
        {interviews.map((interview, index) => (
          <article
            key={interview.title}
            className={`overflow-hidden rounded-lg border border-white/10 bg-gradient-to-br ${movies[index]?.style || movies[0].style}`}
          >
            <div className="min-h-[220px] bg-[linear-gradient(to_right,rgba(0,0,0,0.88),rgba(0,0,0,0.2))] p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-red-300">{interview.label}</p>
              <h3 className="mt-12 max-w-md text-2xl font-semibold text-white">{interview.title}</h3>
              <p className="mt-3 max-w-md text-sm leading-6 text-gray-300">{interview.text}</p>
              <button type="button" className="liquid-glass mt-5 inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium">
                <Play size={15} className="fill-white" />
                Watch Interview
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ReviewsSection() {
  return (
    <section id="user-reviews" className="min-h-screen bg-black px-4 py-14 text-white sm:px-6 md:px-12">
      <SectionHeader icon={<Star size={18} className="fill-white" />} title="User Reviews" />
      <div className="grid gap-4 lg:grid-cols-[0.8fr_1fr_1fr_1fr]">
        <article className="rounded-lg border border-white/10 bg-white/[0.04] p-6">
          <p className="text-5xl font-semibold">4.8</p>
          <div className="mt-3 flex gap-1 text-red-300">
            {Array.from({ length: 5 }).map((_, index) => (
              <Star key={index} size={18} className="fill-current" />
            ))}
          </div>
          <p className="mt-4 text-sm text-gray-400">Based on 12.8K viewer reviews</p>
        </article>
        {reviews.map((review) => (
          <article key={review.name} className="rounded-lg border border-white/10 bg-white/[0.04] p-6">
            <p className="text-sm leading-7 text-gray-200">“{review.text}”</p>
            <div className="mt-6 flex items-center justify-between border-t border-white/10 pt-4">
              <span className="text-sm font-medium text-white">{review.name}</span>
              <span className="text-sm text-red-300">{review.rating}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function StreamingSections() {
  return (
    <div className="relative z-10">
      <MoviesSection />
      <SeriesSection />
      <EditorsPickSection />
      <InterviewsSection />
      <ReviewsSection />
    </div>
  );
}

export default function App() {
  return (
    <div id="top" className="relative min-h-screen overflow-x-hidden bg-black font-inter">
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
      <StreamingSections />
    </div>
  );
}
