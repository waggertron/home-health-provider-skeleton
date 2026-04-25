import { ContactForm } from '@/components/ContactForm';

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? 'http://localhost:3001';

const FEATURES = [
  {
    title: 'AI-driven scheduling',
    body: 'OR-Tools VRP solver with credential constraints + time windows, plus a sklearn re-ranker scoring historical clinician–patient fit.',
  },
  {
    title: 'Real-time fanout',
    body: 'Every visit reassign and check-in lands on dispatcher screens within a second via a Node WebSocket gateway over Redis pub/sub.',
  },
  {
    title: 'Patient engagement',
    body: 'Templated SMS reminders + signed-link confirmations, all logged to a tenant-scoped outbox surfaceable from the ops console.',
  },
];

export default function HomePage() {
  return (
    <main>
      <Nav />
      <Hero />
      <Features />
      <Pricing />
      <Contact />
      <Footer />
    </main>
  );
}

function Nav() {
  return (
    <header className="sticky top-0 z-10 backdrop-blur bg-white/70 dark:bg-black/40 border-b border-slate-200/60 dark:border-slate-800">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <a href="#" className="font-semibold tracking-tight">
          HHPS
        </a>
        <nav className="flex items-center gap-6 text-sm">
          <a href="#features" className="opacity-80 hover:opacity-100">
            Features
          </a>
          <a href="#pricing" className="opacity-80 hover:opacity-100">
            Pricing
          </a>
          <a href="#contact" className="opacity-80 hover:opacity-100">
            Contact
          </a>
          <a
            href={APP_URL}
            className="rounded-md bg-blue-600 text-white px-4 py-1.5 text-sm font-medium hover:bg-blue-500"
          >
            Open demo →
          </a>
        </nav>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="max-w-6xl mx-auto px-6 pt-20 pb-24 text-center">
      <p className="text-xs uppercase tracking-widest text-blue-600 dark:text-blue-400">
        Home-health dispatching · portfolio demo
      </p>
      <h1 className="mt-3 text-4xl sm:text-6xl font-semibold tracking-tight">
        Route every visit.
        <br className="hidden sm:block" />
        <span className="text-blue-600 dark:text-blue-400">Watch it happen live.</span>
      </h1>
      <p className="mt-6 max-w-2xl mx-auto text-base sm:text-lg opacity-80">
        OR-Tools VRP + an ML re-ranker plan each clinician's day. A real-time gateway
        keeps every dispatcher screen in sync as visits get reassigned and checked in.
      </p>
      <div className="mt-8 flex justify-center gap-3">
        <a
          href={APP_URL}
          className="rounded-md bg-blue-600 text-white px-5 py-3 text-sm font-medium hover:bg-blue-500"
        >
          Open the live demo
        </a>
        <a
          href="#features"
          className="rounded-md border border-slate-300 dark:border-slate-700 px-5 py-3 text-sm hover:border-slate-500"
        >
          See the moving parts
        </a>
      </div>
    </section>
  );
}

function Features() {
  return (
    <section id="features" className="bg-slate-100 dark:bg-slate-950 py-24">
      <div className="max-w-6xl mx-auto px-6">
        <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight">
          Three pillars, one demo loop
        </h2>
        <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <article
              key={f.title}
              className="rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6"
            >
              <h3 className="font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm opacity-80 leading-relaxed">{f.body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function Pricing() {
  return (
    <section id="pricing" className="py-24">
      <div className="max-w-3xl mx-auto px-6 text-center">
        <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight">Pricing</h2>
        <p className="mt-3 opacity-80">
          This is a portfolio project — there's no real billing. The demo is free
          forever; production-grade pricing would be tiered by clinician headcount.
        </p>
        <div className="mt-10 inline-block rounded-lg border border-slate-200 dark:border-slate-800 p-8">
          <div className="text-sm uppercase tracking-widest opacity-60">Demo tier</div>
          <div className="mt-2 text-4xl font-semibold">$0<span className="text-base opacity-60">/mo</span></div>
          <ul className="mt-4 text-sm opacity-80 space-y-1 text-left">
            <li>· 2 seeded tenants</li>
            <li>· 25 clinicians + 300 patients per tenant</li>
            <li>· OR-Tools + ML re-ranker</li>
            <li>· Real-time updates</li>
          </ul>
        </div>
      </div>
    </section>
  );
}

function Contact() {
  return (
    <section id="contact" className="bg-slate-100 dark:bg-slate-950 py-24">
      <div className="max-w-2xl mx-auto px-6">
        <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight">Talk to a (fake) human</h2>
        <p className="mt-3 opacity-80">
          The contact form is inert in this demo — no email goes out. To kick the
          tires, just open the live console.
        </p>
        <ContactForm />
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="py-12 text-center text-xs opacity-60">
      © {new Date().getFullYear()} HHPS · Portfolio demo · Not for clinical use
    </footer>
  );
}
