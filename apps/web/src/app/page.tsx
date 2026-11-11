import { configured, getSession } from '@/lib/session';
import { Studio } from '@/components/Studio';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

export default async function Page() {
  const session = await getSession();
  if (session) return <Studio subject={session.subject} />;
  return <main className="welcome">
    <header className="welcome-header"><Link className="wordmark" href="/">Atelier<span>OS</span><i /></Link>
      <span className="eyebrow">A workspace for considered design</span></header>
    <section className="welcome-content">
      <div><p className="eyebrow">FROM FIRST STROKE TO FINAL SIGN-OFF</p>
        <h1>Your vision.<br />Every detail,<br /><em>kept.</em></h1>
        <p className="welcome-copy">A working studio for garment design. Sketch freely,
          preserve the details that matter, and keep every decision connected.</p>
        {configured() ? <a className="button primary" href="/auth/login">Enter your studio <span aria-hidden>↗</span></a>
          : <p className="notice">Workspace sign-in is awaiting an administrator connection.</p>}
        <p className="fineprint">Designer-controlled. Versioned by design.</p>
      </div>
      <figure className="garment-study" aria-label="Illustrative blouse drawing, not a saved design">
        <div className="study-meta"><span>GARMENT STUDY</span><span>NO. 001</span></div>
        <svg viewBox="0 0 500 540" role="img" aria-label="Editable blouse silhouette illustration">
          <defs><pattern id="grid" width="25" height="25" patternUnits="userSpaceOnUse"><path d="M 25 0 L 0 0 0 25" fill="none" stroke="#dcd9d1" strokeWidth=".5"/></pattern></defs>
          <rect width="500" height="540" fill="url(#grid)"/>
          <g fill="none" stroke="#334d48" strokeWidth="1.5" strokeLinejoin="round">
            <path d="M170 115L120 138L58 266L122 297L157 214L156 400Q250 425 344 400L343 214L378 297L442 266L380 138L330 115"/>
            <path d="M170 115Q182 215 250 220Q318 215 330 115M170 115L193 103Q250 172 307 103L330 115"/>
            <path d="M157 214Q155 167 120 138M343 214Q345 167 380 138M156 385Q250 410 344 385" strokeDasharray="4 4"/>
            <path d="M208 249L199 381M292 249L301 381M122 297L114 313L50 282L58 266M378 297L386 313L450 282L442 266"/>
          </g>
          <g stroke="#b18550" fill="#b18550"><circle cx="250" cy="220" r="4"/><path d="M250 220L349 68H418" fill="none"/></g>
          <text x="354" y="59" fontSize="10" letterSpacing="1.5" fill="#7d643e">DESIGN INTENT</text>
          <path d="M250 81V452" stroke="#aaa69a" strokeDasharray="3 6"/>
        </svg>
        <figcaption><span>Ideas evolve. Intent remains.</span><span className="fineprint">Illustration · not a technical specification</span></figcaption>
      </figure>
    </section>
    <footer className="welcome-footer"><span>ATELIEROS / THE DESIGN STUDIO</span>
      <span>Sketch → Review → Preserve</span></footer>
  </main>;
}
