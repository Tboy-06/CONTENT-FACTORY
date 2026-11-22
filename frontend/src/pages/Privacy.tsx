import { Link } from 'react-router-dom';
import { Shield, ArrowLeft } from 'lucide-react';

export default function Privacy() {
  return (
    <div className="animate-in fade-in max-w-3xl mx-auto w-full py-4 space-y-5">
      <Link
        to="/"
        className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--mu)] hover:text-[var(--tx)] transition-colors"
      >
        <ArrowLeft size={14} />
        <span>Return to Dashboard</span>
      </Link>

      <div className="glass-panel p-6 md:p-8 space-y-6">
        <div className="border-b border-[var(--ln-subtle)] pb-4">
          <div className="flex items-center gap-2.5 mb-1">
            <div className="p-2 rounded-xl bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/25">
              <Shield size={18} />
            </div>
            <h1 className="text-xl font-bold text-[var(--tx)] tracking-tight">Privacy Policy</h1>
          </div>
          <p className="text-xs text-[var(--mu)] mt-1">
            Effective Date: November 11, 2026. Last updated: November 2026.
          </p>
        </div>

        <div className="space-y-5 text-xs leading-relaxed text-[var(--mu)]">
          <section className="space-y-1.5">
            <h2 className="text-xs font-bold text-[var(--tx)] uppercase tracking-wider">
              1. Architecture and Data Isolation
            </h2>
            <p>
              Content Factory is designed with an offline-first and local-data isolation architecture. Video rendering, audio processing, frame extraction, and local knowledge graphs execute locally on your physical workstation. Raw video footage, project timelines, and database records remain stored in your local directory structures and are not transmitted to any centralized telemetry service.
            </p>
          </section>

          <section className="space-y-1.5">
            <h2 className="text-xs font-bold text-[var(--tx)] uppercase tracking-wider">
              2. API Credentials and External Services
            </h2>
            <p>
              When optional cloud capabilities are enabled (such as free-tier LLM routing, Pexels asset search, or external multimodal inference), credentials stored in your local configuration files are used strictly for direct HTTPS client requests to the respective provider endpoints. Your API keys are masked in API responses, stored locally on your machine, and never synchronized to external telemetry servers.
            </p>
          </section>

          <section className="space-y-1.5">
            <h2 className="text-xs font-bold text-[var(--tx)] uppercase tracking-wider">
              3. Local File Storage and Retention
            </h2>
            <p>
              Generated media assets, subtitles (.ass files), audio tracks, and temporary frame caches are written directly to your local file system under the configured workspace directories (`C:\cf_training\`). You maintain full administrative ownership and deletion control over all intermediate files, render caches, and project metadata.
            </p>
          </section>

          <section className="space-y-1.5">
            <h2 className="text-xs font-bold text-[var(--tx)] uppercase tracking-wider">
              4. Analytics and Telemetry
            </h2>
            <p>
              This application contains zero tracking cookies, zero third-party marketing pixels, and zero behavioral profiling mechanisms. Session states, system preferences, and theme choices (`Light Glass`, `Dark Glass`, `Classic`) are stored strictly within local browser storage (`localStorage`) on your local device.
            </p>
          </section>

          <section className="space-y-1.5">
            <h2 className="text-xs font-bold text-[var(--tx)] uppercase tracking-wider">
              5. Contact and Inquiries
            </h2>
            <p>
              For questions regarding local deployment, technical specifications, or security boundaries, refer to the documentation in your local repository or contact your workspace administrator.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
