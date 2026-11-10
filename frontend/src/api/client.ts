import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export const api = {
  get: async (url: string) => {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`GET ${url} failed`);
    return res.json();
  },
  post: async (url: string, body?: any) => {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`POST ${url} failed`);
    return res.json();
  },
  put: async (url: string, body?: any) => {
    const res = await fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`PUT ${url} failed`);
    return res.json();
  },
  delete: async (url: string) => {
    const res = await fetch(url, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error(`DELETE ${url} failed`);
    return res.json();
  },
  upload: async (url: string, formData: FormData) => {
    const res = await fetch(url, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error(`UPLOAD ${url} failed`);
    return res.json();
  }
};

import { useMutation, useQuery } from '@tanstack/react-query';

export function useJobs() {
  return useQuery({
    queryKey: ['jobs'],
    queryFn: async () => {
      const data = await api.get('/api/jobs');
      return data;
    },
    refetchInterval: 5000, // Poll every 5s
  });
}

export function useChat() {
  return useMutation({
    mutationFn: async ({ prompt, system_prompt }: { prompt: string, system_prompt?: string }) => {
      const data = await api.post('/api/copilot/chat', { prompt, system_prompt });
      return data.response;
    }
  });
}

export function useScoreNiche() {
  return useMutation({
    mutationFn: async (niche: string) => {
      const data = await api.post('/api/jobs/score-niche', { niche });
      return data.data;
    }
  });
}

export function useCreateJob() {
  return useMutation({
    mutationFn: async (jobData: any) => {
      const data = await api.post('/api/jobs', jobData);
      return data;
    }
  });
}

export function useCreateInstantJob() {
  return useMutation({
    mutationFn: async ({ topic, voice, style_preset }: { topic: string, voice?: string, style_preset?: string }) => {
      const data = await api.post('/api/jobs/instant', { topic, voice, style_preset });
      return data;
    }
  });
}

export function useBrainstormHooks() {
  return useMutation({
    mutationFn: async (topic: string) => {
      const data = await api.post('/api/jobs/brainstorm-hooks', { topic });
      return data.hooks || [];
    }
  });
}

export function useCacheStatus() {
  return useQuery({
    queryKey: ['system-cache'],
    queryFn: async () => {
      return await api.get('/api/system/cache');
    },
    refetchInterval: 10000,
  });
}

export function useClearCache() {
  return useMutation({
    mutationFn: async () => {
      return await api.post('/api/system/cache/clear');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-cache'] });
    }
  });
}

export function useRerollVisual() {
  return useMutation({
    mutationFn: async ({ jobId, sceneIndex, customPrompt, stylePreset }: { jobId: string | number, sceneIndex: number, customPrompt?: string, stylePreset?: string }) => {
      return await api.post(`/api/jobs/${jobId}/reroll-visual`, {
        scene_index: sceneIndex,
        custom_prompt: customPrompt,
        style_preset: stylePreset,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    }
  });
}

export function useRegenerateAudio() {
  return useMutation({
    mutationFn: async ({ jobId, voice, scenes }: { jobId: string | number, voice?: string, scenes?: any[] }) => {
      return await api.post(`/api/jobs/${jobId}/regenerate-audio`, {
        voice,
        scenes,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    }
  });
}

export function useUploadAnchor() {
  return useMutation({
    mutationFn: async ({ jobId, file }: { jobId: string | number, file: File }) => {
      const formData = new FormData();
      formData.append('file', file);
      return await api.upload(`/api/jobs/${jobId}/upload-anchor`, formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    }
  });
}

export function usePublishJob() {
  return useMutation({
    mutationFn: async ({ jobId, platforms }: { jobId: string | number, platforms: string[] }) => {
      return await api.post(`/api/jobs/${jobId}/publish`, { platforms });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    }
  });
}

export function useDeleteJobTemp() {
  return useMutation({
    mutationFn: async (jobId: string | number) => {
      return await api.post(`/api/jobs/${jobId}/delete-temp`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-cache'] });
    }
  });
}

export function useDeleteJob() {
  return useMutation({
    mutationFn: async (jobId: string | number) => {
      return await api.delete(`/api/jobs/${jobId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['system-cache'] });
    }
  });
}

export function useClearAllJobs() {
  return useMutation({
    mutationFn: async (status?: string) => {
      const qs = status ? `?status=${status}` : '';
      return await api.delete(`/api/jobs${qs}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['system-cache'] });
    }
  });
}

export function useApproveJob() {
  return useMutation({
    mutationFn: async ({ jobId, notes }: { jobId: string, notes?: string }) => {
      return await api.post(`/api/jobs/${jobId}/approve`, { notes });
    }
  });
}

export function useRejectJob() {
  return useMutation({
    mutationFn: async ({ jobId, reason }: { jobId: string, reason: string }) => {
      return await api.post(`/api/jobs/${jobId}/reject`, { reason });
    }
  });
}

export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      return await api.get('/api/settings');
    }
  });
}

export function useUpdateSettings() {
  return useMutation({
    mutationFn: async (settings: any) => {
      return await api.post('/api/settings', settings);
    }
  });
}

// Mock for capabilities since it's missing from the backend
export function useCapabilities() {
  return useQuery({
    queryKey: ['capabilities'],
    queryFn: async () => {
      return await api.get('/api/capabilities');
    }
  });
}

export function useSpend() {
  return useQuery({
    queryKey: ['spend'],
    queryFn: async () => {
      const data = await api.get('/api/jobs/spend');
      return data.total_spend;
    }
  });
}
