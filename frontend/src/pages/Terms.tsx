import { Link } from 'react-router-dom';
import { FileText, ArrowLeft } from 'lucide-react';

export default function Terms() {
  return (
    <div className="max-w-3xl mx-auto w-full py-8 px-4 space-y-6 text-slate-300">
      <Link to="/" className="inline-flex items-center gap-2 text-xs text-slate-400 hover:text-white transition-colors mb-2">
        <ArrowLeft size={14} />
        <span>Return to Dashboard</span>
      </Link>

      <div className="border-b border-slate-800 pb-4">
        <div className="flex items-center gap-2.5 mb-1">
          <FileText size={20} className="text-blue-500" />
          <h1 className="text-xl font-semibold text-white tracking-tight">Terms & Conditions</h1>
        </div>
        <p className="text-xs text-slate-400">Effective Date: November 11, 2026. Version 2.4.</p>
      </div>

      <div className="space-y-6 text-xs leading-relaxed">
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">1. License and Local Usage</h2>
          <p>
            Content Factory is licensed for local production, compilation, and automated assembly of audiovisual content. By running this software, you agree to execute operations in compliance with applicable local and international copyright laws, fair-use guidelines, and platform distribution terms.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">2. Ownership of Produced Content</h2>
          <p>
            You retain 100% intellectual property ownership of all videos, audio files, motion cards, and scripts assembled by your local pipeline instance. Content Factory asserts zero copyright, royalty, or commercial claim over your finished media outputs.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">3. Third-Party Media and Asset Rights</h2>
          <p>
            When utilizing third-party assets, stock photography (e.g. Pexels), or public datasets, you are solely responsible for ensuring adherence to the respective third-party license terms, attribution requirements, and commercial usage restrictions.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">4. System Performance and Storage Notice</h2>
          <p>
            Video rendering and multi-track audio concatenation involve intensive hardware operations. You are responsible for monitoring your local disk space, CPU temperature, and background render processes to prevent hardware exhaustion. The software is provided on an as-is basis without warranties of uninterrupted local operation.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">5. Updates and Modifications</h2>
          <p>
            These terms may be updated alongside new pipeline releases. Continued utilization of this local pipeline environment constitutes acceptance of current terms.
          </p>
        </section>
      </div>
    </div>
  );
}
