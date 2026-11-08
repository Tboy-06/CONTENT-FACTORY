import React from 'react';
import { Card } from '../components/ui';

export default function Privacy() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="border-b border-[var(--ln)] pb-4">
        <h1 className="text-2xl font-bold text-white">Privacy Policy</h1>
        <p className="text-sm text-[var(--mu)] mt-1">Last updated: November 2026</p>
      </div>

      <Card className="space-y-4 text-sm text-[var(--tx)] leading-relaxed">
        <section className="space-y-2">
          <h2 className="text-base font-semibold text-white">1. Data Ownership and Local Storage</h2>
          <p>
            CONTENT-FACTORY operates with a local-first architecture. All generated video timelines, scripts,
            storyboards, and Vault assets remain stored on your local workstation and self-hosted instances.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-semibold text-white">2. AI Engine Data Transmission</h2>
          <p>
            When utilizing local open-source models (such as Ollama, Kokoro, Edge-TTS, and Whisper), no prompt or video data is transmitted to external servers. If external API endpoints are configured, data transmission adheres strictly to the chosen provider's standard terms.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-semibold text-white">3. Third-Party Integrations</h2>
          <p>
            Connected distribution channels (such as Postiz, Telegram, and YouTube) receive only the finalized media and metadata explicitly approved through human quality review checkpoints.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-semibold text-white">4. User Rights</h2>
          <p>
            You retain 100% ownership and copyright over all video artifacts, scripts, and media generated through your pipeline instances.
          </p>
        </section>
      </Card>
    </div>
  );
}
