import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useJobs } from '../api/client';
import { Thumbnail } from '../components/Thumbnails';
import { Button, Badge, EmptyState } from '../components/ui';

export default function Vault() {
  const navigate = useNavigate();
  const { data: jobs = [], isLoading } = useJobs();
  
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');

  const vaultJobs = jobs.filter((j: any) => j.status === 'COMPLETED' || j.status === 'PUBLISHED');

  const filteredJobs = vaultJobs.filter((j: any) => {
    if (search && !j.niche.toLowerCase().includes(search.toLowerCase())) return false;
    if (statusFilter !== 'All' && j.status !== statusFilter) return false;
    return true;
  });

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8">
      <div className="flex justify-between items-center flex-wrap gap-3 mb-4 shrink-0">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Vault</h1>
          <div className="text-[var(--mu)] text-[13px]">Your finished videos and assets.</div>
        </div>
      </div>

      <div className="flex gap-3 mb-4 shrink-0">
        <input 
          type="text" 
          placeholder="Search..." 
          className="px-3 py-1.5 rounded-lg border border-[var(--ln)] bg-[var(--gl)] text-[13px] outline-none min-w-[200px]"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select 
          className="px-3 py-1.5 rounded-lg border border-[var(--ln)] bg-[var(--gl)] text-[13px] outline-none"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
        >
          <option value="All">All status</option>
          <option value="COMPLETED">Completed</option>
          <option value="PUBLISHED">Published</option>
        </select>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="glass-panel overflow-hidden animate-pulse h-[180px]" />
          ))}
        </div>
      ) : filteredJobs.length === 0 ? (
        <EmptyState 
          title="No finished videos" 
          description="Your vault is empty. Create a new video to get started." 
          action={{ label: 'Create new', onClick: () => navigate('/create') }} 
        />
      ) : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-4 overflow-y-auto pb-4">
          {filteredJobs.map((job: any) => {
            const cost = job.costs?.reduce((acc: number, c: any) => acc + (c.usd_estimate || 0), 0) || 0;
            const isFree = !job.config?.premium;

            return (
              <div key={job.id} className="glass-panel overflow-hidden cursor-pointer transition-transform hover:-translate-y-0.5 group !p-0">
                <Thumbnail type="mountain" className="h-[110px] !rounded-none" />
                <div className="p-[10px_12px]">
                  <b className="font-medium text-[13px] line-clamp-1">{job.niche}</b>
                  <div className="flex justify-between items-center mt-1 text-[11px] text-[var(--mu)]">
                    <span>
                      {job.config?.duration || '60s'} ·{' '}
                      {job.status === 'PUBLISHED' ? <Badge variant="success">Published</Badge> : <Badge variant="info">Completed</Badge>}
                    </span>
                    <span className="font-medium text-[var(--tx)]">{isFree ? 'Free' : `$${cost.toFixed(2)}`}</span>
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
