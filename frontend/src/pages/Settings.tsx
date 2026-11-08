import { useState, useEffect } from 'react';
import { useSettings, useUpdateSettings } from '../api/client';
import { Button } from '../components/ui';

const SecretInput = ({ label, value, onChange, disableable, disabled, onToggleDisable }: any) => {
  const [show, setShow] = useState(false);
  
  return (
    <div className="flex justify-between items-center py-3 border-b border-[var(--ln)] last:border-0 text-[13px]">
      <span className="text-[var(--tx)] font-medium">{label}</span>
      <div className="flex gap-2">
        <input 
          type={show ? "text" : "password"} 
          value={value || ''} 
          onChange={e => onChange(e.target.value)}
          disabled={disabled}
          placeholder="Not set"
          className="px-3 py-1.5 rounded-lg border border-[var(--ln)] bg-[var(--gl)] outline-none min-w-[200px] text-sm font-mono disabled:opacity-50"
        />
        <Button variant="ghost" onClick={() => setShow(!show)}>{show ? 'Hide' : 'Show'}</Button>
        {disableable && (
          <Button variant="ghost" onClick={onToggleDisable} className={disabled ? '' : '!bg-[rgba(255,107,122,0.1)] !text-[var(--er)] !border-[rgba(255,107,122,0.4)]'}>
            {disabled ? 'Enable' : 'Disable'}
          </Button>
        )}
      </div>
    </div>
  );
};

export default function Settings() {
  const { data: serverSettings, isLoading } = useSettings();
  const updateMutation = useUpdateSettings();

  const [settings, setSettings] = useState<any>({
    openai_key: '',
    gemini_key: '',
    telegram_token: '',
    youtube_key: '',
    pexels_key: '',
    spend_cap: '10.00',
    force_offline: false,
    youtube_enabled: true,
    pexels_enabled: true
  });

  useEffect(() => {
    if (serverSettings) {
      setSettings((prev: any) => ({ ...prev, ...serverSettings }));
    }
  }, [serverSettings]);

  const handleSave = async () => {
    try {
      await updateMutation.mutateAsync(settings);
    } catch(e) {
      console.error(e);
    }
  };

  if (isLoading) {
    return <div className="p-8 text-center text-[var(--mu)]">Loading settings...</div>;
  }

  return (
    <div className="animate-in fade-in min-h-full flex flex-col max-w-4xl mx-auto w-full pb-8">
      <div className="flex justify-between items-center flex-wrap gap-3 mb-6 shrink-0">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Settings</h1>
          <div className="text-[var(--mu)] text-[13px]">Manage integrations and system behavior.</div>
        </div>
        <Button onClick={handleSave} disabled={updateMutation.isPending}>
          {updateMutation.isPending ? 'Saving...' : 'Save changes'}
        </Button>
      </div>

      <div className="flex flex-col gap-6 flex-1 overflow-y-auto pb-8">
        
        <div className="glass-panel p-5">
          <h2 className="font-semibold text-[15px] mb-4">Core Credentials</h2>
          <div className="flex flex-col">
            <SecretInput 
              label="OpenAI API Key" 
              value={settings.openai_key} 
              onChange={(val: string) => setSettings({...settings, openai_key: val})} 
            />
            <SecretInput 
              label="Gemini API Key" 
              value={settings.gemini_key} 
              onChange={(val: string) => setSettings({...settings, gemini_key: val})} 
            />
            <SecretInput 
              label="Telegram Bot Token" 
              value={settings.telegram_token} 
              onChange={(val: string) => setSettings({...settings, telegram_token: val})} 
            />
          </div>
        </div>

        <div className="glass-panel p-5">
          <h2 className="font-semibold text-[15px] mb-4">Optional Integrations</h2>
          <div className="flex flex-col">
            <SecretInput 
              label="YouTube OAuth API Key" 
              value={settings.youtube_key} 
              onChange={(val: string) => setSettings({...settings, youtube_key: val})} 
              disableable
              disabled={!settings.youtube_enabled}
              onToggleDisable={() => setSettings({...settings, youtube_enabled: !settings.youtube_enabled})}
            />
            <SecretInput 
              label="Pexels API Key" 
              value={settings.pexels_key} 
              onChange={(val: string) => setSettings({...settings, pexels_key: val})} 
              disableable
              disabled={!settings.pexels_enabled}
              onToggleDisable={() => setSettings({...settings, pexels_enabled: !settings.pexels_enabled})}
            />
          </div>
        </div>

        <div className="glass-panel p-5">
          <h2 className="font-semibold text-[15px] mb-4">Jobs & Connections</h2>
          <div className="flex flex-col">
            <div className="flex justify-between items-center py-3 border-b border-[var(--ln)] text-[13px]">
              <span className="text-[var(--tx)] font-medium">Monthly Spend Cap</span>
              <div className="flex gap-2">
                <span className="text-[var(--mu)] self-center">$</span>
                <input 
                  type="number" 
                  value={settings.spend_cap} 
                  onChange={e => setSettings({...settings, spend_cap: e.target.value})}
                  className="px-3 py-1.5 rounded-lg border border-[var(--ln)] bg-[var(--gl)] outline-none w-[100px] text-sm text-right"
                />
              </div>
            </div>
            
            <div className="flex justify-between items-center py-3 border-b border-[var(--ln)] text-[13px]">
              <span className="text-[var(--tx)] font-medium">Force Offline Mode</span>
              <div 
                className={`w-11 h-6 rounded-full p-1 cursor-pointer transition-colors ${settings.force_offline ? 'bg-[var(--ac)]' : 'bg-[var(--ln)]'}`}
                onClick={() => setSettings({...settings, force_offline: !settings.force_offline})}
              >
                <div className={`w-4 h-4 rounded-full bg-white transition-transform ${settings.force_offline ? 'translate-x-5' : 'translate-x-0'}`} />
              </div>
            </div>
          </div>
          <div className="text-[var(--mu)] text-xs mt-3">
            Offline mode disables premium engines and queues publishing until reconnected. Spend cap applies to paid jobs only.
          </div>
        </div>

      </div>
    </div>
  );
}
