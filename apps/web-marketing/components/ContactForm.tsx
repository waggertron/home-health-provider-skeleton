'use client';

import { useState } from 'react';

export function ContactForm() {
  const [status, setStatus] = useState<string | null>(null);
  return (
    <form
      className="mt-8 space-y-3"
      aria-label="Contact form (demo only)"
      onSubmit={(e) => {
        e.preventDefault();
        setStatus('Demo only — no message was sent.');
      }}
    >
      <input
        type="email"
        placeholder="you@example.com"
        required
        className="w-full rounded-md border border-slate-300 dark:border-slate-700 bg-transparent px-4 py-2 text-sm"
      />
      <textarea
        placeholder="What problem are you trying to solve?"
        rows={4}
        className="w-full rounded-md border border-slate-300 dark:border-slate-700 bg-transparent px-4 py-2 text-sm"
      />
      <button
        type="submit"
        className="rounded-md bg-blue-600 text-white px-5 py-2 text-sm font-medium hover:bg-blue-500"
      >
        Send (demo)
      </button>
      {status && (
        <p role="status" className="block text-xs opacity-70">
          {status}
        </p>
      )}
    </form>
  );
}
