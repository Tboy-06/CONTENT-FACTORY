import React from 'react';
import { Card } from '../components/ui';

export default function Terms() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="border-b border-[var(--ln)] pb-4">
        <h1 className="text-2xl font-bold text-white">Terms & Conditions</h1>
        <p className="text-sm text-[var(--mu)] mt-1">Last updated: November 2026</p>
      </div>

      <Card className="space-y-4 text-sm text-[var(--tx)] leading-relaxed">
        <section className="space-y-2">
          <h2 className="text-base font-semibold text-white">1. Acceptance of Terms</h2>
          <p>
            By deploying or using CONTENT-FACTORY software, you agree to comply with these terms, governing the automation, generation, and publishing workflows of digital video content.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-semibold text-white">2. Permitted Use</h2>
          <p>
            The software is provided for multi-agent content generation, research, and timeline editing. Users are responsible for ensuring published media satisfies applicable distribution network policies and copyright laws.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-semibold text-white">3. Content Review & Responsibility</h2>
          <p>
            Automated content passes through a human-in-the-loop review gate (QC1). You assume full editorial responsibility for any content approved and published to external social platforms.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-semibold text-white">4. Disclaimer of Warranty</h2>
          <p>
            CONTENT-FACTORY is provided on an &quot;as is&quot; basis without warranties of any kind, either express or implied, regarding uptime, automated publishing outcomes, or platform algorithm metrics.
          </p>
        </section>
      </Card>
    </div>
  );
}
