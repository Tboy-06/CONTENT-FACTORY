import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Film, Download, Trash2, ExternalLink } from 'lucide-react';
import { useJobs, useDeleteJob, useClearAllJobs } from '../api/client';
import { Thumbnail } from '../components/Thumbnails';
import { Button, Badge, EmptyState } from '../components/ui';

export default function Vault() {
  const navigate = useNavigate();
  const { data: jobs = [], isLoading } = useJobs();
  const deleteJobMutation = useDeleteJob();
  const clearAllMutation = useClearAllJobs();
  
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');

  // Include completed, published, or any job that has a rendered VIDEO asset
  const vaultJobs = jobs.filter((j: any) => 
    j.status === 'COMPLETED' || 
    j.status === 'PUBLISHED' || 
    j.current_stage === 'QC1' ||
    j.assets?.some((a: any) => a.type === 'VIDEO' || a.type === 'video')
  );

  const filteredJobs = vaultJobs.filter((j: any) => {
    if (search && !j.niche.toLowerCase().includes(search.toLowerCase())) return false;
    if (statusFilter !== 'All' && j.status !== statusFilter) return false;
    return true;
  });

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8">
      {/* Header */}
      <div className="flex justify-between items-center flex-wrap gap-3 mb-4 shrink-0">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-white">Vault</h1>
          <div className="text-[var(--mu)] text-[13px]">Your library of finished 9:16 documentary videos and assets.</div>
        </div>

        {vaultJobs.length > 0 && (
          <Button
            variant="secondary"
            onClick={() => {
              if (confirm('Clear all vault videos and jobs?')) {
                clearAllMutation.mutate();
              }
            }}
            disabled={clearAllMutation.isPending}
            className="flex items-center gap-1.5 text-xs !py-1.5 !px-3 border-slate-700 text-slate-300 hover:text-red-400"
          >
            <Trash2 size={13} />
            <span>Clear Vault</span>
          </Button>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="flex gap-3 mb-4 shrink-0">
        <input 
          type="text" 
          placeholder="Search videos..." 
          className="px-3 py-1.5 rounded-lg border border-[var(--ln)] bg-[var(--gl)] text-slate-200 text-[13px] outline-none min-w-[220px] focus:border-blue-500"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select 
          className="px-3 py-1.5 rounded-lg border border-[var(--ln)] bg-[var(--gl)] text-slate-200 text-[13px] outline-none"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
        >
          <option value="All">All statuses</option>
          <option value="COMPLETED">Completed</option>
          <option value="PUBLISHED">Published</option>
        </select>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="glass-panel overflow-hidden animate-pulse h-[200px]" />
          ))}
        </div>
      ) : filteredJobs.length === 0 ? (
        <EmptyState 
          title="No finished videos yet" 
          description="Your vault is empty. Generate a new vertical documentary to populate your vault." 
        />
      ) : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-4 pb-4">
          {filteredJobs.map((job: any) => {
            const videoAsset = job.assets?.find((a: any) => a.type === 'VIDEO' || a.type === 'video');
            const videoMeta = videoAsset?.metadata || {};
            const videoUrl = videoMeta.video_url || (videoAsset?.path ? `/output/${videoAsset.path.split(/[\\/]/).pop()}` : null);

            return (
              <div 
                key={job.id} 
                onClick={() => navigate(`/qc1/${job.id}`)}
                className="glass-panel overflow-hidden cursor-pointer transition-all hover:-translate-y-1 hover:border-blue-500/50 group !p-0 flex flex-col justify-between"
              >
                <div className="relative h-[120px] bg-slate-950 flex items-center justify-center border-b border-slate-800">
                  <div className="w-10 h-10 rounded-xl bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center">
                    <Film size={20} />
                  </div>
                  <span className="absolute top-2 right-2 text-[10px] font-mono px-2 py-0.5 rounded bg-black/60 text-slate-300 border border-white/10">
                    Job #{job.id}
                  </span>
                </div>

                <div className="p-3 space-y-2">
                  <b className="font-medium text-sm text-white line-clamp-1 group-hover:text-blue-400 transition-colors">
                    {job.niche}
                  </b>

                  <div className="flex justify-between items-center text-xs text-[var(--mu)]">
                    <Badge variant={job.status === 'PUBLISHED' ? 'success' : 'info'}>
                      {job.status === 'PUBLISHED' ? 'Published' : '9:16 Ready'}
                    </Badge>
                    <span className="font-mono text-[11px] text-slate-400">
                      {videoMeta.duration ? `${Math.round(videoMeta.duration)}s` : '45s'}
                    </span>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                    {videoUrl ? (
                      <a
                        href={videoUrl}
                        download={`${job.niche.replace(/[^a-zA-Z0-9_-]/g, '_')}_9x16.mp4`}
                        onClick={(e) => e.stopPropagation()}
                        className="text-[11px] text-emerald-400 hover:text-emerald-300 flex items-center gap-1 transition-colors"
                        title="Download 9:16 MP4"
                      >
                        <Download size={13} />
                        <span>Download</span>
                      </a>
                    ) : <span />}

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteJobMutation.mutate(job.id);
                      }}
                      className="text-slate-500 hover:text-red-400 p-1 transition-colors rounded"
                      title="Delete video from vault"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
