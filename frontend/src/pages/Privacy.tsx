import { Link } from 'react-router-dom';
import { Shield, ArrowLeft } from 'lucide-react';

export default function Privacy() {
  return (
    <div className="max-w-3xl mx-auto w-full py-8 px-4 space-y-6 text-slate-300">
      <Link to="/" className="inline-flex items-center gap-2 text-xs text-slate-400 hover:text-white transition-colors mb-2">
        <ArrowLeft size={14} />
        <span>Return to Dashboard</span>
      </Link>

      <div className="border-b border-slate-800 pb-4">
        <div className="flex items-center gap-2.5 mb-1">
          <Shield size={20} className="text-blue-500" />
          <h1 className="text-xl font-semibold text-white tracking-tight">Privacy Policy</h1>
        </div>
        <p className="text-xs text-slate-400">Effective Date: November 11, 2026. Last updated: November 2026.</p>
      </div>

      <div className="space-y-6 text-xs leading-relaxed">
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">1. Architecture and Data Isolation</h2>
          <p>
            Content Factory is designed with an offline-first and local-data isolation architecture. Video rendering, audio processing, frame extraction, and local knowledge graphs execute locally on your physical workstation. Raw video footage, project timelines, and database records remain stored in your local directory structures and are not transmitted to any centralized telemetry service.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">2. API Credentials and External Services</h2>
          <p>
            When optional cloud capabilities are enabled (such as cloud transcription, Pexels asset search, or external LLM inference), credentials stored in your local configuration files are used strictly for direct HTTPS client requests to the respective provider endpoints. Your API keys are stored locally on your machine and are never synchronized to external telemetry or third-party monitoring servers.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">3. Local File Storage and Retention</h2>
          <p>
            Generated media assets, subtitles (.ass files), audio tracks, and temporary frame caches are written directly to your local file system under the configured workspace directories. You maintain full administrative ownership and deletion control over all intermediate files, render caches, and project metadata through the built-in storage management tools or directly via your operating system file manager.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">4. Analytics and Telemetry</h2>
          <p>
            This application contains zero tracking cookies, zero third-party marketing pixels, and zero behavioral profiling mechanisms. Session states, system preferences, and theme choices are stored strictly within local browser storage (localStorage) on your local device.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">5. Contact and Inquiries</h2>
          <p>
            For questions regarding local deployment, technical specifications, or security boundaries, refer to the documentation in your local repository or contact your workspace administrator.
          </p>
        </section>
      </div>
    </div>
  );
}
