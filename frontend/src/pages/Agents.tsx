import { Badge } from '../components/ui';

export default function Agents() {
  const agents = [
    { name: 'Niche scorer', status: 'Idle', model: 'gpt-4o-mini', type: 'Evaluator' },
    { name: 'Researcher', status: 'Active', model: 'gemini-1.5-pro', type: 'Content' },
    { name: 'Scriptwriter', status: 'Idle', model: 'gpt-4o', type: 'Content' },
    { name: 'Art director', status: 'Idle', model: 'dall-e-3', type: 'Visual' },
    { name: 'Storyboard director', status: 'Idle', model: 'claude-3-5-sonnet', type: 'Planner' },
    { name: 'Video editor', status: 'Active', model: 'ffmpeg', type: 'Renderer' },
  ];

  return (
    <div className="animate-in fade-in min-h-full flex flex-col pb-8">
      <div className="flex justify-between items-center flex-wrap gap-3 mb-6 shrink-0">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Agents Studio</h1>
          <div className="text-[var(--mu)] text-[13px] mt-1">Manage the AI workforce powering your pipeline.</div>
        </div>
      </div>

      <div className="p-4 bg-[rgba(79,124,255,0.06)] border border-[rgba(79,124,255,0.2)] text-[var(--ac)] rounded-xl text-sm mb-6">
        Note: Backend capabilities mapping and agent config APIs are currently missing. This is a read-only preview.
      </div>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-4">
        {agents.map(agent => (
          <div key={agent.name} className="glass-panel p-5 flex flex-col gap-3">
            <div className="flex justify-between items-start">
              <div>
                <b className="font-semibold text-[15px]">{agent.name}</b>
                <div className="text-[12px] text-[var(--mu)] mt-0.5">{agent.type}</div>
              </div>
              {agent.status === 'Active' ? <Badge variant="success">Active</Badge> : <Badge variant="neutral">Idle</Badge>}
            </div>
            
            <div className="mt-2 text-[13px]">
              <div className="text-[var(--mu)] mb-1.5">Model / Engine</div>
              <select 
                className="w-full px-2.5 py-1.5 rounded-lg border border-[var(--ln)] bg-[var(--bg)] outline-none text-[var(--tx)] hover:border-[var(--ac)] transition-colors cursor-pointer"
                defaultValue={agent.model}
              >
                <option value={agent.model}>{agent.model}</option>
                <option value="gpt-4o">GPT-4o</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
              </select>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
