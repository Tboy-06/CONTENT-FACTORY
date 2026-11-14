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

export interface VideoContext {
  status: string;
  video_path: string;
  filename: string;
  duration: number;
  dimensions: {
    duration: number;
    width: number;
    height: number;
    aspect_ratio: string;
    fps: number;
  };
  pacing: {
    cuts_count: number;
    avg_cut_interval: number;
    cuts_per_minute: number;
    cut_timestamps: number[];
  };
  audio: {
    total_words: number;
    words_per_minute: number;
    silence_segments: Array<{ start: number; end: number; duration: number }>;
    total_silence_seconds: number;
    transcript: Array<{ start: number | string; end: number | string; text: string }>;
    full_text: string;
  };
  full_text: string;
}

export interface DirectorChatAction {
  action?: string;
  [key: string]: any;
}

export interface DirectorChatResponse {
  status: string;
  message: string;
  actions: DirectorChatAction[];
  executed_actions: any[];
  video_url?: string;
  job_id?: number;
}

export function useAnalyzeVideo() {
  return useMutation({
    mutationFn: async ({ file, jobId, videoPath }: { file?: File; jobId?: number; videoPath?: string }) => {
      const formData = new FormData();
      if (file) formData.append('file', file);
      if (jobId !== undefined && jobId !== null) formData.append('job_id', String(jobId));
      if (videoPath) formData.append('video_path', videoPath);
      return (await api.upload('/api/copilot/analyze-video', formData)) as VideoContext;
    }
  });
}

export function useDirectorChat() {
  return useMutation({
    mutationFn: async ({
      prompt,
      jobId,
      videoContext,
      engineMode = 'auto',
      history,
    }: {
      prompt: string;
      jobId?: number;
      videoContext?: VideoContext | null;
      engineMode?: 'auto' | 'offline_spark' | 'cloud';
      history?: Array<{ role: string; content: string }>;
    }) => {
      const data = await api.post('/api/copilot/chat', {
        prompt,
        job_id: jobId,
        video_context: videoContext,
        engine_mode: engineMode,
        history,
      });
      return data as DirectorChatResponse;
    },
    onSuccess: (data) => {
      if (data.executed_actions && data.executed_actions.length > 0) {
        queryClient.invalidateQueries({ queryKey: ['jobs'] });
      }
    }
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
    mutationFn: async ({
      topic,
      voice,
      style_preset,
      aspect_ratio,
      duration
    }: {
      topic: string;
      voice?: string;
      style_preset?: string;
      aspect_ratio?: string;
      duration?: string;
    }) => {
      const data = await api.post('/api/jobs/instant', {
        topic,
        voice,
        style_preset,
        aspect_ratio,
        duration
      });
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

export function useUploadCustomSceneMedia() {
  return useMutation({
    mutationFn: async ({ jobId, sceneIndex, file }: { jobId: string | number, sceneIndex: number, file: File }) => {
      const formData = new FormData();
      formData.append('file', file);
      return await api.upload(`/api/jobs/${jobId}/scenes/${sceneIndex}/upload-custom-media`, formData);
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

export interface ThumbnailVariant {
  id: number;
  name: string;
  thumb_16x9: string;
  thumb_9x16: string;
  style: string;
  badge: string;
}

export interface ThumbnailPackage {
  status: string;
  job_id: number;
  variants: ThumbnailVariant[];
  ab_titles: string[];
}

export function useJobThumbnails(jobId?: string | number) {
  return useQuery({
    queryKey: ['job-thumbnails', jobId],
    queryFn: async () => {
      if (!jobId) return null;
      return (await api.get(`/api/jobs/${jobId}/thumbnails`)) as ThumbnailPackage;
    },
    enabled: !!jobId,
  });
}

export function useRegenerateThumbnails() {
  return useMutation({
    mutationFn: async (jobId: string | number) => {
      return (await api.post(`/api/jobs/${jobId}/thumbnails/generate`)) as ThumbnailPackage;
    },
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: ['job-thumbnails', jobId] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    }
  });
}

export interface ViralShort {
  id: number;
  title: string;
  start: number;
  end: number;
  duration: number;
  video_url: string;
  thumb_url?: string;
  hook_text?: string;
}

export function useSliceViralShorts() {
  return useMutation({
    mutationFn: async (payload: {
      video_path?: string;
      youtube_url?: string;
      job_id?: number;
      target_count?: number;
      min_duration?: number;
      max_duration?: number;
    }) => {
      return await api.post('/api/copilot/slice-viral-shorts', payload);
    }
  });
}
